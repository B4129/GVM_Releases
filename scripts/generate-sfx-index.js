const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const AUDIO_EXTENSIONS = new Set(['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']);
const BASE_URL = 'https://raw.githubusercontent.com/B4129/GVM_Releases/main/sfx/';
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function segment(value) {
    assert.equal(typeof value, 'string', 'Path segment must be text');
    assert.ok(value && value === value.trim() && value !== '.' && value !== '..'
        && !/[<>:"/\\|?*\x00-\x1f]/.test(value) && !/[. ]$/.test(value), `Unsafe segment: ${value}`);
    return value;
}

function buildCatalog(root) {
    const registry = JSON.parse(fs.readFileSync(path.join(root, 'sfx-registry.json'), 'utf8'));
    assert.equal(registry.formatVersion, 1, 'Unsupported registry version');
    assert.ok(Array.isArray(registry.assets) && registry.assets.length <= 10000);
    const ids = new Set();
    const audioPaths = new Set();
    const labels = new Set();
    const numbers = new Set();
    const catalog = registry.assets.map(asset => {
        assert.ok(typeof asset.id === 'string' && /^[a-zA-Z0-9._-]{1,256}$/.test(asset.id)
            && !ids.has(asset.id), `Duplicate or invalid ID: ${asset.id}`);
        ids.add(asset.id);
        const category = segment(asset.category);
        const name = segment(asset.name);
        assert.ok(category.length <= 128 && name.length <= 255);
        assert.ok(AUDIO_EXTENSIONS.has(path.extname(name).toLowerCase()), `Unsupported audio: ${name}`);
        const label = path.basename(name, path.extname(name));
        if (asset.legacyName === true) {
            assert.match(name, /^\d+\.mp3$/, 'Only existing numbered MP3 names may be retained');
        } else {
            assert.ok([...label].length <= 20 && /^[^（）_]+（[^（）_]+）$/.test(label)
                && !/^GVM/i.test(label) && !/^\d/.test(label), `Use 用途（音の特徴）, at most 20 characters: ${label}`);
            const key = label.normalize('NFC').toLowerCase();
            assert.ok(!labels.has(key), `Duplicate display name: ${label}`);
            labels.add(key);
        }
        if (asset.presetNumber !== undefined) {
            assert.ok(Number.isSafeInteger(asset.presetNumber) && asset.presetNumber > 0
                && !numbers.has(asset.presetNumber), 'Duplicate or invalid preset number');
            numbers.add(asset.presetNumber);
        }
        if (asset.seed !== undefined) assert.match(asset.seed, /^\d+$/, 'Seed must be a lossless decimal string');
        assert.match(asset.sha256, /^[a-f0-9]{64}$/, 'Missing audio hash');
        assert.ok(asset.aliases === undefined || Array.isArray(asset.aliases));
        for (const filename of [name, ...(asset.aliases || [])]) {
            segment(filename);
            const relative = `${category}/${filename}`;
            const key = relative.normalize('NFC').toLowerCase();
            assert.ok(!audioPaths.has(key), `Duplicate audio path: ${relative}`);
            audioPaths.add(key);
            const bytes = fs.readFileSync(path.join(root, 'sfx', category, filename));
            assert.ok(bytes.length > 0 && bytes.length <= 64 * 1024 * 1024);
            assert.equal(hash(bytes), asset.sha256, `Audio changed: ${relative}`);
            if (asset.sizeBytes !== undefined) assert.equal(bytes.length, asset.sizeBytes, `Wrong size: ${relative}`);
        }
        if (asset.duration !== undefined) {
            assert.ok(Number.isFinite(asset.duration) && asset.duration > 0 && asset.duration <= 86400);
        }
        return {
            id: asset.id,
            name,
            category,
            url: `${BASE_URL}${encodeURIComponent(category)}/${encodeURIComponent(name)}`,
            ...(asset.duration === undefined ? {} : {duration: asset.duration}),
            ...(asset.sizeBytes === undefined ? {} : {sizeBytes: asset.sizeBytes}),
        };
    });
    // Old URLs remain on disk, but only the canonical entry appears in the app.
    for (const directory of fs.readdirSync(path.join(root, 'sfx'), {withFileTypes: true})) {
        if (!directory.isDirectory()) continue;
        for (const file of fs.readdirSync(path.join(root, 'sfx', directory.name), {withFileTypes: true})) {
            if (!file.isFile() || !AUDIO_EXTENSIONS.has(path.extname(file.name).toLowerCase())) continue;
            const relative = `${directory.name}/${file.name}`;
            assert.ok(audioPaths.has(relative.normalize('NFC').toLowerCase()), `Register audio before publishing: ${relative}`);
        }
    }
    return catalog.sort((a, b) => a.category.localeCompare(b.category, 'ja')
        || a.name.localeCompare(b.name, 'ja', {numeric: true}));
}

if (require.main === module) {
    const root = path.resolve(__dirname, '..');
    const catalog = buildCatalog(root);
    const output = path.join(root, 'sfx-list.json');
    fs.writeFileSync(output, JSON.stringify(catalog, null, 2) + '\n', 'utf8');
    console.log(`Generated ${output} with ${catalog.length} SFX items.`);
}

module.exports = {buildCatalog};
