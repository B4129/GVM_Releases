"""Shared acoustic building blocks, with deterministic noise from dsp.RNG."""
import numpy as np
import dsp
from dsp import SR, TAU, timeline, envelope, taper, tonal, oscillator, color_noise
from dsp import stereo, place, room


def contour(seconds, points):
    t = timeline(seconds)
    return np.interp(t / seconds, np.linspace(0, 1, len(points)), points)


def gliss(seconds, points, decay=0.08, attack=0.002, partials=((1, 1),)):
    t = timeline(seconds)
    phase = TAU * np.cumsum(contour(seconds, points)) / SR
    tone = sum(a * np.sin(r * phase) for r, a in partials)
    return taper(tone * envelope(t, attack, decay))


def strike(seconds, f=500, decay=0.04, noise=0.10, material='wood', start=None):
    t = timeline(seconds)
    ratios = {'wood': ((1, 1), (2.76, 0.28), (5.4, 0.05)),
              'metal': ((1, 1), (1.414, 0.24), (2.79, 0.20), (4.07, 0.08)),
              'soft': ((1, 1), (2, 0.12)),
              'click': ((1, 1), (2.31, 0.17))}[material]
    bend = None if start is None else (start, 0.009)
    tone = tonal(f, seconds, decay, 0.0015, ratios, bend)
    low, high = (800, 7500) if material in ('click', 'metal') else (180, 3600)
    texture = color_noise(seconds, low, high) * envelope(t, 0.0008, decay * 0.21)
    return tone + noise * texture


def bell(seconds, frequency, decay=0.14, style='glass'):
    t = timeline(seconds)
    modes = {'glass': ((1, 1, 1), (2.756, 0.16, 0.55), (4.11, 0.06, 0.3)),
             'round': ((1, 1, 1), (2.003, 0.09, 0.7)),
             'wood': ((1, 1, 1), (3.99, 0.10, 0.21), (9.97, 0.016, 0.08)),
             'metal': ((1, 1, 1), (1.49, 0.17, 0.65), (2.71, 0.10, 0.38)),
             'retro': ((1, 1, 1), (3, 0.15, 0.65), (5, 0.05, 0.35))}[style]
    out = np.zeros_like(t)
    for ratio, amplitude, factor in modes:
        if frequency * ratio < 18000:
            out += amplitude * np.sin(TAU * frequency * ratio * t) * envelope(t, 0.0025, decay * factor)
    return taper(out)


def pop(p):
    duration = p.get('duration', 0.48)
    x = stereo(duration)
    f = p.get('f', 260)
    decay = p.get('decay', 0.045)
    count = p.get('count', 1)
    for i in range(count):
        note_duration = min(0.45, duration - i * p.get('gap', 0.09))
        t = timeline(note_duration)
        freq = f * p.get('step', 1.2) ** i
        if p.get('wobble'):
            phase = TAU * np.cumsum(freq + p['wobble'] * np.exp(-t / 0.1) * np.cos(TAU * p.get('speed', 7) * t)) / SR
            sound = (np.sin(phase) + 0.13 * np.sin(2 * phase)) * envelope(t, 0.002, decay)
        else:
            sound = tonal(freq, note_duration, decay, 0.0017,
                          ((1, 1), (2, p.get('harmonic', 0.13))),
                          (p.get('start', f * 2) * p.get('step', 1.2) ** i, p.get('bend', 0.014)))
        texture = color_noise(note_duration, p.get('low', 900), p.get('high', 5500))
        sound += p.get('noise', 0.035) * texture * envelope(t, 0.001, 0.006)
        place(x, taper(sound), i * p.get('gap', 0.09), 0.9 ** i,
              0 if count == 1 else np.linspace(-0.16, 0.16, count)[i])
    return room(x, p.get('room', 0.035), p.get('wet', 0.045))


def clicks(p):
    x = stereo(p.get('duration', 0.42))
    times = p.get('times', [0])
    freqs = p.get('freqs', [p.get('f', 950)] * len(times))
    for i, at in enumerate(times):
        sound = strike(p.get('tail', 0.17), freqs[i], p.get('decay', 0.008),
                       p.get('noise', 0.5), p.get('material', 'click'))
        place(x, sound, at, p.get('gains', [1] * len(times))[i],
              float(dsp.RNG.uniform(-0.1, 0.1)))
    if p.get('rustle'):
        d = p['rustle']
        tt = timeline(d)
        place(x, color_noise(d, 1200, 6500) * np.sin(np.pi * tt / d) ** 2,
              p.get('rustle_at', 0.04), 0.11)
    return room(x, 0.021, 0.04)


def chime(p):
    x = stereo(p.get('duration', 1.3))
    notes = p.get('notes', [880])
    times = p.get('times', [i * p.get('gap', 0.1) for i in range(len(notes))])
    for i, (at, note) in enumerate(zip(times, notes)):
        sound = bell(min(1.4, len(x) / SR - at), note,
                     p.get('decay', 0.13), p.get('style', 'glass'))
        place(x, sound, at, p.get('gains', [1] * len(notes))[i],
              0 if len(notes) == 1 else np.linspace(-0.22, 0.22, len(notes))[i])
    return room(x, p.get('room', 0.09), p.get('wet', 0.10))


def reaction(p):
    x = stereo(p.get('duration', 0.9))
    mode = p.get('mode', 'bounce')
    if mode == 'buzz':
        for at, f in zip(p.get('times', [0, 0.20]), p.get('notes', [150, 135])):
            d = p.get('note_duration', 0.14)
            t = timeline(d)
            env = np.sin(np.minimum(1, np.minimum(t / 0.009, (d - t) / 0.02)) * np.pi / 2) ** 2
            place(x, oscillator(f, d, ((1, 1), (3, 0.28), (5, 0.08))) * env, at)
    elif mode == 'slide':
        sound = gliss(p.get('length', 0.6), p['points'], p.get('decay', 0.16),
                      0.004, ((1, 1), (2, 0.18), (3, 0.1), (5, 0.04)))
        place(x, sound)
    else:
        t = timeline(p.get('length', 0.65))
        f = p.get('f', 320) + p.get('depth', 180) * np.exp(-t / p.get('settle', 0.15)) * np.cos(TAU * p.get('speed', 6) * t)
        phase = TAU * np.cumsum(f) / SR
        sound = (np.sin(phase) + 0.14 * np.sin(2 * phase)) * envelope(t, 0.002, p.get('decay', 0.12))
        for at in p.get('times', [0]):
            place(x, taper(sound), at)
    return room(x, 0.045, 0.06)


def retro(p):
    x = stereo(p.get('duration', 1.2))
    notes = p.get('notes', [880, 1320])
    gap = p.get('gap', 0.07)
    for i, f in enumerate(notes):
        d = p.get('length', 0.13)
        if p.get('points'):
            sound = gliss(d, p['points'], p.get('decay', 0.10), 0.003,
                          ((1, 1), (3, 0.22), (5, 0.075), (7, 0.03)))
        else:
            sound = tonal(f, d, p.get('decay', 0.065), 0.003,
                          ((1, 1), (3, 0.22), (5, 0.075), (7, 0.03)))
        place(x, taper(sound, 0.002, 0.015), i * gap, 1, 0.08 * (-1) ** i)
    return room(x, 0.025, 0.035)
