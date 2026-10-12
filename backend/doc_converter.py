"""
.doc（旧版 Word 97-2003 二进制格式）转文本模块

按可用性依次尝试多种转换引擎，返回提取到的纯文本。
优先级：
  1. Microsoft Word COM（Windows，需安装 Word + pywin32）
  2. LibreOffice / OpenOffice（跨平台，soffice 命令行）
  3. antiword（Linux，轻量）
  4. catdoc（Linux，轻量）
"""
import os
import shutil
import subprocess
import tempfile


def _run(cmd, timeout=90, **kwargs):
    """执行外部命令并返回 stdout 文本，出错返回 None"""
    try:
        proc = subprocess.run(
            cmd,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )
        if proc.returncode != 0:
            return None
        # 优先按 UTF-8 解码，失败回退 GBK（Windows 生成的文本常见）
        raw = proc.stdout
        for enc in ("utf-8", "gbk", "latin-1"):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _convert_with_word_com(file_path):
    """Windows：通过 Word COM 将 .doc 另存为 UTF-8 文本"""
    try:
        import win32com.client  # pywin32（可选依赖）
    except ImportError:
        return None, "pywin32 未安装（Windows 下可执行 pip install pywin32）"

    word = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(os.path.abspath(file_path), ReadOnly=True)
        # 直接通过 COM 读取正文纯文本，避免 SaveAs 到文件再处理编码
        text = doc.Content.Text
        doc.Close(False)
        return text, None
    except Exception as e:
        return None, f"Word COM 转换失败：{str(e)[:200]}"
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def _convert_with_libreoffice(file_path):
    """跨平台：使用 LibreOffice 将 .doc 转 txt"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice and os.name == "nt":
        candidate = r"C:\Program Files\LibreOffice\program\soffice.exe"
        if os.path.exists(candidate):
            soffice = candidate
    if not soffice:
        return None, "未找到 LibreOffice/soffice"
    if os.name == "nt" and not os.path.exists(soffice):
        return None, "未找到 LibreOffice/soffice"

    try:
        tmpdir = tempfile.mkdtemp()
        cmd = [
            soffice,
            "--headless",
            "--convert-to", "txt:Text",
            "--outdir", tmpdir,
            os.path.abspath(file_path),
        ]
        subprocess.run(cmd, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        base = os.path.splitext(os.path.basename(file_path))[0]
        txt_path = os.path.join(tmpdir, base + ".txt")
        if not os.path.exists(txt_path):
            # LibreOffice 可能输出同名但大小写不同
            for name in os.listdir(tmpdir):
                if name.lower().endswith(".txt"):
                    txt_path = os.path.join(tmpdir, name)
                    break
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), None
        return None, "LibreOffice 未生成输出文件"
    except Exception as e:
        return None, f"LibreOffice 转换失败：{str(e)[:200]}"


def _convert_with_antiword(file_path):
    exe = shutil.which("antiword")
    if not exe:
        return None, "antiword 未安装"
    text = _run([exe, os.path.abspath(file_path)])
    if text is None:
        return None, "antiword 执行失败"
    return text, None


def _convert_with_catdoc(file_path):
    exe = shutil.which("catdoc")
    if not exe:
        return None, "catdoc 未安装"
    text = _run([exe, os.path.abspath(file_path)])
    if text is None:
        return None, "catdoc 执行失败"
    return text, None


def convert_doc_to_text(file_path):
    """
    将 .doc 文件转换为纯文本。
    返回 (text, error)：成功时 text 非空、error 为 None；失败时 text 为空、error 为原因。
    """
    engines = [
        ("Word COM", _convert_with_word_com) if os.name == "nt" else None,
        ("LibreOffice", _convert_with_libreoffice),
        ("antiword", _convert_with_antiword),
        ("catdoc", _convert_with_catdoc),
    ]
    last_error = None
    for engine in engines:
        if engine is None:
            continue
        name, fn = engine
        text, err = fn(file_path)
        if text and text.strip():
            return text.strip(), None
        if err:
            last_error = err

    if last_error is None:
        last_error = "没有可用的 .doc 转换引擎"
    return "", (
        "无法解析旧版 Word(.doc) 文件。请将文件“另存为” .docx 或导出 PDF 后重新上传。"
        "（已尝试：Word COM / LibreOffice / antiword / catdoc，均不可用。最后错误：" + last_error + "）"
    )
