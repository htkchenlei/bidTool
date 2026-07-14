from backend.llm_client import call_llm, get_all_enabled_model_configs, get_active_model_config

print("=== Testing LLM ===")
print(f"Active model: {get_active_model_config()}")
print(f"All enabled models: {len(get_all_enabled_model_configs())}")

messages = [
    {"role": "system", "content": "你是一个专业的招标文件分析专家。"},
    {"role": "user", "content": "请简要说明什么是评分标准。"}
]

try:
    response = call_llm(messages, temperature=0.1, max_tokens=500)
    print(f"Response: {response[:500]}")
except Exception as e:
    print(f"Error: {str(e)[:500]}")
