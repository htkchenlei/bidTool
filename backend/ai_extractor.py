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
from backend.llm_client import call_llm, get_active_model_config


# 字段提取 Prompt 模板
FIELD_EXTRACTION_PROMPT = """你是一个专业的招标文件信息提取助手。请从以下招标文件内容中提取关键信息。

需要提取的字段包括：
1. 项目名称 (project_name)
2. 项目编号 (project_no)
3. 标段或包号 (section_no)
4. 招标方式 (bidding_method)
5. 采购类型 (procurement_type)
6. 采购内容摘要 (procurement_summary)
7. 项目地点 (project_location)
8. 资金来源 (fund_source)
9. 招标人或采购人 (purchaser)
10. 招标代理机构 (agency)
11. 招标人联系人 (purchaser_contact)
12. 招标人联系电话 (purchaser_phone)
13. 代理机构联系人 (agency_contact)
14. 代理机构联系电话 (agency_phone)
15. 电子邮箱 (email)
16. 预算金额 (budget_amount)
17. 最高限价 (max_price)
18. 投标保证金金额 (bid_bond_amount)
19. 保证金缴纳方式 (bid_bond_method)
20. 公告发布时间 (announce_date)
21. 报名截止时间 (register_end)
22. 招标文件获取截止时间 (doc_get_end)
23. 答疑或澄清截止时间 (clarify_end)
24. 投标截止时间 (bid_deadline)
25. 开标时间 (opening_time)
26. 报名地点或平台 (register_location)
27. 开标地点或平台 (opening_location)

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


def extract_fields_with_ai(text, project_id=None):
    """
    使用 AI 从文本中提取字段
    返回: {"success": True, "fields": {...}} 或 {"success": False, "message": "..."}
    """
    # 检查模型配置
    cfg = get_active_model_config()
    if not cfg:
        return {"success": False, "message": "未配置或启用大模型，请先在设置中配置并启用一个模型"}

    # 智能文本选择（原版本只截取前 12000 字符导致关键信息丢失）
    processed_text = _extract_key_sections(text, max_chars=60000)

    messages = [
        {"role": "system", "content": FIELD_EXTRACTION_PROMPT},
        {"role": "user", "content": f"请从以下招标文件内容中提取关键信息：\n\n{processed_text}"}
    ]

    try:
        response = call_llm(messages, temperature=0.1, max_tokens=2000)
        fields = _parse_json_response(response)

        if fields:
            return {"success": True, "fields": fields}
        else:
            return {"success": False, "message": "AI 返回格式解析失败"}

    except Exception as e:
        return {"success": False, "message": f"AI 调用失败: {str(e)}"}


def extract_risks_with_ai(text, project_id=None):
    """
    使用 AI 从文本中识别风险条款
    返回: {"success": True, "risks": [...]} 或 {"success": False, "message": "..."}
    """
    # 检查模型配置
    cfg = get_active_model_config()
    if not cfg:
        return {"success": False, "message": "未配置或启用大模型，请先在设置中配置并启用一个模型"}

    # 智能文本选择
    processed_text = _extract_key_sections(text, max_chars=60000)

    messages = [
        {"role": "system", "content": RISK_EXTRACTION_PROMPT},
        {"role": "user", "content": f"请从以下招标文件内容中识别风险条款：\n\n{processed_text}"}
    ]

    try:
        response = call_llm(messages, temperature=0.1, max_tokens=3000)
        risks = _parse_json_array_response(response)

        if risks is not None:
            return {"success": True, "risks": risks}
        else:
            return {"success": False, "message": "AI 返回格式解析失败"}

    except Exception as e:
        return {"success": False, "message": f"AI 调用失败: {str(e)}"}


def _parse_json_response(response):
    """解析 JSON 响应"""
    text = response.strip()

    # 尝试提取 JSON 块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试更宽松的解析
        result = {}
        patterns = [
            (r'"project_name"\s*:\s*"([^"]*)"', "project_name"),
            (r'"project_no"\s*:\s*"([^"]*)"', "project_no"),
            (r'"purchaser"\s*:\s*"([^"]*)"', "purchaser"),
            (r'"agency"\s*:\s*"([^"]*)"', "agency"),
            (r'"budget_amount"\s*:\s*"([^"]*)"', "budget_amount"),
            (r'"bid_deadline"\s*:\s*"([^"]*)"', "bid_deadline"),
            (r'"opening_time"\s*:\s*"([^"]*)"', "opening_time"),
        ]
        for pattern, key in patterns:
            match = re.search(pattern, response)
            if match:
                result[key] = match.group(1)
        return result if result else None


def _parse_json_array_response(response):
    """解析 JSON 数组响应"""
    text = response.strip()

    # 尝试提取 JSON 块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return None
    except json.JSONDecodeError:
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
