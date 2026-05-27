from flask import Blueprint, request, jsonify
import os
import tempfile
import json
import requests
from docx import Document
from datetime import datetime

try:
    from pdfplumber import open as open_pdf
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

bid_assistant_bp = Blueprint('bid_assistant', __name__)

current_file = os.path.abspath(__file__)
parent_dir = os.path.dirname(current_file)  # routes
parent_dir = os.path.dirname(parent_dir)    # app  
parent_dir = os.path.dirname(parent_dir)    # backend
parent_dir = os.path.dirname(parent_dir)    # project root
DATA_DIR = os.path.join(parent_dir, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
PROJECTS_FILE = os.path.join(DATA_DIR, 'projects.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'ai_config.json')

DEFAULT_CONFIG = {
    "default_model": "deepseek",
    "models": {
        "deepseek": {
            "api_key": "",
            "api_base": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        },
        "aliyun": {
            "api_key": "",
            "api_base": "https://dashscope.aliyuncs.com/api/text/chat",
            "model": "qwen-max"
        },
        "volcengine": {
            "api_key": "",
            "api_base": "https://ark.cn-beijing.volces.com/api/text/chat",
            "model": "Doubao-3.5-128K"
        },
        "kimi": {
            "api_key": "",
            "api_base": "https://api.moonshot.cn/v1",
            "model": "moonshot-v1-8k"
        },
        "glm": {
            "api_key": "",
            "api_base": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "model": "glm-4"
        },
        "minimax": {
            "api_key": "",
            "api_base": "https://api.minimax.chat/v1/text/chatcompletion",
            "model": "abab6-chat"
        },
        "openai": {
            "api_key": "",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4o-mini"
        },
        "siliconflow": {
            "api_key": "",
            "api_base": "https://api.siliconflow.cn/v1",
            "model": "Qwen/Qwen-2-7B-Instruct"
        }
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                result = DEFAULT_CONFIG.copy()
                result['default_model'] = config.get('default_model', DEFAULT_CONFIG['default_model'])
                if 'models' in config:
                    for model_name in result['models']:
                        if model_name in config['models']:
                            result['models'][model_name].update(config['models'][model_name])
                return result
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_projects(projects):
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def extract_text_from_pdf(file_path):
    if not PDFPLUMBER_AVAILABLE:
        return ""
    try:
        with open_pdf(file_path) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                text += page_text + '\n\n--- Page Separator ---\n\n'
            print(f"PDF extraction completed, total chars: {len(text)}")
            return text
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

def fetch_url_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"URL fetch error: {e}")
        return ""

def call_ai_api(model_type, api_key, api_base, model_name, prompt, text_content):
    max_chars = 20000
    text_to_send = text_content[:max_chars]
    print(f"Sending {len(text_to_send)}/{len(text_content)} chars to AI")
    full_prompt = f"""{prompt}

招标公告内容：
{text_to_send}"""

    try:
        if model_type == 'deepseek':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1
            }
            response = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, timeout=120)
        
        elif model_type == 'aliyun':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "input": {"messages": [{"role": "user", "content": full_prompt}]},
                "parameters": {"temperature": 0.1}
            }
            response = requests.post(api_base, headers=headers, json=data, timeout=120)
        
        elif model_type == 'volcengine':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1
            }
            response = requests.post(api_base, headers=headers, json=data, timeout=120)
        
        elif model_type == 'kimi':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1
            }
            response = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, timeout=120)
        
        elif model_type == 'glm':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1
            }
            response = requests.post(api_base, headers=headers, json=data, timeout=120)
        
        elif model_type == 'minimax':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1,
                "tokens_to_generate": 4096
            }
            response = requests.post(api_base, headers=headers, json=data, timeout=120)
        
        elif model_type == 'openai':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1
            }
            response = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, timeout=120)
        
        elif model_type == 'siliconflow':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.1
            }
            response = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, timeout=120)
        
        else:
            return None, f"不支持的模型类型: {model_type}"

        response.raise_for_status()
        result = response.json()

        if model_type == 'deepseek' or model_type == 'kimi' or model_type == 'openai' or model_type == 'siliconflow':
            content = result['choices'][0]['message']['content']
        elif model_type == 'aliyun':
            content = result['output']['choices'][0]['message']['content']
        elif model_type == 'volcengine':
            content = result['choices'][0]['message']['content']
        elif model_type == 'glm':
            content = result['choices'][0]['message']['content']
        elif model_type == 'minimax':
            content = result['reply']
        else:
            content = str(result)

        return content, None

    except Exception as e:
        return None, str(e)

def parse_with_ai(text_content):
    config = load_config()
    default_model = config['default_model']
    model_config = config['models'].get(default_model, {})
    api_key = model_config.get('api_key', '')
    api_base = model_config.get('api_base', '')
    model_name = model_config.get('model', '')

    if not api_key or not api_base:
        return None, f"请先配置{default_model}模型的API密钥"

    prompt = """你是一个专业的招投标文档解析专家。请从以下招标公告文本中提取关键信息，严格按照JSON格式输出，不要添加任何额外的解释性文字。

输出格式要求：
```json
{
  "projectName": "项目名称",
  "projectCode": "项目编号",
  "budgetAmount": "预算金额",
  "bidDate": "YYYY年MM月DD日",
  "bidTime": "HH:MM",
  "bidderName": "招标人名称",
  "agencyName": "代理机构名称",
  "disqualificationItems": ["废标项1", "废标项2", "..."],
  "evaluationCriteria": ["评分项1及分值", "评分项2及分值", "..."],
  "otherInfo": "其他信息"
}
```

需要提取的详细信息：
1. projectName: 项目名称（如果存在多个项目，提取最主要的一个）
2. projectCode: 项目编号（招标编号）
3. budgetAmount: 预算金额（项目总预算或最高限价）
4. bidDate: 开标日期，格式必须是YYYY年MM月DD日，如果找不到则为空字符串
5. bidTime: 开标时间，格式必须是HH:MM，如果找不到则为空字符串
6. bidderName: 招标人（招标单位）名称
7. agencyName: 招标代理机构名称
8. disqualificationItems: 废标条款列表，仔细查找所有可能导致废标的条款，如资格审查不合格、文件格式错误、逾期提交、保证金问题等，找不到则返回空数组[]
9. evaluationCriteria: 评分标准列表，仔细查找技术评分、商务评分、价格评分等各项评分标准及其分值或权重，包括技术方案、人员配备、业绩经验、售后服务、投标报价等方面，找不到则返回空数组[]
10. otherInfo: 其他重要信息，如最高限价、项目地点、联系人及电话、招标文件获取时间等

注意事项：
- 评分标准和废标条款通常在文档的后面部分，请仔细查找
- 如果某项信息确实不存在，对应字段返回空字符串""或空数组[]
- 严格输出JSON格式，不要包含markdown代码块标记
- 确保JSON格式正确，引号使用双引号，逗号正确使用"""

    content, error = call_ai_api(default_model, api_key, api_base, model_name, prompt, text_content)
    if error:
        return None, error

    try:
        return json.loads(content), None
    except json.JSONDecodeError:
        return None, "AI返回的内容不是有效的JSON格式"

@bid_assistant_bp.route('/api/bid-assistant/parse', methods=['POST'])
def parse_document():
    try:
        print("=== Parse request received ===")
        url = request.form.get('url', '')
        file = request.files.get('file')
        
        print(f"URL: {url[:100] if url else 'None'}")
        print(f"File: {file.filename if file else 'None'}")

        if not url and not file:
            print("Error: No URL or file provided")
            return jsonify({'success': False, 'message': '请提供招标公告URL或上传文件'}), 400

        text_content = ""

        if url:
            print("Fetching URL content...")
            text_content = fetch_url_content(url)
            print(f"URL content fetched: {len(text_content)} chars")
        
        if file:
            filename = file.filename.lower()
            print(f"Processing file: {filename}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                if filename.endswith('.docx'):
                    text_content += extract_text_from_docx(temp_path)
                elif filename.endswith('.pdf'):
                    text_content += extract_text_from_pdf(temp_path)
                elif filename.endswith('.doc'):
                    text_content = "DOC格式文件解析需要安装额外组件"
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        print(f"Total text content: {len(text_content)} chars")
        
        if not text_content.strip():
            print("Error: No content extracted")
            return jsonify({'success': False, 'message': '无法从URL或文件中提取内容'}), 400

        print("Calling AI parser...")
        parsed_result, error = parse_with_ai(text_content)
        if error:
            print(f"AI parsing error: {error}")
            return jsonify({'success': False, 'message': f'AI解析失败: {error}'}), 500

        if parsed_result is None:
            print("Error: AI returned empty result")
            return jsonify({'success': False, 'message': 'AI解析返回空结果'}), 500

        print("Parse successful!")
        return jsonify({
            'success': True,
            'projectName': parsed_result.get('projectName', ''),
            'result': {
                'projectCode': parsed_result.get('projectCode', ''),
                'budgetAmount': parsed_result.get('budgetAmount', ''),
                'bidDate': parsed_result.get('bidDate', ''),
                'bidTime': parsed_result.get('bidTime', ''),
                'bidderName': parsed_result.get('bidderName', ''),
                'agencyName': parsed_result.get('agencyName', ''),
                'disqualificationItems': parsed_result.get('disqualificationItems', []),
                'evaluationCriteria': parsed_result.get('evaluationCriteria', []),
                'otherInfo': parsed_result.get('otherInfo', '')
            }
        })

    except Exception as e:
        print(f"Parse error: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'解析失败: {str(e)}'}), 500

@bid_assistant_bp.route('/api/bid-assistant/save', methods=['POST'])
def save_project():
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': '缺少项目名称'}), 400

        projects = load_projects()
        
        new_project = {
            'id': len(projects) + 1,
            'name': data['name'],
            'projectCode': data.get('projectCode', ''),
            'budgetAmount': data.get('budgetAmount', ''),
            'bidDate': data.get('bidDate', ''),
            'bidTime': data.get('bidTime', ''),
            'bidderName': data.get('bidderName', ''),
            'agencyName': data.get('agencyName', ''),
            'disqualificationItems': data.get('disqualificationItems', '[]'),
            'evaluationCriteria': data.get('evaluationCriteria', '[]'),
            'otherInfo': data.get('otherInfo', ''),
            'created_at': datetime.now().isoformat()
        }

        projects.append(new_project)
        save_projects(projects)

        return jsonify({'success': True, 'message': '保存成功'})

    except Exception as e:
        print(f"Save error: {e}")
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500

@bid_assistant_bp.route('/api/bid-assistant/projects', methods=['GET'])
def get_projects():
    try:
        projects = load_projects()
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        print(f"Get projects error: {e}")
        return jsonify({'success': False, 'message': f'获取项目列表失败: {str(e)}'}), 500

@bid_assistant_bp.route('/api/bid-assistant/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    try:
        projects = load_projects()
        project = next((p for p in projects if p.get('deleted') != True and p['id'] == project_id), None)
        
        if project:
            return jsonify({'success': True, 'project': project})
        else:
            return jsonify({'success': False, 'message': '项目不存在'}), 404
    except Exception as e:
        print(f"Get project error: {e}")
        return jsonify({'success': False, 'message': f'获取项目详情失败: {str(e)}'}), 500

@bid_assistant_bp.route('/api/bid-assistant/projects/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    try:
        projects = load_projects()
        project = next((p for p in projects if p.get('deleted') != True and p['id'] == project_id), None)
        
        if not project:
            return jsonify({'success': False, 'message': '项目不存在'}), 404
        
        project['deleted'] = True
        project['deleted_at'] = datetime.now().isoformat()
        save_projects(projects)
        
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        print(f"Delete project error: {e}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@bid_assistant_bp.route('/api/bid-assistant/config', methods=['GET'])
def get_config():
    try:
        config = load_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        print(f"Get config error: {e}")
        return jsonify({'success': False, 'message': f'获取配置失败: {str(e)}'}), 500

@bid_assistant_bp.route('/api/bid-assistant/config', methods=['POST'])
def update_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '缺少配置数据'}), 400
        
        config = load_config()
        
        if 'default_model' in data:
            config['default_model'] = data['default_model']
        
        if 'models' in data:
            for model_name, model_config in data['models'].items():
                if model_name in config['models']:
                    if isinstance(model_config, dict):
                        config['models'][model_name] = {**config['models'][model_name], **model_config}
        
        save_config(config)
        return jsonify({'success': True, 'message': '配置保存成功'})
    
    except Exception as e:
        print(f"Update config error: {e}")
        return jsonify({'success': False, 'message': f'保存配置失败: {str(e)}'}), 500