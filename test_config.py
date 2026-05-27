import os
import json

DATA_DIR = r'D:\Python\bidTool\data'
CONFIG_FILE = os.path.join(DATA_DIR, 'ai_config.json')

print('DATA_DIR:', DATA_DIR)
print('CONFIG_FILE:', CONFIG_FILE)
print('Exists:', os.path.exists(CONFIG_FILE))

# Test saving
config = {
    'default_model': 'deepseek',
    'models': {
        'deepseek': {
            'api_key': 'test123',
            'api_base': 'https://api.deepseek.com/v1',
            'model': 'deepseek-chat'
        }
    }
}

print('\nSaving config...')
with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print('Saved successfully')

# Test reading
print('\nReading config...')
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    content = f.read()
    print('Content:', content)