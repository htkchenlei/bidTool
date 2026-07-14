import json
import os

from backend.markdown_converter import convert_to_markdown, detect_file_type

with open('data/project_files.json', 'r', encoding='utf-8') as f:
    project_files = json.load(f)

tender_files = [f for f in project_files 
                if f.get('storage_name', '').lower().endswith(('.docx', '.pdf'))]

print(f'Found {len(tender_files)} tender files')

if tender_files:
    t = tender_files[0]
    storage_path = t.get('storage_path')
    print(f'Testing: {storage_path}')
    print(f'Exists: {os.path.exists(storage_path)}')
    ft = detect_file_type(storage_path)
    print(f'File type: {ft}')
    
    result = convert_to_markdown(storage_path, ft)
    print(f'Success: {result["success"]}')
    print(f'Length: {len(result.get("markdown", ""))}')
    if 'error' in result:
        print(f'Error: {result["error"]}')
    if result.get('markdown'):
        print(f'First 500 chars:\n{result["markdown"][:500]}')
