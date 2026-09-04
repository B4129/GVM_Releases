"""Layered cinematic and transition sounds, synthesized without recordings."""
import numpy as np
import dsp
from dsp import SR, TAU, timeline, envelope, taper, tonal, color_noise, sweep_noise
from dsp import stereo, place, room
from voices import gliss, strike, bell


def whoosh(p):
    d = p.get('length', 0.42)
    x = stereo(p.get('duration', d + 0.28))
    t = timeline(d)
    u = t / d
    center = p.get('center', 0.42)
    shape = np.where(u < center, (u / center) ** p.get('curve', 1.9),
                     np.exp(-(u - center) / p.get('fall', 0.105)))
    noise = sweep_noise(d, p.get('start', 450), p.get('peak', 5800),
                        p.get('end', 350), center, p.get('width', 0.8))
    if p.get('flutter'):
        shape *= 0.68 + 0.32 * np.cos(TAU * p['flutter'] * t)
    pan = p.get('pan', [-0.4, 0.4])
    for at in p.get('times', [0]):
        place(x, taper(noise * shape, 0.006, 0.03), at, 0.8,
              np.linspace(pan[0], pan[-1], len(t)))
    if p.get('tone'):
        sound = gliss(d, p['tone'], p.get('tone_decay', 0.1), 0.02)
        place(x, sound, gain=p.get('tone_gain', 0.10))
    return room(x, p.get('room', 0.035), p.get('wet', 0.055))


def impact(p):
    x = stereo(p.get('duration', 0.85))
    d = p.get('length', 0.64)
    t = timeline(d)
    mode = p.get('material', 'soft')
    f = p.get('f', 90)
    for at, gain in zip(p.get('times', [0]), p.get('gains', [1])):
        sound = strike(d, f, p.get('decay', 0.075), p.get('noise', 0.24), mode,
                       p.get('start', f * 2.1))
        place(x, sound, at, gain)
        noise = color_noise(d, p.get('low', 150), p.get('high', 4500))
        place(x, noise * envelope(t, 0.0015, p.get('noise_decay', 0.025)),
              at, gain * p.get('texture', 0.18))
        if p.get('clap'):
            for delay in [0.005, 0.014, 0.023]:
                clap = color_noise(0.18, 700, 6700) * envelope(timeline(0.18), 0.0007, 0.012)
                place(x, clap, at + delay, gain * 0.22)
    return room(x, p.get('room', 0.065), p.get('wet', 0.09))


def transition(p):
    mode = p.get('mode', 'riser')
    d = p.get('length', 1.2)
    x = stereo(p.get('duration', d + 0.45))
    t = timeline(d)
    u = t / d
    if mode == 'tape':
        f = p.get('f', 520) * np.maximum(0.09, (1 - u) ** 1.7)
        phase = TAU * np.cumsum(f) / SR
        tonal = np.sin(phase) + 0.20 * np.sin(2 * phase) + 0.055 * np.sin(3 * phase)
        shape = np.sin(np.minimum(u / 0.025, 1) * np.pi / 2) ** 2 * (1 - u) ** 0.7
        place(x, taper(tonal * shape, 0.01, 0.07), gain=0.5)
    elif mode == 'glitch':
        for i, at in enumerate([0, 0.045, 0.105, 0.185, 0.31, 0.38]):
            n = 0.045 if i % 2 else 0.028
            noise = color_noise(n, 400 + 150 * i, 6200)
            place(x, taper(noise, 0.002, 0.008), at, 0.11, 0.18 * (-1) ** i)
            tone = gliss(n, [600 + i * 180, 1000 + i * 120], 0.015)
            place(x, tone, at, 0.20)
    else:
        center = p.get('center', 0.91 if mode == 'riser' else 0.12)
        if mode == 'reverse':
            shape = np.sin(np.pi * u / 2) ** 2.6
        elif mode == 'down':
            shape = (1 - np.exp(-t / 0.025)) * np.exp(-t / (d * 0.19))
        else:
            shape = np.where(u < center, (u / center) ** 2.2,
                             np.exp(-(u - center) / 0.035))
        sound = sweep_noise(d, p.get('start', 250), p.get('peak', 5800),
                            p.get('end', 450), center, p.get('width', 0.82))
        place(x, taper(sound * shape, 0.012, p.get('release', 0.025)), gain=0.65,
              pan=np.linspace(-0.27, 0.27, len(t)))
        points = p.get('tone', [160, 260, 470, 720])
        phase = TAU * np.cumsum(np.interp(u, np.linspace(0, 1, len(points)), points)) / SR
        place(x, np.sin(phase) * shape, gain=p.get('tone_gain', 0.08))
        if p.get('bell'):
            place(x, bell(0.72, p['bell'], 0.11), max(0, d - 0.025), 0.3)
        if p.get('hit'):
            place(x, strike(0.65, 85, 0.06, 0.17, 'soft', 160), max(0, d - 0.03), 0.48)
    return room(x, p.get('room', 0.065), p.get('wet', 0.08))


def sparkle(p):
    x = stereo(p.get('duration', 1.6))
    notes = p.get('notes', [1320, 1980, 2640])
    times = p.get('times', [i * p.get('gap', 0.10) for i in range(len(notes))])
    for i, (at, f) in enumerate(zip(times, notes)):
        place(x, bell(min(1.4, len(x) / SR - at), f, p.get('decay', 0.16)), at,
              p.get('gains', [0.83 ** i for i in range(len(notes))])[i],
              np.linspace(-0.32, 0.32, len(notes))[i])
    if p.get('air'):
        d = min(0.75, len(x) / SR)
        t = timeline(d)
        place(x, color_noise(d, 4500, 13000) * np.sin(np.pi * t / d) ** 2,
              gain=p['air'])
    if p.get('swell'):
        d = 0.75
        t = timeline(d)
        env = np.sin(np.pi * t / d) ** 2
        pad = sum(np.sin(TAU * f * t) for f in [440, 554.365, 659.255])
        place(x, pad * env, gain=0.055)
    return room(x, p.get('room', 0.11), p.get('wet', 0.14))


def texture(p):
    x = stereo(p.get('duration', 0.9))
    mode = p.get('mode', 'paper')
    d = p.get('length', 0.3)
    for j, at in enumerate(p.get('times', [0])):
        t = timeline(d)
        noise = color_noise(d, p.get('low', 600), p.get('high', 7200), p.get('tilt', -0.2))
        if mode == 'shaker':
            env = np.sin(np.pi * t / d) ** 1.5
            flutter = 0.35 + 0.65 * np.sin(TAU * p.get('speed', 35) * t) ** 2
            sound = noise * env * flutter
        else:
            env = np.sin(np.pi * t / d) ** p.get('curve', 1.8)
            grains = np.zeros_like(t)
            for at_grain in dsp.RNG.uniform(0.025, max(0.03, d - 0.025), 12):
                grains += np.exp(-((t - at_grain) / 0.002) ** 2) * float(dsp.RNG.uniform(0.1, 0.7))
            sound = noise * env * (0.4 + grains)
        place(x, taper(sound, 0.006, 0.025), at, 0.28, (-1) ** j * 0.16)
        if p.get('tap'):
            place(x, strike(0.1, 740, 0.01, 0.1), at + d * 0.77, 0.17)
    return room(x, 0.026, 0.04)
