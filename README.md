# BidTool — 智能投标工具

面向投标业务的全流程辅助工具，涵盖文件管理、AI 招标分析、资质证书管理（含 OCR 识别）、区域招标信息查询、报价计算与策略调整等核心功能。

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3.8+, Flask 3.0+, Flask-CORS |
| 前端 | HTML5 + CSS3 + Vue 3（CDN，无需构建工具） |
| 数据存储 | JSON 文件（`data/` 目录） |
| AI 集成 | OpenAI 兼容 API，支持多模型切换 |
| PDF 处理 | pdfplumber |
| OCR（可选） | pytesseract + Tesseract |
| 文档处理 | python-docx |

## 快速开始

### 环境要求

- Python 3.8+
- （可选）Tesseract OCR — 用于非视觉模型的图片识别降级

### 安装运行

**方式一：一键启动（Windows）**

双击 `start.bat`，自动安装依赖并打开浏览器。

**方式二：命令行**

```bash
pip install -r requirements.txt
python backend/app.py
```

启动后访问 `http://127.0.0.1:5000`。

## 项目结构

```
├── backend/
│   ├── app.py                 # Flask 主程序
│   ├── llm_client.py          # 大模型 API 客户端（OpenAI 兼容协议）
│   └── routes/
│       ├── files.py           # 文件管理
│       ├── analysis.py        # 招标分析
│       ├── certs.py           # 资质管理（含 OCR）
│       ├── region.py          # 区域查询
│       ├── pricing.py         # 报价调整
│       └── settings.py        # 系统设置
├── frontend/
│   ├── templates/
│   │   └── index.html         # 单页应用（SPA）
│   └── static/
│       ├── css/main.css       # 全局样式
│       └── js/app.js          # Vue 3 应用逻辑
├── data/                      # JSON 数据存储
│   ├── config.json            # 大模型配置
│   ├── certs.json             # 证书数据
│   ├── bidding.json           # 招标数据（自动生成）
│   ├── cert_files/            # 证书附件
│   └── files/                 # 上传文件
├── requirements.txt
├── run.py                     # 启动脚本
├── start.bat                  # Windows 一键启动
└── README.md
```

## 功能模块

### 1. 工作台（Dashboard）

展示关键统计数据与快捷操作入口：

- 已上传文件 / 招标分析 / 资质证书数量统计
- 即将到期证书提醒
- 快速新建分析 / 上传证书入口

### 2. 文件管理（Files）

- 文件上传与下载
- 文件夹管理（创建 / 删除）
- 面包屑导航
- 文件列表表格展示（名称、大小、日期）

### 3. 招标分析（Analysis）

- 新建分析记录（关联招标文件）
- 分析记录查看与删除
- 预留 LLM 招标文件智能分析接口

### 4. 资质管理（Certs）

最完整的模块，支持企业资质证书的全生命周期管理：

- **分类管理**：左侧目录树 + 右侧证书网格，支持增删改
- **AI OCR 识别**：上传营业执照、资质证书等图片或 PDF，大模型自动提取关键字段（证书名称、编号、发证机关、有效期等）
  - 视觉模型：直接识别图片内容
  - 文本模型：自动降级为 pytesseract OCR → 文本识别
- **文件存储**：上传文件实际保存到 `data/cert_files/`，支持下载
- **Demo 数据**：预置 3 条示例证书

### 5. 区域查询（Region）

按省份和城市查询招标信息：

- 统计卡片：招标总数 / 招标中 / 7 天内截止 / 已中标
- 多条件筛选：省份 → 城市联动、项目类别、招标状态、关键词搜索
- 分页浏览（每页 15 条）
- 详情弹窗查看
- 一键刷新 Mock 数据（约 128 条覆盖 16 个省份）

### 6. 报价调整（Pricing）

投标报价的精细化计算工具：

- **成本明细表**：6 类成本项（人工 / 材料 / 设备 / 服务 / 差旅 / 其他），内联编辑
- **3 种报价策略**：激进（薄利多销）/ 平衡 / 保守（高利润空间）
- **费率滑块**：利润率（0-50%）/ 折扣率（0-30%）/ 税率（0-17%），拖拽 + 手动输入
- **自动计算**：成本合计 → +利润 → -折扣 → +税费 → 最终报价
- **多项目管理**：支持多个报价方案并存

### 7. 系统设置（Settings）

大模型配置中心：

- **4 个内置模型**：OpenAI GPT / DeepSeek / 通义千问 / 智谱 GLM
- **1 个自定义模型**：支持任意 OpenAI 兼容接口
- **视觉开关**：标识模型是否支持图片识别
- **连接测试**：一键测试模型 API 连通性和延迟
- **默认模型选择**：全局生效于 AI OCR 等场景

## 大模型配置

配置文件位于 `data/config.json`，预置了 5 个模型槽位：

```json
{
  "models": [
    { "name": "OpenAI GPT",    "model": "gpt-4o",            "supports_vision": true },
    { "name": "DeepSeek",      "model": "deepseek-v4-flash", "supports_vision": false },
    { "name": "通义千问",       "model": "qwen-max",          "supports_vision": false },
    { "name": "智谱 GLM",      "model": "glm-4-flash",       "supports_vision": false },
    { "name": "自定义模型",     "model": "",                  "supports_vision": false }
  ],
  "active_model": "通义千问"
}
```

也可通过系统设置页面可视化配置。

## 设计说明

- **前端**：Vue 3 CDN 方式引入，无需 Node.js、无需构建步骤，修改即生效
- **后端**：Flask Blueprint 模块化，每个功能模块独立路由文件
- **数据**：JSON 文件持久化，零数据库依赖
- **配色**：马卡龙色系（紫 / 粉 / 薄荷绿 / 暖橙 / 天蓝）
- **认证**：未实现，单机本地使用

## License

MIT
