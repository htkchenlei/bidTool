"""
AI 提取模块
使用大模型从招标文件中提取字段和识别风险条款
"""
import os
import json
import re
from datetime import datetime

# 导入 LLM 客户端
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.llm_client import call_llm, get_active_model_config, get_all_enabled_model_configs


# 字段提取 Prompt 模板（增强版：支持多源内容交叉匹配）
FIELD_EXTRACTION_PROMPT = """你是一个专业的招标文件信息提取助手。请从以下招标文件内容中提取关键信息。

【重要说明】
你收到的内容可能包含多个来源：
1. 【公告网页内容】— 来自招标公告网页的 Markdown 格式内容（包含项目基本信息、时间节点、联系方式等）
2. 【投标文件】— 上传的正式招标文件（PDF/DOCX等解析后的文本）

请综合所有来源的信息进行提取和交叉验证：
- 如果同一字段在多个来源中都有提及，选择最完整、最准确的值
- 对于日期、金额等关键字段，优先使用投标文件中的正式数据，但可用公告网页信息补充
- 如果不同来源的信息有冲突，以投标文件为准并在备注中说明

需要提取的字段包括：
1. 项目名称 (project_name)
2. 项目编号 (project_no)
3. 标段或包号 (section_no)
4. 招标方式 (bidding_method)
5. 采购类型 (procurement_type)
6. 项目地点 (project_location)
7. 招标人或采购人 (purchaser)
8. 招标代理机构 (agency)
9. 招标人联系人 (purchaser_contact)
10. 招标人联系电话 (purchaser_phone)
11. 代理机构联系人 (agency_contact)
12. 代理机构联系电话 (agency_phone)
13. 电子邮箱 (email)
14. 预算金额 (budget_amount)
15. 最高限价 (max_price)
16. 招标控制价 (control_price)
17. 投标保证金金额 (bid_bond_amount)
18. 履约保证金 (performance_bond)
19. 公告发布时间 (announce_date)
20. 报名开始时间 (register_start)
21. 报名截止时间 (register_end)
22. 答疑或澄清截止时间 (clarify_end)
23. 保证金缴纳截止时间 (bond_deadline)
24. 投标截止时间 (bid_deadline)
25. 开标时间 (opening_time)
26. 报名地点或平台 (register_location)
27. 投标文件递交地点或平台 (submit_location)
28. 开标地点或平台 (opening_location)
29. 所属行业 (industry)

请以严格的 JSON 格式返回，格式如下：
{
  "project_name": "提取的值，如果未找到则填空字符串",
  "project_no": "",
  ...
}

注意：
1. 只返回 JSON，不要包含任何其他文本或解释
2. 日期统一转换为 YYYY-MM-DD 格式
3. 金额提取数字和单位，如 "100万元"
4. 电话号码保持原格式
5. 如果某项信息无法识别，对应的值填空字符串"""


RISK_EXTRACTION_PROMPT = """你是一个专业的招标文件风险分析助手。请从以下招标文件内容中识别可能导致废标、否决投标或无效投标的风险条款。

【重要说明】
你收到的内容可能包含多个来源：
1. 【公告网页内容】— 来自招标公告网页（包含资格要求、时间节点、联系方式等公开信息）
2. 【投标文件】— 上传的正式招标文件（包含详细的技术要求、评标标准、合同条款等）

请综合所有来源的信息进行风险识别：
- 公告网页通常包含资格审查、报名要求等前置条件
- 投标文件包含详细的技术规范、评标办法、废标条款等
- 两个来源都可能有风险条款，需要全面覆盖

请识别以下类型的风险：
1. 明确包含"废标"、"否决投标"、"无效投标"、"投标无效"的条款
2. 资格审查中的硬性要求
3. 符合性审查中的否决条款
4. 带 ★、*、▲ 等特殊标记的实质性条款
5. 说明为"实质性要求"、"不得负偏离"、"必须满足"的条款
6. 签字盖章、密封、递交要求
7. 保证金缴纳要求
8. 报价不得超过最高限价要求
9. 服务期限、交付期要求
10. 人员配置、项目负责人要求
11. 业绩证明要求
12. 等保、密评、信创、国产化要求

请以严格的 JSON 数组格式返回，格式如下：
[
  {
    "title": "风险条款简短标题（20字以内）",
    "category": "风险类别（从以下选择：明确废标/否决投标、资格审查不通过、符合性审查不通过、特殊标记实质性条款、不允许负偏离、签字盖章要求、密封和递交要求、投标保证金要求、报价和最高限价要求、服务期限或交付期要求、运维响应要求、源代码知识产权数据归属要求、等保密评信创国产化要求、人员配置或项目负责人要求、业绩证明或案例要求、其他需关注条款）",
    "severity": "严重程度（high/medium/low/unknown）",
    "original_text": "原文内容（完整引用）",
    "trigger_reason": "触发原因说明"
  }
]

注意：
1. 只返回 JSON 数组，不要包含任何其他文本
2. severity 判断标准：
   - high: 原文明确说明不满足会废标、否决投标、投标无效
   - medium: 原文说明必须满足、不得负偏离、实质性响应
   - low: 需要关注但不一定导致废标
   - unknown: 条款后果不明确
3. original_text 必须是原文完整引用，不要修改或概括"""


def _extract_key_sections(text, max_chars=60000):
    """
    智能文本选择：如果文本过长，优先保留包含关键字的段落
    策略：
    1. 保留开头 5000 字符（通常包含项目基本信息）
    2. 搜索关键字相关段落，每类关键字保留 ±500 字符上下文
    3. 从文本末尾保留 3000 字符（通常包含重要截止日期、联系方式等）
    """
    if len(text) <= max_chars:
        return text

    keywords = {
        "budget": ["预算金额", "预算", "最高限价", "最高投标限价", "控制价", "万元", "采购预算"],
        "amount": ["保证金", "履约保证金", "元", "金额"],
        "deadline": ["投标截止", "开标时间", "截止时间", "截止日期", "报名截止", "获取文件", "澄清截止", "答疑截止"],
        "contact": ["采购人", "采购代理", "联系人", "联系电话", "联系方式", "地址"],
        "requirement": ["★", "*", "实质性", "废标", "否决投标", "无效投标", "不得", "必须满足"],
        "project": ["项目名称", "项目编号", "采购项目", "招标项目"],
    }

    context_window = 800
    segments = []

    # 开头 5000 字符
    segments.append(("--- 文档开头 ---", text[:5000]))

    # 搜索关键字并保留上下文
    found_positions = set()
    for category, kws in keywords.items():
        for kw in kws:
            pos = 0
            while True:
                idx = text.find(kw, pos)
                if idx == -1:
                    break
                # 避免重叠 - 如果此位置已被包含在另一个段中则跳过
                already_covered = any(abs(idx - p) < context_window for p in found_positions)
                if not already_covered:
                    start = max(0, idx - context_window)
                    end = min(len(text), idx + context_window)
                    segments.append((f"--- [{category}] '{kw}' at pos {idx} ---", text[start:end]))
                    found_positions.add(idx)
                pos = idx + len(kw)
                if len(segments) > 40:  # 防止段过多
                    break
            if len(segments) > 40:
                break
        if len(segments) > 40:
            break

    # 文本末尾 3000 字符
    if len(text) > 3000:
        segments.append(("--- 文档末尾 ---", text[-3000:]))

    # 合并所有段
    combined = ""
    for label, content in segments:
        combined += f"\n\n{label}\n{content}\n"

    # 如果合并后仍过长，再次截断
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n...(内容过长已做智能截取)"
    else:
        combined += "\n(已采用关键字优先方式截取关键信息)"

    return combined.strip()


def _call_llm_with_fallback(messages, temperature=0.1, max_tokens=1000):
    """
    调用 LLM，如果激活模型失败则自动回退到其他已启用的模型
    返回: (response_text: str, used_model_name: str)
    抛出异常时包含详细错误信息和可用模型列表
    """
    active_model = get_active_model_config()
    all_models = get_all_enabled_model_configs()

    if not all_models:
        raise RuntimeError("未配置或启用任何大模型，请先在设置中配置并启用一个模型")

    last_error = None
    failed_models = []

    if active_model:
        try:
            response = call_llm(messages, temperature=temperature, max_tokens=max_tokens, model_config=active_model)
            return response, active_model.get("name", active_model.get("model", "unknown"))
        except Exception as e:
            last_error = e
            failed_models.append({"id": active_model.get("id"), "name": active_model.get("name"), "error": str(e)[:200]})

    for cfg in all_models:
        if active_model and cfg.get("id") == active_model.get("id"):
            continue
        try:
            response = call_llm(messages, temperature=temperature, max_tokens=max_tokens, model_config=cfg)
            return response, cfg.get("name", cfg.get("model", "unknown"))
        except Exception as e:
            last_error = e
            failed_models.append({"id": cfg.get("id"), "name": cfg.get("name"), "error": str(e)[:200]})
            continue

    available_models = [{"id": m.get("id"), "name": m.get("name")} for m in all_models]
    raise RuntimeError(
        f"所有模型均调用失败。\n最后一个错误: {last_error}\n"
        f"可用模型: {json.dumps(available_models, ensure_ascii=False)}"
    )


def extract_fields_with_ai(text, project_id=None):
    """
    使用 AI 从文本中提取字段（含多模型自动回退）
    返回: {"success": True, "fields": {...}} 或 {"success": False, "message": "..."}
    """
    # 智能文本选择
    processed_text = _extract_key_sections(text, max_chars=60000)

    messages = [
        {"role": "system", "content": FIELD_EXTRACTION_PROMPT},
        {"role": "user", "content": f"请从以下招标文件内容中提取关键信息：\n\n{processed_text}"}
    ]

    try:
        response, model_name = _call_llm_with_fallback(messages, temperature=0.1, max_tokens=4000)
        fields = _parse_json_response(response)

        if fields:
            return {"success": True, "fields": fields}
        else:
            return {"success": False, "message": f"AI ({model_name}) 返回格式解析失败"}

    except Exception as e:
        return {"success": False, "message": f"AI 调用失败: {str(e)}"}


def extract_risks_with_ai(text, project_id=None):
    """
    使用 AI 从文本中识别风险条款（含多模型自动回退）
    返回: {"success": True, "risks": [...]} 或 {"success": False, "message": "..."}
    """
    # 智能文本选择
    processed_text = _extract_key_sections(text, max_chars=60000)

    messages = [
        {"role": "system", "content": RISK_EXTRACTION_PROMPT},
        {"role": "user", "content": f"请从以下招标文件内容中识别风险条款：\n\n{processed_text}"}
    ]

    try:
        response, model_name = _call_llm_with_fallback(messages, temperature=0.1, max_tokens=8000)
        risks = _parse_json_array_response(response)

        if risks is not None:
            return {"success": True, "risks": risks}
        else:
            return {"success": False, "message": f"AI ({model_name}) 风险返回格式解析失败"}

    except Exception as e:
        return {"success": False, "message": f"AI 调用失败: {str(e)}"}


def _parse_json_response(response):
    """从大模型响应中解析 JSON — 多重策略确保成功"""
    if not response or not response.strip():
        return None

    text = response.strip()

    # --- 策略1：提取 ```json ... ``` 代码块 ---
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    # --- 策略2：在完整文本中找第一个 { 和最后一个 } ---
    if text.strip() and not text.strip().startswith("{"):
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace >= 0 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1]

    # --- 策略3：尝试直接 JSON 解析 ---
    try:
        data = json.loads(text)
        if isinstance(data, dict) and len(data) > 0:
            return data
    except json.JSONDecodeError:
        pass

    # --- 策略4：尝试清理常见格式问题后再解析 ---
    # 移除尾部逗号 (JSON 不允许 trailing comma)
    cleaned = re.sub(r',\s*}', '}', text)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and len(data) > 0:
            return data
    except json.JSONDecodeError:
        pass

    # --- 策略5：正则表达式逐个字段提取（覆盖全部31个字段） ---
    # 匹配 "field_key": "value" 格式，值可以包含转义引号和中文
    all_field_keys = [
        "project_name", "project_no", "section_no", "bidding_method",
        "procurement_type", "project_location", "purchaser", "agency",
        "purchaser_contact", "purchaser_phone", "agency_contact",
        "agency_phone", "email", "budget_amount", "max_price",
        "control_price", "bid_bond_amount", "performance_bond",
        "announce_date", "register_start", "register_end", "clarify_end",
        "bond_deadline", "bid_deadline", "opening_time",
        "register_location", "submit_location",
        "opening_location", "industry",
    ]

    result = {}
    for key in all_field_keys:
        # 匹配 "key": "value" - 支持中文、标点、括号、转义引号等
        pattern = r'"' + re.escape(key) + r'"\s*:\s*"((?:[^"\\]|\\.)*)"'
        match = re.search(pattern, response)
        if match:
            val = match.group(1).strip()
            # 取消转义
            val = val.replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
            if val:
                result[key] = val

    return result if result else None


def _parse_json_array_response(response):
    """从大模型响应中解析 JSON 数组（风险条款等）— 多重策略"""
    if not response or not response.strip():
        return None

    text = response.strip()

    # --- 策略1：提取 ```json ... ``` 代码块 ---
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    # --- 策略2：尝试直接解析为 JSON 数组 ---
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # 模型可能返回 { "risks": [...], "items": [...] } 等
            for key in ["risks", "items", "risk_items", "data", "list", "result"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
    except json.JSONDecodeError:
        pass

    # --- 策略3：在文本中查找第一个 [ 和最后一个 ] ---
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket >= 0 and last_bracket > first_bracket:
        candidate = text[first_bracket:last_bracket + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # --- 策略4：清理尾部逗号后重试 ---
    if first_bracket >= 0 and last_bracket > first_bracket:
        candidate = text[first_bracket:last_bracket + 1]
        cleaned = re.sub(r',\s*]', ']', candidate)
        cleaned = re.sub(r',\s*}', '}', cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ["risks", "items", "risk_items", "data", "list"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
        except json.JSONDecodeError:
            pass

    # --- 策略5：截断 JSON 恢复 — 大模型可能因 max_tokens 限制输出不完整 ---
    if first_bracket >= 0:
        candidate = text[first_bracket:] if last_bracket < 0 else text[first_bracket:last_bracket + 1]
        # 手动扫描，找最后一个完整的 {...} 对象
        # candidate 以 [ 开头，深度 = 0 表示在数组级；遇到对象内 } 回到深度 0 表示对象完成
        depth = 0
        in_string = False
        escape_next = False
        last_complete_pos = -1
        for i, ch in enumerate(candidate):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    # 当深度回到 0（即回到数组级但未到数组结尾）时，上一个对象完成
                    # 检查：如果此 } 后面跟着 , 或 whitespace 则是对象间分隔
                    if depth == 0:
                        last_complete_pos = i

        if last_complete_pos > 0:
            recovered = "[" + candidate[1:last_complete_pos + 1] + "]"
            try:
                data = json.loads(recovered)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                pass

    return None


def analyze_document_full(text, project_id=None):
    """
    完整分析文档：提取字段 + 识别风险
    """
    result = {
        "fields": {},
        "risks": [],
        "field_success": False,
        "risk_success": False,
        "errors": []
    }

    # 提取字段
    field_result = extract_fields_with_ai(text, project_id)
    if field_result["success"]:
        result["fields"] = field_result["fields"]
        result["field_success"] = True
    else:
        result["errors"].append(f"字段提取失败: {field_result.get('message', '')}")

    # 识别风险
    risk_result = extract_risks_with_ai(text, project_id)
    if risk_result["success"]:
        result["risks"] = risk_result["risks"]
        result["risk_success"] = True
    else:
        result["errors"].append(f"风险识别失败: {risk_result.get('message', '')}")

    return result
