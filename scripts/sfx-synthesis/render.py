"""Render the 100-sound expansion into an explicitly selected directory.

Requires Python 3 and NumPy. Example: python render.py --output ./rendered-pack
The approved first ten sample WAVs are retained separately without re-rendering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import dsp
import voices
import motion
from presets import PRESETS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--registry', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'sfx-registry.json')
    args = parser.parse_args()
    output = args.output.resolve()
    registry = json.loads(args.registry.read_text(encoding='utf-8'))
    assert registry['formatVersion'] == 1
    assets = {asset['presetNumber']: asset for asset in registry['assets'] if 'presetNumber' in asset}
    families = {name: getattr(module, name) for module, names in [
        (voices, ['pop', 'clicks', 'chime', 'reaction', 'retro']),
        (motion, ['whoosh', 'impact', 'transition', 'sparkle', 'texture'])]
        for name in names}
    records = []
    for preset in PRESETS:
        asset = assets[preset['number']]
        filename = asset['name']
        assert filename == f"{preset['name']}.wav" and asset['category'] == preset['category']
        # Preserve the published waveform when its customer-facing name changes.
        seed = int(asset['seed'])
        dsp.RNG = np.random.default_rng(seed)
        sound = families[preset['family']](preset['params'])
        sound = dsp.trim_tail(dsp.master(sound, rms_db=preset['level'], peak_db=-6))
        relative = Path('sfx') / preset['category'] / filename
        destination = output / relative
        dsp.write_wav(destination, sound)
        # Read serialized PCM for the authoritative metadata and checks.
        decoded = dsp.read_wav(destination)
        peak = dsp.interpolated_peak(decoded)
        mono = decoded.mean(axis=1)
        mono_loss = dsp.db(np.sqrt(np.mean(mono ** 2)) / np.sqrt(np.mean(decoded ** 2)))
        end_peak = dsp.db(np.max(np.abs(decoded[-960:])))
        assert np.isfinite(decoded).all(), filename
        assert peak <= 10 ** (-5.95 / 20), (filename, peak)
        assert np.max(np.abs(decoded)) > .025, filename
        assert np.max(np.abs(decoded.mean(axis=0))) < .00025, filename
        assert mono_loss > -2, (filename, mono_loss)
        assert end_peak < -60, (filename, end_peak)
        assert np.max(np.abs(decoded[:4])) == 0 and np.max(np.abs(decoded[-8:])) == 0
        data = destination.read_bytes()
        assert hashlib.sha256(data).hexdigest() == asset['sha256'], ('Published audio changed', filename)
        records.append(dict(number=preset['number'], name=filename,
            category=preset['category'], description=preset['description'],
            relativePath=relative.as_posix(), duration=round(len(decoded) / dsp.SR, 4),
            sizeBytes=len(data), sampleRate=dsp.SR, channels=2, bitDepth=24,
            sha256=hashlib.sha256(data).hexdigest(), seed=str(seed),
            family=preset['family'], estimatedTruePeakDbfs=round(dsp.db(peak), 3),
            peak50msRmsDbfs=round(dsp.db(dsp.short_rms(decoded)), 3),
            tail20msPeakDbfs=round(end_peak, 3), monoRmsChangeDb=round(mono_loss, 3)))
        if len(records) % 10 == 0:
            print(f"Rendered and checked {len(records)}/100: {preset['category']}", flush=True)
    assert len(set(record['sha256'] for record in records)) == 100
    (output / 'expansion-manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='passed', newSounds=len(records), totalBytes=sum(r['sizeBytes'] for r in records),
                         longestSeconds=max(r['duration'] for r in records)), ensure_ascii=False))


if __name__ == '__main__':
    main()
