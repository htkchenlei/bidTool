import json
from backend.markdown_converter import convert_to_markdown, detect_file_type
from backend.routes.bid_score import _extract_criteria_section, _build_criteria_extraction_messages, _parse_json_response, _normalize_criteria
from backend.llm_client import call_llm, get_all_enabled_model_configs, get_active_model_config

with open('data/project_files.json', 'r', encoding='utf-8') as f:
    project_files = json.load(f)

tender_files = [f for f in project_files 
                if f.get('storage_name', '').lower().endswith(('.docx', '.pdf'))]

if tender_files:
    t = tender_files[0]
    storage_path = t.get('storage_path')
    ft = detect_file_type(storage_path)
    result = convert_to_markdown(storage_path, ft)
    
    tender_content = result.get('markdown', '')
    
    criteria_section = _extract_criteria_section(tender_content)
    print(f"提取的评分标准章节长度: {len(criteria_section)} 字符")
    
    messages = _build_criteria_extraction_messages("请提取评分标准", tender_content)
    
    print("\n=== 尝试其他模型 ===")
    all_models = get_all_enabled_model_configs()
    print(f"可用模型: {[m.get('name') for m in all_models]}")
    
    for model_config in all_models:
        print(f"\n尝试模型: {model_config.get('name')}")
        try:
            response = call_llm(messages, temperature=0.0, max_tokens=4000, model_config=model_config)
            print(f"响应:\n{response[:800]}")
            
            parsed = _parse_json_response(response)
            if parsed and 'criteria' in parsed and parsed['criteria']:
                criteria_info = _normalize_criteria(parsed)
                print(f"\n成功！")
                print(f"总分: {criteria_info.get('total_max')}")
                for c in criteria_info.get('criteria', []):
                    print(f"  - {c.get('name')}: {c.get('max_score')}分 ({c.get('category')})")
                break
        except Exception as e:
            print(f"失败: {str(e)[:300]}")
