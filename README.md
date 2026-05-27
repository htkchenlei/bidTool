# 投标工具

一个独立的投标工具应用，包含价格调整、地名查询和招标解析功能。

## 功能特性

- **价格调整**：上传Excel文件，设置目标总价，自动调整价格以达到目标
- **地名查询**：上传文档，自动识别文档中的地名信息
- **地名管理**：管理省级、市级、区级地名数据
- **招标解析**：上传招标公告（支持doc、docx、pdf）或输入URL，调用AI大模型自动解析关键信息
  - 项目名称、项目编号、预算金额
  - 开标日期、开标时间
  - 招标人名称、代理机构
  - 废标项、评分标准
  - 历史项目管理（支持软删除）

## 技术栈

- **前端**: Vue 3 + JavaScript + Vite
- **后端**: Flask + Python 3.11
- **数据库**: JSON文件存储
- **AI模型支持**: DeepSeek、阿里云通义千问、火山引擎豆包、Kimi、GLM-4、Minimax、OpenAI、硅基流动

## 快速开始

### 开发模式

#### 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

#### 启动前端

```bash
cd frontend
npm install
npm run dev
```

### Docker部署

```bash
docker-compose up -d --build
```

## 项目结构

```
bidTool/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── excel_process_routes.py
│   │   │   ├── file_parse_routes.py
│   │   │   ├── place_routes.py
│   │   │   └── bid_assistant_routes.py
│   │   └── utils/
│   │       └── ai_helper.py
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── style.css
├── data/
│   ├── ai_config.json
│   ├── bid_projects.json
│   └── china_regions.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## API接口

### 价格调整

- `POST /process-excel` - 处理Excel文件，调整价格

### 地名查询

- `POST /file-parse` - 解析文件，查找地名
- `GET /api/places` - 获取所有地名数据
- `POST /api/places/add` - 添加地名
- `POST /api/places/delete` - 删除地名

### 招标解析

- `POST /api/bid-assistant/parse` - 解析招标公告（URL或文件）
- `GET /api/bid-assistant/projects` - 获取历史项目列表
- `POST /api/bid-assistant/projects` - 保存项目
- `GET /api/bid-assistant/projects/<id>` - 获取单个项目
- `POST /api/bid-assistant/projects/<id>/delete` - 软删除项目
- `GET /api/bid-assistant/config` - 获取AI配置
- `POST /api/bid-assistant/config` - 保存AI配置

## 配置说明

### 环境变量

- `FLASK_APP` - Flask应用入口
- `FLASK_ENV` - 运行环境 (development/production)

### AI配置

AI模型配置存储在 `data/ai_config.json` 文件中，支持以下模型：
- DeepSeek
- 阿里云通义千问
- 火山引擎豆包
- Kimi
- GLM-4
- Minimax
- OpenAI
- 硅基流动 (SiliconFlow)

### 地名数据

地名数据存储在 `data/china_regions.json` 文件中，包含省级、市级、区级三个级别的地名信息。

### 项目数据

解析的招标项目存储在 `data/bid_projects.json` 文件中，支持软删除。

## 使用说明

### 招标解析

1. 在侧边栏点击「招标解析」
2. 输入招标公告URL或上传文档（支持doc、docx、pdf）
3. 点击「开始解析」，AI自动提取关键信息
4. 解析完成后可保存到历史项目或复制结果
5. 历史项目支持查看详情和删除（二次确认）

## 许可证

MIT