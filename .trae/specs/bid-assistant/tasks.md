# 投标助手功能 - 实现计划

## [x] Task 1: 更新前端侧边栏，添加投标助手导航
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 在App.vue的侧边栏导航中添加"投标助手"按钮
  - 添加对应的图标和样式
  - 添加新的tab类型 'bid-assistant'
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `human-judgment` TR-1.1: 侧边栏显示"投标助手"按钮，点击后切换到对应页面

## [x] Task 2: 创建投标助手页面组件
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 创建BidAssistant.vue组件
  - 实现项目名称输入框、URL输入框和文件上传区域
  - 实现解析按钮和加载状态
  - 实现解析结果展示区域
  - 添加一键复制功能
  - 实现历史项目列表展示和选择功能
- **Acceptance Criteria Addressed**: AC-2, AC-3, AC-4, AC-5, FR-8, FR-9
- **Test Requirements**:
  - `human-judgment` TR-2.1: 页面布局合理，包含项目名称、URL输入、文件上传、解析按钮
  - `human-judgment` TR-2.2: 解析结果展示结构化信息（开标日期、时间、招标人名称等）
  - `human-judgment` TR-2.3: 复制按钮正常工作
  - `human-judgment` TR-2.4: 历史项目列表显示正常，可选择查看详情

## [x] Task 3: 更新BidTool.vue主组件
- **Priority**: P0
- **Depends On**: Task 2
- **Description**: 
  - 添加bid-assistant tab的展示逻辑
  - 导入并引用BidAssistant组件
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `human-judgment` TR-3.1: 点击侧边栏"投标助手"时显示对应页面

## [x] Task 4: 创建后端AI解析路由
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 创建bid_assistant_routes.py路由文件
  - 实现文件解析接口（支持doc、docx、pdf格式）
  - 实现URL内容抓取接口
  - 实现AI大模型调用逻辑（mock实现，预留API调用接口）
- **Acceptance Criteria Addressed**: AC-2, AC-3
- **Test Requirements**:
  - `programmatic` TR-4.1: POST /api/bid-assistant/parse 返回成功状态和解析结果

## [x] Task 5: 创建数据持久化模块
- **Priority**: P0
- **Depends On**: Task 4
- **Description**: 
  - 创建SQLite数据库模型
  - 实现项目数据存储接口
  - 实现项目列表查询接口
  - 实现项目详情查询接口
- **Acceptance Criteria Addressed**: FR-7, FR-8, FR-9
- **Test Requirements**:
  - `programmatic` TR-5.1: POST /api/bid-assistant/save 成功保存解析结果
  - `programmatic` TR-5.2: GET /api/bid-assistant/projects 返回项目列表
  - `programmatic` TR-5.3: GET /api/bid-assistant/projects/{id} 返回项目详情

## [x] Task 6: 注册后端路由到主应用
- **Priority**: P0
- **Depends On**: Task 4, Task 5
- **Description**: 
  - 在app.py中注册bid_assistant_routes蓝图
- **Acceptance Criteria Addressed**: AC-2, AC-3, FR-7
- **Test Requirements**:
  - `programmatic` TR-6.1: 路由/api/bid-assistant/*均可访问

## [x] Task 7: 添加必要的依赖包
- **Priority**: P1
- **Depends On**: Task 4
- **Description**: 
  - 在requirements.txt中添加pdfplumber、requests、sqlalchemy等依赖
  - 更新后端依赖
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-7.1: 依赖安装成功，服务正常启动