const fs = require('fs');
const path = require('path');

const sfxDir = path.join(__dirname, '../sfx');
const outputFile = path.join(__dirname, '../sfx-list.json');

if (!fs.existsSync(sfxDir)) {
    console.error(`SFX directory not found: ${sfxDir}`);
    process.exit(1);
}

const categories = fs.readdirSync(sfxDir).filter(f => {
    return fs.statSync(path.join(sfxDir, f)).isDirectory();
});

const sfxList = [];

for (const category of categories) {
    const catPath = path.join(sfxDir, category);
    const files = fs.readdirSync(catPath).filter(f => {
        const ext = path.extname(f).toLowerCase();
        return ext === '.mp3' || ext === '.wav' || ext === '.ogg';
    });

    for (const file of files) {
        const id = `sfx-${category}-${path.basename(file, path.extname(file))}`.replace(/[^a-zA-Z0-9-_]/g, '_');
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
