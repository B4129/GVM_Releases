const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {buildCatalog} = require('./generate-sfx-index');

function fixture(t) {
    const temporary = path.resolve('.tmp');
    fs.mkdirSync(temporary, {recursive: true});
    const root = fs.mkdtempSync(path.join(temporary, 'sfx-index-test-'));
    t.after(() => {
        assert.ok(root.startsWith(temporary + path.sep));
        fs.rmSync(root, {recursive: true, force: true});
    });
    const bytes = Buffer.from('unchanged audio payload');
    const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
    const asset = {id: 'sfx-stable-id', category: '通知', name: '通知（ピコン）.wav',
        sha256, duration: .69, sizeBytes: bytes.length, aliases: ['GVM_003_通知_ピコン.wav']};
    const save = (assets = [asset]) => fs.writeFileSync(path.join(root, 'sfx-registry.json'),
        JSON.stringify({formatVersion: 1, assets}), 'utf8');
    const audio = name => {
        const destination = path.join(root, 'sfx', asset.category, name);
        fs.mkdirSync(path.dirname(destination), {recursive: true});
        fs.writeFileSync(destination, bytes);
    };
    audio(asset.name); audio(asset.aliases[0]); save();
    return {root, asset, save, audio};
}

test('renaming retains the ID and metadata, encodes Japanese URLs, and hides old aliases', t => {
    const {root, asset} = fixture(t);
    const items = buildCatalog(root);
    assert.equal(items.length, 1);
    assert.equal(items[0].id, 'sfx-stable-id');
    assert.equal(items[0].name, '通知（ピコン）.wav');
    assert.equal(items[0].duration, .69);
    assert.equal(items[0].sizeBytes, asset.sizeBytes);
    assert.equal(decodeURIComponent(new URL(items[0].url).pathname),
        '/B4129/GVM_Releases/main/sfx/通知/通知（ピコン）.wav');
    assert.deepEqual(buildCatalog(root), items);
});

test('missing or changed old aliases block publication', t => {
    const {root, asset} = fixture(t);
    const alias = path.join(root, 'sfx', asset.category, asset.aliases[0]);
    fs.writeFileSync(alias, 'different audio');
    assert.throws(() => buildCatalog(root), /Audio changed/);
    fs.unlinkSync(alias);
    assert.throws(() => buildCatalog(root), /ENOENT/);
});

test('unregistered audio and duplicate stable IDs cannot silently enter the catalog', t => {
    const {root, asset, save, audio} = fixture(t);
    save([asset, asset]);
    assert.throws(() => buildCatalog(root), /Duplicate or invalid ID/);
    save(); audio('未登録（ポン）.wav');
    assert.throws(() => buildCatalog(root), /Register audio/);
});

test('customer names must be concise and paths cannot escape their category', t => {
    const {root, asset, save} = fixture(t);
    for (const name of ['GVM_003_通知_ピコン.wav', '通知.wav', '通知（あ'.padEnd(29, 'あ') + '）.wav']) {
        save([{...asset, name}]);
        assert.throws(() => buildCatalog(root), /Use 用途/);
    }
    save([{...asset, aliases: ['../outside.wav']}]);
    assert.throws(() => buildCatalog(root), /Unsafe segment/);
});

test('existing numbered assets retain the original catalog shape', t => {
    const {root, asset, save, audio} = fixture(t);
    audio('1.mp3');
    const legacy = {id: 'sfx-legacy', name: '1.mp3', category: asset.category,
        sha256: asset.sha256, legacyName: true};
    save([asset, legacy]);
    const item = buildCatalog(root).find(item => item.id === legacy.id);
    assert.deepEqual(Object.keys(item), ['id', 'name', 'category', 'url']);
    assert.equal(item.name, '1.mp3');
});
