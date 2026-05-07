const fs = require('fs');
const path = require('path');

const patchNotesDir = path.join(__dirname, '../patch-notes');
const outputFile = path.join(__dirname, '../patch-notes.json');

const files = fs.readdirSync(patchNotesDir).filter(f => (f.startsWith('v') || f === 'next.json') && f.endsWith('.json'));

const allNotes = files.map(file => {
    const content = fs.readFileSync(path.join(patchNotesDir, file), 'utf8');
    const data = JSON.parse(content);
    if (file === 'next.json') {
        data.version = 'next';
        data.isNext = true;
    }
    return data;
});

// バージョン順にソート（降順）
allNotes.sort((a, b) => {
    if (a.isNext) return -1;
    if (b.isNext) return 1;

    const va = a.version.split('.').map(Number);
    const vb = b.version.split('.').map(Number);
    for (let i = 0; i < Math.max(va.length, vb.length); i++) {
        const na = va[i] || 0;
        const nb = vb[i] || 0;
        if (na !== nb) return nb - na;
    }
    return 0;
});

fs.writeFileSync(outputFile, JSON.stringify(allNotes, null, 2), 'utf8');
console.log(`Generated ${outputFile} with ${allNotes.length} versions.`);
