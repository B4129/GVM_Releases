import json

path = r'c:\Users\neko3\Desktop\agent\GVM\GVM_release\patch-notes.json'

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = []
for version_group in data:
    for update in version_group.get('updates', []):
        if 'sections' in update:
            for section in update['sections']:
                items.extend(section.get('items', []))
        elif 'content' in update:
            items.append(update['content'])

seen = set()
duplicates = []
for item in items:
    if item in seen:
        duplicates.append(item)
    seen.add(item)

if duplicates:
    print("Found duplicates in patch-notes.json:")
    for d in duplicates:
        print(f"- {d}")
else:
    print("No duplicates found in patch-notes.json.")
