const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const sfxDir = path.join(__dirname, '../sfx');
const outputFile = path.join(__dirname, '../sfx-list.json');

if (!fs.existsSync(sfxDir)) {
    console.error(`SFX directory not found: ${sfxDir}`);
    process.exit(1);
}

const categories = fs.readdirSync(sfxDir).filter(f => {
    return fs.statSync(path.join(sfxDir, f)).isDirectory();
});
// カテゴリ名を日本語の辞書順（50音順）にソート
categories.sort((a, b) => a.localeCompare(b, 'ja'));

const sfxList = [];

for (const category of categories) {
    const catPath = path.join(sfxDir, category);
    const files = fs.readdirSync(catPath).filter(f => {
        const ext = path.extname(f).toLowerCase();
        return ext === '.mp3' || ext === '.wav' || ext === '.ogg';
    });
    // ファイル名を数値順にナチュラルソート (1 -> 2 -> 10)
    files.sort((a, b) => {
        return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
    });

    for (const file of files) {
        const id = 'sfx-' + crypto.createHash('md5').update(`${category}-${file}`).digest('hex');
        const encodedCategory = encodeURIComponent(category);
        const encodedFile = encodeURIComponent(file);
        sfxList.push({
            id,
            name: file,
            category,
            url: `https://raw.githubusercontent.com/B4129/GVM_Releases/main/sfx/${encodedCategory}/${encodedFile}`
        });
    }
}

fs.writeFileSync(outputFile, JSON.stringify(sfxList, null, 2), 'utf8');
console.log(`Generated ${outputFile} with ${sfxList.length} SFX items.`);
