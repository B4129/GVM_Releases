import os
import json

base_dir = r'c:\Users\neko3\Desktop\agent\GVM\GVM_Releases'
patch_notes_dir = os.path.join(base_dir, 'patch-notes')

# 修正対象のバージョン（2026-05-09 -> 2026-05-10 にしたいもの）
target_versions = [f'0.0.{i}' for i in range(226, 235)]

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    changed = False
    if isinstance(data, list):
        for item in data:
            if item.get('version') in target_versions and item.get('releaseDate') == '2026-05-09':
                item['releaseDate'] = '2026-05-10'
                changed = True
    elif isinstance(data, dict):
        if data.get('version') in target_versions and data.get('releaseDate') == '2026-05-09':
            data['releaseDate'] = '2026-05-10'
            changed = True
            
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Updated {filepath}')

# patch-notes.json を更新
update_file(os.path.join(base_dir, 'patch-notes.json'))

# 各個別ファイルを更新
for v in target_versions:
    filename = f'v{v}.json'
    filepath = os.path.join(patch_notes_dir, filename)
    if os.path.exists(filepath):
        update_file(filepath)
