"""
投标比对 — 模拟评分 API Blueprint
- 选择已分析的招标项目，上传至少 3 份投标文件（支持更多）
- AI 根据招标文件中的评分标准对每家投标文件进行打分
- 技术部分内容查重检测，标出疑似重复
- 生成多文件对比评分报告（docx）供下载
- 结果不持久化：仅本次请求返回，刷新后清空
"""
import os
import io
import re
import json
import difflib
import tempfile
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file

bid_score_bp = Blueprint("bid_score", __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")

# 单个投标文件大小限制：200MB
MAX_BID_FILE_SIZE = 200 * 1024 * 1024
# 最多支持同时上传的投标文件数量
MAX_BID_FILES = 10
# 最少需要的投标文件数量
MIN_BID_FILES = 3


def _load_projects():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _get_tender_content(project_id):
    """读取项目已解析的招标文件内容"""
    parts = []
    project_parsed_dir = os.path.join(PARSED_DIR, project_id)

    md_path = os.path.join(project_parsed_dir, "announcement.md")
    if os.path.exists(md_path):
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md = f.read().strip()
            if md:
                parts.append("【公告网页内容】\n" + md)
        except Exception:
            pass

    if os.path.isdir(project_parsed_dir):
        for fname in sorted(os.listdir(project_parsed_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(project_parsed_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            text = (data.get("text") or "").strip()
            tables = data.get("tables") or []
            table_parts = []
            for idx, table in enumerate(tables):
                rows = []
                for row in table:
                    if isinstance(row, list):
                        rows.append(" | ".join(str(c) for c in row))
                    else:
                        rows.append(str(row))
                if rows:
                    table_parts.append("[表格" + str(idx + 1) + "]\n" + "\n".join(rows))
            if table_parts:
                text = (text + "\n\n" + "\n\n".join(table_parts)).strip()
            if text:
                parts.append("【招标文件解析内容】\n" + text)

    return "\n\n".join(parts)


def _truncate(text, max_chars):
    """文本过长时保留开头 75% 与结尾 25%"""
    if not text or len(text) <= max_chars:
        return text or ""
    head = int(max_chars * 0.75)
    tail = max_chars - head
    return (
        text[:head]
        + "\n\n…（内容过长，已截取开头与结尾部分，完整内容请参见原文件）…\n\n"
        + text[-tail:]
    )


def _extract_scoring_criteria(tender_content, user_prompt):
    """从招标文件中提取评分标准，若失败则使用默认维度"""
    from backend.ai_extractor import _call_llm_with_fallback, _parse_json_response

    system_prompt = (
        "你是一位专业的政府采购评审专家。请从提供的【招标文件内容】中提取评分标准的各项要求。"
        "只返回 JSON 对象本身，不要包含 ``` 代码块或任何解释文字。\n\n"
        "输出格式：\n"
        "{\n"
        '  "criteria": [\n'
        '    {"name": "评分项名称（如：技术方案、商务报价、项目业绩等）", "max_score": 该项满分},\n'
        '    ...\n'
        '  ],\n'
        '  "total_max": 总满分,\n'
        '  "raw_text": "原始评分标准文本摘录"\n'
        "}\n\n"
        "要求：\n"
        "1. 尽可能完整地提取招标文件中列出的所有评分项\n"
        "2. 若招标文件未明确给出评分项，criteria 返回空数组\n"
        "3. max_score 为数字，若是百分比请换算为实际分值\n"
        "4. raw_text 摘录招标文件中关于评分标准的原文"
    )

    user_content = (
        user_prompt
        + "\n\n==== 招标文件内容 ====\n" + _truncate(tender_content, 60000)
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response, model_name = _call_llm_with_fallback(messages, temperature=0.1, max_tokens=4000)
    except Exception:
        return None, None

    parsed = _parse_json_response(response)
    if not parsed or not isinstance(parsed, dict):
        return None, None

    criteria = parsed.get("criteria") or []
    if not isinstance(criteria, list) or not criteria:
        return None, None

    norm_criteria = []
    for c in criteria:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip()
        if not name:
            continue
        try:
            max_score = float(c.get("max_score", 0) or 0)
        except Exception:
            max_score = 0
        norm_criteria.append({"name": name, "max_score": max_score})

    if not norm_criteria:
        return None, None

    total_max = 0
    try:
        total_max = float(parsed.get("total_max", sum(c["max_score"] for c in norm_criteria)) or 0)
    except Exception:
        total_max = sum(c["max_score"] for c in norm_criteria)

    raw_text = str(parsed.get("raw_text", "")).strip()

    return {
        "criteria": norm_criteria,
        "total_max": total_max,
        "raw_text": raw_text,
    }, model_name


# 默认评分维度（当无法从招标文件提取评分标准时使用）
DEFAULT_CRITERIA = [
    {"name": "技术方案", "max_score": 30},
    {"name": "商务报价", "max_score": 20},
    {"name": "项目业绩", "max_score": 15},
    {"name": "团队资质", "max_score": 10},
    {"name": "服务承诺", "max_score": 10},
    {"name": "文件完整性", "max_score": 10},
    {"name": "其他评分项", "max_score": 5},
]
DEFAULT_TOTAL_MAX = 100


def _score_single_bid(bidder_index, bidder_name, bid_text, criteria_info, tender_content, model_extractor):
    """对单个投标文件进行 AI 打分"""
    from backend.ai_extractor import _call_llm_with_fallback, _parse_json_response

    criteria = criteria_info["criteria"]
    total_max = criteria_info["total_max"]

    criteria_text = "\n".join(
        f"    {i+1}. {c['name']}（满分 {c['max_score']} 分）"
        for i, c in enumerate(criteria)
    )

    system_prompt = (
        "你是一位专业的政府采购评审专家。请严格依据【评分标准】对【投标文件】进行逐项打分。"
        "只返回 JSON 对象本身，不要包含 ``` 代码块或任何解释文字。\n\n"
        "输出格式：\n"
        "{\n"
        f'  "bidder_index": {bidder_index},\n'
        '  "bidder_name": "' + bidder_name + '",\n'
        '  "scores": [\n'
        '    {"name": "评分项名称", "max_score": 满分, "score": 实际得分, "reason": "打分依据"},\n'
        '    ...\n'
        '  ],\n'
        f'  "total_score": 总得分（各项 score 之和），\n'
        f'  "total_max": {total_max},\n'
        '  "summary": "对该投标文件的整体评价（100字以内）",\n'
        '  "strengths": ["优势点1", ...],\n'
        '  "weaknesses": ["不足点1", ...]\n'
        "}\n\n"
        "要求：\n"
        "1. 严格按照评分标准中的评分项名称和满分进行打分\n"
        "2. 打分必须有充分依据，引用投标文件中的具体内容\n"
        "3. score 不得超过 max_score\n"
        "4. 若投标文件在某项评分标准下完全没有相关内容，score 为 0\n"
        "5. 打分要客观公正，不偏袒任何一方"
    )

    user_content = (
        "==== 评分标准 ====\n"
        f"总分满分：{total_max}\n"
        f"各项评分项：\n{criteria_text}\n\n"
        + "==== 投标文件（投标人：" + bidder_name + "）====\n"
        + bid_text
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response, model_name = _call_llm_with_fallback(messages, temperature=0.1, max_tokens=6000)
    except Exception as e:
        return None, str(e)

    parsed = _parse_json_response(response)
    if not parsed or not isinstance(parsed, dict):
        return None, "AI 响应解析失败"

    # 规范化结果
    raw_scores = parsed.get("scores") or []
    norm_scores = []
    for s in raw_scores:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name", "")).strip()
        max_s = 0
        try:
            max_s = float(s.get("max_score", 0) or 0)
        except Exception:
            pass
        score = 0
        try:
            score = float(s.get("score", 0) or 0)
        except Exception:
            pass
        reason = str(s.get("reason", "")).strip()
        norm_scores.append({
            "name": name,
            "max_score": max_s,
            "score": min(score, max_s),
            "reason": reason,
        })

    total_score = 0
    try:
        total_score = float(parsed.get("total_score", sum(s["score"] for s in norm_scores)) or 0)
    except Exception:
        total_score = sum(s["score"] for s in norm_scores)

    result = {
        "bidder_index": bidder_index,
        "bidder_name": bidder_name,
        "scores": norm_scores,
        "total_score": total_score,
        "total_max": float(parsed.get("total_max", total_max) or total_max),
        "summary": str(parsed.get("summary", "")).strip(),
        "strengths": [str(x).strip() for x in (parsed.get("strengths") or []) if str(x).strip()],
        "weaknesses": [str(x).strip() for x in (parsed.get("weaknesses") or []) if str(x).strip()],
    }

    return result, model_name


def _extract_technical_sections(text):
    """从投标文本中提取技术部分相关段落，用于查重检测"""
    lines = text.split("\n")
    tech_lines = []
    in_tech = False
    tech_keywords = ["技术方案", "技术实施", "技术路线", "系统架构", "功能模块", "技术指标",
                     "实施方案", "部署方案", "运维方案", "技术响应", "技术偏离",
                     "开发计划", "项目实施", "建设方案", "设计方案", "技术参数"]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_tech and tech_lines:
                tech_lines.append("")
            continue
        # 检测进入技术部分
        for kw in tech_keywords:
            if kw in stripped and len(stripped) < 20:
                in_tech = True
                break
        # 检测离开技术部分
        if in_tech and any(kw in stripped for kw in ["商务部分", "商务条款", "资格", "报价", "价格",
                                                     "第一部分", "第二部分", "第三部分", "四、", "五、"]):
            if len(stripped) < 15:
                in_tech = False
                continue
        if in_tech:
            tech_lines.append(stripped)

    tech_text = "\n".join(tech_lines).strip()
    # 若未检测到技术部分，退回到全文的前 60% 作为技术相关内容
    if len(tech_text) < 200:
        total = len(text)
        tech_text = text[:int(total * 0.6)]

    return tech_text


def _detect_plagiarism(bid_texts, bidder_names, threshold=0.5):
    """检测各投标文件技术部分的相似度"""
    n = len(bid_texts)
    plagiarism_results = []

    tech_texts = [_extract_technical_sections(t) for t in bid_texts]

    for i in range(n):
        for j in range(i + 1, n):
            t1 = tech_texts[i]
            t2 = tech_texts[j]

            if len(t1) < 100 or len(t2) < 100:
                continue

            # 使用 SequenceMatcher 计算相似度
            ratio = difflib.SequenceMatcher(None, t1[:50000], t2[:50000]).ratio()

            # 找出具体的重复段落
            s1_lines = t1.split("\n")
            s2_lines = t2.split("\n")
            matching_blocks = []

            # 将行作为基本单元进行比对
            sm = difflib.SequenceMatcher(
                None,
                [l for l in s1_lines if l.strip()],
                [l for l in s2_lines if l.strip()],
                autojunk=False
            )
            for block in sm.get_matching_blocks():
                if block.size >= 5:  # 至少 5 行连续匹配
                    i_start = block.a
                    j_start = block.b
                    size = block.size
                    lines_from_1 = [l for l in s1_lines if l.strip()][i_start:i_start + size]
                    lines_from_2 = [l for l in s2_lines if l.strip()][j_start:j_start + size]
                    if len(lines_from_1) >= 3:
                        matching_blocks.append({
                            "lines_from_1": lines_from_1[:8],
                            "lines_from_2": lines_from_2[:8],
                            "size": size,
                        })

            if ratio >= 0.3 or len(matching_blocks) >= 1:
                plagiarism_results.append({
                    "bidder_a": bidder_names[i],
                    "bidder_b": bidder_names[j],
                    "similarity": round(ratio, 3),
                    "level": "high" if ratio >= 0.6 else ("medium" if ratio >= 0.4 else "low"),
                    "matching_blocks": matching_blocks[:5],
                })

    return plagiarism_results


# ── 运行模拟评分 ───────────────────────────────────────────────
@bid_score_bp.route("/api/bid-score/run", methods=["POST"])
def run_bid_score():
    project_id = (request.form.get("project_id") or "").strip()
    prompt = (request.form.get("prompt") or "").strip()

    if not project_id:
        return jsonify({"success": False, "message": "请选择招标项目"}), 400
    if not prompt:
        return jsonify({"success": False, "message": "评分要求提示词不能为空"}), 400

    # 收集上传的投标文件
    files = []
    for key in sorted(request.files.keys()):
        f = request.files[key]
        if f and f.filename:
            files.append(f)

    if len(files) < MIN_BID_FILES:
        return jsonify({
            "success": False,
            "message": f"至少需要上传 {MIN_BID_FILES} 份投标文件，当前仅有 {len(files)} 份"
        }), 400
    if len(files) > MAX_BID_FILES:
        return jsonify({
            "success": False,
            "message": f"最多支持上传 {MAX_BID_FILES} 份投标文件"
        }), 400

    # 文件格式校验
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext != ".docx":
            return jsonify({
                "success": False,
                "message": f"所有投标文件必须为 .docx 格式，文件 {f.filename} 格式不符"
            }), 400

    # 总大小校验
    cl = request.content_length or 0
    if cl > MAX_BID_FILES * MAX_BID_FILE_SIZE + 50 * 1024 * 1024:
        return jsonify({"success": False, "message": f"文件总大小超过 {MAX_BID_FILES * 200}MB 限制"}), 413

    # 项目校验
    projects = _load_projects()
    project = next((p for p in projects if p.get("id") == project_id), None)
    if not project:
        return jsonify({"success": False, "message": "所选招标项目不存在"}), 400

    tender_content = _get_tender_content(project_id)
    if not tender_content.strip():
        return jsonify({
            "success": False,
            "message": "该招标项目尚未解析任何招标文件内容，请先在「招标分析」中对该项目执行分析"
        }), 400

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.doc_parser import parse_file

    # 保存并解析所有投标文件
    bid_texts = []
    bidder_names = []
    file_meta = []
    all_truncated = False

    with tempfile.TemporaryDirectory() as td:
        for idx, f in enumerate(files):
            ext = os.path.splitext(f.filename)[1].lower()
            safe_name = f"bid_{idx}{ext}"
            tmp_path = os.path.join(td, safe_name)
            f.save(tmp_path)

            size = os.path.getsize(tmp_path)
            if size > MAX_BID_FILE_SIZE:
                return jsonify({
                    "success": False,
                    "message": f"文件 {f.filename} 大小超过 200MB 限制"
                }), 413

            result = parse_file(tmp_path, "DOCX")
            if result.get("error"):
                return jsonify({
                    "success": False,
                    "message": f"文件 {f.filename} 解析失败：{result['error']}"
                }), 400

            text = (result.get("text") or "").strip()
            tables = result.get("tables") or []
            table_parts = []
            for tidx, table in enumerate(tables):
                rows = []
                for row in table:
                    if isinstance(row, list):
                        rows.append(" | ".join(str(c) for c in row))
                    else:
                        rows.append(str(row))
                if rows:
                    table_parts.append("[表格" + str(tidx + 1) + "]\n" + "\n".join(rows))
            if table_parts:
                text = (text + "\n\n" + "\n\n".join(table_parts)).strip()

            truncated = False
            if len(text) > 100000:
                text = _truncate(text, 100000)
                truncated = True
                all_truncated = True

            bid_texts.append(text)
            # 使用文件名（去后缀）作为投标人名称
            base_name = os.path.splitext(os.path.basename(f.filename))[0]
            bidder_names.append(base_name)
            file_meta.append({
                "index": idx,
                "original_name": f.filename,
                "bidder_name": base_name,
                "size": size,
                "truncated": truncated,
            })

    # 截断招标文件
    tender_truncated = False
    tender_for_llm = tender_content
    if len(tender_for_llm) > 60000:
        tender_for_llm = _truncate(tender_for_llm, 60000)
        tender_truncated = True

    # 提取评分标准
    from backend.ai_extractor import _call_llm_with_fallback, _parse_json_response
    criteria_info, criteria_model = _extract_scoring_criteria(tender_for_llm, prompt)

    if criteria_info is None:
        criteria_info = {
            "criteria": DEFAULT_CRITERIA,
            "total_max": DEFAULT_TOTAL_MAX,
            "raw_text": "",
        }
        criteria_source = "default"
    else:
        criteria_source = "extracted"

    # 对每家投标文件进行打分
    scoring_results = []
    scoring_model = ""

    for idx in range(len(bid_texts)):
        result, err = _score_single_bid(
            idx,
            bidder_names[idx],
            bid_texts[idx],
            criteria_info,
            tender_for_llm,
            (_call_llm_with_fallback, _parse_json_response),
        )
        if result is None:
            result = {
                "bidder_index": idx,
                "bidder_name": bidder_names[idx],
                "scores": [],
                "total_score": 0,
                "total_max": criteria_info["total_max"],
                "summary": f"打分失败：{err or '未知错误'}",
                "strengths": [],
                "weaknesses": ["打分过程出现异常"],
            }
        scoring_results.append(result)

    # 技术查重
    plagiarism = _detect_plagiarism(bid_texts, bidder_names)

    # 排名
    ranking = sorted(
        [{"rank": i + 1, "bidder_name": r["bidder_name"], "total_score": r["total_score"],
          "total_max": r["total_max"]}
         for i, r in enumerate(sorted(scoring_results, key=lambda x: x["total_score"], reverse=True))],
        key=lambda x: x["rank"]
    )

    return jsonify({
        "success": True,
        "project_name": project.get("name", ""),
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "criteria_info": {
            "source": criteria_source,
            "criteria": criteria_info["criteria"],
            "total_max": criteria_info["total_max"],
            "raw_text": criteria_info["raw_text"],
        },
        "bidders": file_meta,
        "scoring_results": scoring_results,
        "plagiarism": plagiarism,
        "ranking": ranking,
        "truncated": bool(all_truncated or tender_truncated),
        "criteria_model": criteria_model or "",
        "scoring_model": scoring_model,
        "bid_count": len(bid_texts),
    })


# ── 下载评分报告（docx） ──────────────────────────────────
@bid_score_bp.route("/api/bid-score/download", methods=["POST"])
def download_bid_score_report():
    data = request.get_json(silent=True) or {}
    if not data.get("scoring_results"):
        return jsonify({"success": False, "message": "报告内容为空"}), 400

    try:
        bio = _build_score_report_docx(data)
    except Exception as e:
        return jsonify({"success": False, "message": "报告生成失败：" + str(e)}), 500

    fname = f"投标评分对比报告_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    return send_file(bio, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def _build_score_report_docx(data):
    """根据评分结果生成 docx 对比报告"""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn

    doc = Document()

    # 默认中文字体
    normal = doc.styles['Normal']
    normal.font.name = '宋体'
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    # 标题
    title = doc.add_heading('投标文件模拟评分对比报告', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 元信息
    meta = doc.add_paragraph()
    meta.add_run('招标项目：').bold = True
    meta.add_run(data.get('project_name', '—') + '\n')
    meta.add_run('投标文件数量：').bold = True
    meta.add_run(str(data.get('bid_count', 0)) + '\n')
    meta.add_run('评分时间：').bold = True
    meta.add_run(data.get('checked_at', '—'))
    for run in meta.runs:
        run.font.size = Pt(10)

    doc.add_paragraph('')

    # 一、评分标准
    doc.add_heading('一、评分标准', level=1)
    ci = data.get("criteria_info", {})
    criteria = ci.get("criteria") or []
    if criteria:
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = table.rows[0].cells
        hdr[0].text = "序号"
        hdr[1].text = "评分项"
        hdr[2].text = "满分"
        for cell in hdr:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(10)
        for i, c in enumerate(criteria, 1):
            row = table.add_row().cells
            row[0].text = str(i)
            row[1].text = c.get("name", "—")
            row[2].text = str(c.get("max_score", 0))
            for cell in row:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(10)
        doc.add_paragraph('')

    if ci.get("source") == "default":
        p = doc.add_paragraph()
        rn = p.add_run("注：未能从招标文件中提取到明确的评分标准，以上为默认评分维度。")
        rn.italic = True
        rn.font.size = Pt(9)
        rn.font.color.rgb = RGBColor(0xCC, 0x7A, 0x00)

    # 二、得分对比表
    doc.add_heading('二、得分对比', level=1)
    results = data.get("scoring_results") or []
    bidders = data.get("bidders") or []
    criteria_names = [c.get("name", "") for c in criteria]

    if results and criteria_names:
        # 构建列：序号 | 评分项 | 每家公司得分
        n_bidders = len(results)
        n_cols = 2 + n_bidders
        table = doc.add_table(rows=1 + len(criteria_names) + 1, cols=n_cols)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # 表头
        hdr_row = table.rows[0].cells
        hdr_row[0].text = "序号"
        hdr_row[1].text = "评分项"
        for i, r in enumerate(results):
            name = r.get("bidder_name", f"投标人{i+1}")
            hdr_row[2 + i].text = name
        for cell in hdr_row:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(9)

        # 数据行
        for row_idx, crit_name in enumerate(criteria_names):
            cells = table.rows[row_idx + 1].cells
            cells[0].text = str(row_idx + 1)
            cells[1].text = crit_name
            for bidder_idx, r in enumerate(results):
                score = 0
                max_s = 0
                for s in (r.get("scores") or []):
                    if s.get("name") == crit_name:
                        score = s.get("score", 0)
                        max_s = s.get("max_score", 0)
                        break
                cells[2 + bidder_idx].text = f"{score}/{max_s}"
            for cell in cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)

        # 总分行
        total_row_idx = len(criteria_names) + 1
        if total_row_idx < len(table.rows):
            total_cells = table.rows[total_row_idx].cells
            total_cells[0].text = ""
            total_cells[1].text = "总分"
            for bidder_idx, r in enumerate(results):
                ts = r.get("total_score", 0)
                tm = r.get("total_max", 0)
                total_cells[2 + bidder_idx].text = f"{ts}/{tm}"
            for cell in total_cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.bold = True
                        run.font.size = Pt(9)
                        run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)

        doc.add_paragraph('')

    # 三、排名
    doc.add_heading('三、排名', level=1)
    ranking = data.get("ranking") or []
    for r in ranking:
        p = doc.add_paragraph()
        rank_text = f"第 {r['rank']} 名：{r['bidder_name']} — {r['total_score']} / {r['total_max']} 分"
        run = p.add_run(rank_text)
        run.font.size = Pt(11)

    doc.add_paragraph('')

    # 四、各家详情
    doc.add_heading('四、各家评分详情', level=1)
    for r in results:
        bidder_name = r.get("bidder_name", "—")
        total_s = r.get("total_score", 0)
        total_m = r.get("total_max", 0)

        p = doc.add_paragraph()
        run = p.add_run(f"【{bidder_name}】总分：{total_s} / {total_m}")
        run.bold = True
        run.font.size = Pt(12)

        summary = r.get("summary", "")
        if summary:
            sp = doc.add_paragraph()
            sp.add_run("整体评价：").bold = True
            sp.add_run(summary)

        # 各项打分
        for s in (r.get("scores") or []):
            name = s.get("name", "—")
            sc = s.get("score", 0)
            mx = s.get("max_score", 0)
            reason = s.get("reason", "")
            dp = doc.add_paragraph()
            dp.add_run(f"• {name}：{sc} / {mx}")
            if reason:
                dp2 = doc.add_paragraph()
                rp = dp2.add_run("  " + reason)
                rp.font.size = Pt(10)
                rp.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        # 优势
        strengths = r.get("strengths") or []
        if strengths:
            sp = doc.add_paragraph()
            sp.add_run("优势：").bold = True
            sp.add_run("；".join(strengths))

        # 不足
        weaknesses = r.get("weaknesses") or []
        if weaknesses:
            wp = doc.add_paragraph()
            wp.add_run("不足：").bold = True
            wr = wp.add_run("；".join(weaknesses))
            wr.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)

        doc.add_paragraph('')

    # 五、技术查重警示
    doc.add_heading('五、技术内容查重检测', level=1)
    plagiarism = data.get("plagiarism") or []
    if not plagiarism:
        p = doc.add_paragraph()
        rn = p.add_run("未检测到明显的技术内容重复。")
        rn.font.color.rgb = RGBColor(0x2E, 0x7D, 0x32)
    else:
        for item in plagiarism:
            a = item.get("bidder_a", "—")
            b = item.get("bidder_b", "—")
            sim = item.get("similarity", 0)
            level = item.get("level", "low")

            lp = doc.add_paragraph()
            level_text = {"high": "高度相似", "medium": "中度相似", "low": "轻度相似"}.get(level, "疑似重复")
            color_map = {"high": RGBColor(0xC0, 0x39, 0x2B),
                         "medium": RGBColor(0xCC, 0x7A, 0x00),
                         "low": RGBColor(0xB8, 0x86, 0x00)}
            lr = lp.add_run(f"⚠ {a} 与 {b}：相似度 {sim*100:.1f}%（{level_text}）")
            lr.bold = True
            lr.font.color.rgb = color_map.get(level, RGBColor(0xCC, 0x7A, 0x00))

            blocks = item.get("matching_blocks") or []
            if blocks:
                for blk in blocks[:3]:
                    lines = blk.get("lines_from_1") or []
                    if lines:
                        bp = doc.add_paragraph()
                        bp.add_run("  重复内容：").bold = True
                        bp.add_run("… ".join(lines[:3]))

    doc.add_paragraph('')

    # 结尾
    footer = doc.add_paragraph()
    rn = footer.add_run('本报告由 BidTool 投标工具 自动生成，仅供评审参考。')
    rn.font.size = Pt(9)
    rn.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    rn.italic = True

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
