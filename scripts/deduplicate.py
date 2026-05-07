import json

path = r'c:\Users\neko3\Desktop\agent\GVM\GVM_release\patch-notes.json'

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

seen_items = set()

# Process from oldest to newest (bottom to top)
for i in range(len(data) - 1, -1, -1):
    version_group = data[i]
    updates = version_group.get('updates', [])
    
    new_updates = []
    for update in updates:
        # Some updates are objects with 'title', 'category', 'sections'
        # Others might be flat? The API route handle both.
        # Let's handle both.
        
        if 'sections' in update:
            new_sections = []
            for section in update['sections']:
                new_items = []
                for item in section.get('items', []):
                    if item not in seen_items:
                        new_items.append(item)
                        seen_items.add(item)
                section['items'] = new_items
                if new_items:
                    new_sections.append(section)
            update['sections'] = new_sections
            if new_sections:
                new_updates.append(update)
        elif 'content' in update: # Flat format
            item = update['content']
            if item not in seen_items:
                seen_items.add(item)
                new_updates.append(update)
            else:
                # Duplicate
                pass
        else:
            new_updates.append(update)
            
    version_group['updates'] = new_updates

# Filter out empty version groups? 
# Maybe better to keep them but they will be empty.
# User asked "duplicated content", so empty versions are fine as placeholders.

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("De-duplicated patch-notes.json")
