# 投标助手功能 - 产品需求文档

## Overview
- **Summary**: 在现有投标工具侧边栏中添加"投标助手"功能，通过输入招标公告URL或上传投标文件，调用AI大模型自动解析招投标关键信息，包括开标日期、时间、招标人名称、代理机构名称、废标项、评分标准等。
- **Purpose**: 帮助用户快速从招标文档中提取关键信息，提高投标工作效率，减少人工阅读成本。
- **Target Users**: 投标业务人员、标书制作人员、项目管理人员

## Goals
- 在侧边栏添加"投标助手"导航按钮
- 支持通过URL输入招标公告链接
- 支持上传投标文件（支持doc、docx、pdf格式）
- 调用AI大模型解析文档内容
- 展示解析后的结构化关键信息
- 支持一键复制解析结果
- 解析数据依据项目名称持久化存储到本地
- 支持项目列表管理和查看历史解析记录

## Non-Goals (Out of Scope)
- 不实现完整的AI大模型训练
- 不支持在线编辑招标文档
- 不提供投标文件生成功能

## Background & Context
- 现有项目为投标工具，包含价格调整和地名查询功能
- 前端使用Vue 3 + TypeScript + Vite
- 后端使用Flask框架
- 样式采用马卡龙色系设计风格

## Functional Requirements
- **FR-1**: 在侧边栏添加"投标助手"导航项，点击后切换到对应功能页面
- **FR-2**: 支持输入招标公告URL地址进行解析
- **FR-3**: 支持上传本地投标文件进行解析（支持doc、docx、pdf格式）
- **FR-4**: 调用AI大模型接口解析文档内容
- **FR-5**: 展示解析结果，包括：开标日期、开标时间、招标人名称、代理机构名称、废标项、评分标准
- **FR-6**: 支持一键复制解析结果
- **FR-7**: 解析结果依据项目名称存储到本地数据库
- **FR-8**: 支持查看历史项目列表和对应的解析记录
- **FR-9**: 支持从项目列表中选择历史项目查看详情

## Non-Functional Requirements
- **NFR-1**: 文件上传大小限制50MB
- **NFR-2**: 解析请求超时时间30秒
- **NFR-3**: 响应式设计，适配不同屏幕尺寸
- **NFR-4**: 错误处理友好，提示清晰

## Constraints
- **Technical**: 需要接入外部AI大模型API（如OpenAI、阿里云等）
- **Business**: 需要配置API密钥才能使用AI功能
- **Dependencies**: 需安装python-docx、pdfplumber等文件解析库

## Assumptions
- [ ] AI大模型API已配置可用
- [ ] 用户具备互联网连接以访问AI服务

## Acceptance Criteria

### AC-1: 侧边栏导航
- **Given**: 用户打开应用
- **When**: 查看侧边栏
- **Then**: 看到"投标助手"导航按钮
- **Verification**: `human-judgment`

### AC-2: URL输入解析
- **Given**: 用户在投标助手页面
- **When**: 输入有效的招标公告URL并点击解析
- **Then**: 成功获取页面内容并调用AI解析
- **Verification**: `programmatic`

### AC-3: 文件上传解析
- **Given**: 用户在投标助手页面
- **When**: 上传支持格式的文件并点击解析
- **Then**: 成功解析文件内容并调用AI分析
- **Verification**: `programmatic`

### AC-4: 解析结果展示
- **Given**: AI解析完成
- **When**: 查看解析结果页面
- **Then**: 看到结构化展示的开标日期、时间、招标人名称、代理机构名称、废标项、评分标准
- **Verification**: `human-judgment`

### AC-5: 一键复制功能
- **Given**: 解析结果已展示
- **When**: 点击复制按钮
- **Then**: 解析结果被复制到剪贴板
- **Verification**: `human-judgment`

## Open Questions
- [ ] AI大模型API的具体类型和配置方式是什么？
- [ ] 是否需要支持其他文件格式？