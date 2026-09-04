"""Small, deterministic sound-design helpers; no external audio samples."""
from pathlib import Path
import wave
import numpy as np

SR = 48000
RNG = np.random.default_rng(20260905)
TAU = 2 * np.pi


def timeline(seconds):
    return np.arange(round(seconds * SR), dtype=np.float64) / SR


def envelope(t, attack=0.002, decay=0.1):
    return (1 - np.exp(-t / attack)) * np.exp(-t / decay)


def taper(x, attack=0.001, release=0.025):
    x = x.copy()
    na = min(len(x), round(attack * SR))
    nr = min(len(x), round(release * SR))
    if na:
        ramp = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
        x[:na] *= ramp[:, None] if x.ndim == 2 else ramp
    if nr:
        ramp = np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
        x[-nr:] *= ramp[:, None] if x.ndim == 2 else ramp
    return x


def oscillator(frequency, seconds, partials=((1, 1),), bend=None):
    t = timeline(seconds)
    f = np.full_like(t, frequency)
    if bend is not None:
        start, settle = bend
        f += (start - frequency) * np.exp(-t / settle)
    phase = TAU * np.cumsum(f) / SR
    return sum(amp * np.sin(ratio * phase) for ratio, amp in partials)


def tonal(frequency, seconds, decay, attack=0.002, partials=((1, 1),), bend=None):
    return taper(oscillator(frequency, seconds, partials, bend)
                 * envelope(timeline(seconds), attack, decay))


def color_noise(seconds, low=150, high=8000, tilt=0):
    n = round(seconds * SR)
    padded = 1 << (max(1024, n) - 1).bit_length()
    white = RNG.normal(0, 1, padded)
    f = np.fft.rfftfreq(padded, 1 / SR)
    safe = np.maximum(f, 1)
    response = 1 / np.sqrt(1 + (low / safe) ** 6)
    response *= 1 / np.sqrt(1 + (safe / high) ** 8)
    response *= (safe / 1000) ** tilt
    response[0] = 0
    x = np.fft.irfft(np.fft.rfft(white) * response, n=padded)[:n]
    return x / max(np.std(x), 1e-12)


def sweep_noise(seconds, start_hz, peak_hz, end_hz, peak_at, width=1.25):
    t = timeline(seconds)
    p = t / seconds
    centers = np.exp(np.interp(p, [0, peak_at, 1],
                              np.log([start_hz, peak_hz, end_hz])))
    x = np.zeros_like(t)
    for center in np.geomspace(150, 10500, 16):
        weight = np.exp(-0.5 * (np.log2(centers / center) / width) ** 2)
        x += color_noise(seconds, center / 1.23, min(16000, center * 1.23)) * weight
    return x / max(np.std(x), 1e-12)


def stereo(seconds):
    return np.zeros((round(seconds * SR), 2), dtype=np.float64)


def place(dest, mono, at=0, gain=1, pan=0):
    offset = round(at * SR)
    n = min(len(mono), len(dest) - offset)
    if n <= 0:
        return
    angle = (np.asarray(pan) + 1) * np.pi / 4
    if angle.ndim:
        angle = angle[:n]
    dest[offset:offset + n, 0] += mono[:n] * gain * np.cos(angle)
    dest[offset:offset + n, 1] += mono[:n] * gain * np.sin(angle)


def room(signal, decay=0.13, wet=0.07):
    """Quiet, decorrelated early reflections and a diffuse tail."""
    out = signal.copy()
    mono = signal.mean(axis=1)
    ir_n = min(len(signal), round(decay * 6 * SR))
    tt = np.arange(ir_n) / SR
    for channel in range(2):
        ir = RNG.normal(size=ir_n) * np.exp(-tt / decay)
        ir[:round(0.009 * SR)] = 0
        ir *= RNG.random(ir_n) < 0.16
        ir = np.convolve(ir, np.ones(7) / 7, mode='same')
        ir = taper(ir, 0.003, 0.04)
        ir /= max(np.linalg.norm(ir), 1e-12)
        size = 1 << (len(signal) + len(ir) - 2).bit_length()
        convolution = np.fft.irfft(np.fft.rfft(mono, size)
                                   * np.fft.rfft(ir, size), n=size)
        out[:, channel] += wet * convolution[:len(signal)]
    return out


def short_rms(signal, seconds=0.05):
    power = np.mean(signal ** 2, axis=1)
    window = min(round(seconds * SR), len(signal))
    acc = np.concatenate(([0], np.cumsum(power)))
    return float(np.sqrt(np.max((acc[window:] - acc[:-window]) / window)))


def interpolated_peak(signal, factor=4):
    # Zero padding produces a band-limited interpolation; ends are tapered.
    n = len(signal)
    up = np.fft.irfft(np.fft.rfft(signal, axis=0), n=n * factor, axis=0) * factor
    return float(np.max(np.abs(up)))


def master(signal, rms_db=-19, peak_db=-6):
    out = signal.copy()
    # Remove very low rumble/DC while keeping the audible body of impacts.
    f = np.fft.rfftfreq(len(out), 1 / SR)
    curve = 1 / np.sqrt(1 + (25 / np.maximum(f, 0.001)) ** 8)
    curve[0] = 0
    out = np.fft.irfft(np.fft.rfft(out, axis=0) * curve[:, None], n=len(out), axis=0)
    out = taper(out, 0.002, 0.055)
    out *= 10 ** (rms_db / 20) / max(short_rms(out), 1e-12)
    peak = interpolated_peak(out)
    out *= min(1, 10 ** (peak_db / 20) / peak)
    out[:4] = 0
    out[-8:] = 0
    return out


def trim_tail(signal):
    activity = np.max(np.abs(signal), axis=1)
    audible = np.where(activity > 10 ** (-70 / 20))[0]
    end_seconds = max(0.15, np.ceil((audible[-1] / SR + 0.045) * 100) / 100)
    end = min(len(signal), round(end_seconds * SR))
    return taper(signal[:end], attack=0, release=0.025)


def db(value):
    return float(20 * np.log10(max(float(value), 1e-12)))


def write_wav(path, signal):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Triangular dither at 24-bit precision; deterministic, inaudibly low.
    dither = RNG.random(signal.shape) - RNG.random(signal.shape)
    ints = np.rint(signal * 8388607 + dither).astype(np.int32)
    ints[:4] = 0
    ints[-8:] = 0
    packed = np.empty((ints.size, 3), dtype=np.uint8)
    flat = ints.ravel()
    for k in range(3):
        packed[:, k] = (flat >> (8 * k)) & 255
    with wave.open(str(path), 'wb') as file:
        file.setnchannels(2)
        file.setsampwidth(3)
        file.setframerate(SR)
        file.writeframes(packed.tobytes())


def read_wav(path):
    with wave.open(str(path), 'rb') as file:
        assert file.getframerate() == SR and file.getnchannels() == 2
        assert file.getsampwidth() == 3 and file.getcomptype() == 'NONE'
        packed = np.frombuffer(file.readframes(file.getnframes()), dtype=np.uint8).reshape(-1, 3)
    ints = packed[:, 0].astype(np.int32) | (packed[:, 1].astype(np.int32) << 8) | (packed[:, 2].astype(np.int32) << 16)
    ints = (ints ^ 0x800000) - 0x800000
    return ints.reshape(-1, 2).astype(np.float64) / 8388607
