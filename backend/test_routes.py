import sys
import os

os.chdir('D:\\Python\\bidTool\\backend')

# 直接导入app.py文件
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)

print('Routes:')
for rule in app_module.app.url_map.iter_rules():
    print(f'  {rule}')