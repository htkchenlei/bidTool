<template>
  <div class="bid-assistant">
    <div class="main-section">
      <div class="input-section">
        <h4>投标助手</h4>
        
        <div class="form-row">
          <label for="projectName">项目名称：</label>
          <input 
            type="text" 
            id="projectName" 
            v-model="projectName" 
            class="form-control"
            placeholder="请输入项目名称"
          >
        </div>

        <div class="form-row">
          <label for="bidUrl">招标公告URL：</label>
          <input 
            type="text" 
            id="bidUrl" 
            v-model="bidUrl" 
            class="form-control"
            placeholder="请输入招标公告网页地址"
          >
        </div>

        <div class="form-row file-upload-row">
          <label for="bidFile">上传文件：</label>
          <div class="file-upload-container">
            <input 
              type="text" 
              v-model="selectedFilePath" 
              readonly 
              class="form-control file-path-input"
              placeholder="请选择doc、docx、pdf文件"
            >
            <input 
              type="file" 
              id="bidFile" 
              ref="fileInput"
              accept=".doc, .docx, .pdf"
              class="file-input"
              @change="handleFileSelect"
            >
            <button type="button" class="btn btn-secondary file-select-btn" @click="openFileDialog">选择文件</button>
          </div>
        </div>

        <div class="form-row">
          <button 
            @click="parseDocument" 
            class="btn btn-primary"
            :disabled="isLoading || (!bidUrl && !selectedFilePath)"
          >
            <span v-if="isLoading">⏳</span>
            <span v-else>🔍</span>
            {{ isLoading ? '解析中...' : '开始解析' }}
          </button>
        </div>
      </div>

      <div v-if="parseResult" class="result-section">
        <div class="result-header">
          <h4>解析结果</h4>
          <div class="result-actions">
            <button @click="saveResult" class="btn btn-success btn-sm" :disabled="isSaving">
              <span>{{ isSaving ? '⏳' : '💾' }}</span>
              {{ isSaving ? '保存中...' : '保存项目' }}
            </button>
            <button @click="copyResult" class="btn btn-secondary btn-sm">
              <span>📋</span> 复制结果
            </button>
          </div>
        </div>

        <div class="result-content">
          <div class="result-grid">
            <div class="result-item">
              <span class="result-label">开标日期</span>
              <span class="result-value">{{ parseResult.bidDate || '-' }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">开标时间</span>
              <span class="result-value">{{ parseResult.bidTime || '-' }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">招标人名称</span>
              <span class="result-value">{{ parseResult.bidderName || '-' }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">代理机构</span>
              <span class="result-value">{{ parseResult.agencyName || '-' }}</span>
            </div>
          </div>

          <div class="result-section-item">
            <h5>📋 废标项</h5>
            <ul class="result-list">
              <li v-for="(item, index) in parseResult.disqualificationItems" :key="index">
                {{ item }}
              </li>
              <li v-if="!parseResult.disqualificationItems || parseResult.disqualificationItems.length === 0">
                暂无数据
              </li>
            </ul>
          </div>

          <div class="result-section-item">
            <h5>📊 评分标准</h5>
            <ul class="result-list">
              <li v-for="(item, index) in parseResult.evaluationCriteria" :key="index">
                {{ item }}
              </li>
              <li v-if="!parseResult.evaluationCriteria || parseResult.evaluationCriteria.length === 0">
                暂无数据
              </li>
            </ul>
          </div>

          <div class="result-section-item" v-if="parseResult.otherInfo">
            <h5>📝 其他信息</h5>
            <p class="result-text">{{ parseResult.otherInfo }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="sidebar-section">
      <h4>📁 历史项目</h4>
      <div v-if="projectList.length === 0" class="empty-state">
        <p>暂无历史项目</p>
      </div>
      <div v-else class="project-list">
        <div 
          v-for="project in projectList" 
          :key="project.id"
          class="project-item"
          :class="{ active: selectedProject?.id === project.id }"
          @click="selectProject(project)"
        >
          <div class="project-name">{{ project.name }}</div>
          <div class="project-date">{{ formatDate(project.created_at) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface ParseResult {
  bidDate: string
  bidTime: string
  bidderName: string
  agencyName: string
  disqualificationItems: string[]
  evaluationCriteria: string[]
  otherInfo?: string
}

interface Project {
  id: number
  name: string
  bidDate: string
  bidTime: string
  bidderName: string
  agencyName: string
  disqualificationItems: string
  evaluationCriteria: string
  otherInfo: string
  created_at: string
}

const projectName = ref('')
const bidUrl = ref('')
const selectedFilePath = ref('')
const fileInput = ref<HTMLInputElement>()
const isLoading = ref(false)
const isSaving = ref(false)
const parseResult = ref<ParseResult | null>(null)
const projectList = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFilePath.value = target.files[0].path || target.files[0].name
  }
}

const openFileDialog = () => {
  fileInput.value?.click()
}

const parseDocument = async () => {
  if (!bidUrl.value && !selectedFilePath.value) {
    alert('请输入招标公告URL或上传文件')
    return
  }

  if (!projectName.value) {
    alert('请输入项目名称')
    return
  }

  isLoading.value = true
  parseResult.value = null

  try {
    const formData = new FormData()
    formData.append('projectName', projectName.value)
    
    if (bidUrl.value) {
      formData.append('url', bidUrl.value)
    }

    if (fileInput.value?.files?.[0]) {
      formData.append('file', fileInput.value.files[0])
    }

    const response = await fetch('/api/bid-assistant/parse', {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        parseResult.value = {
          bidDate: data.result.bidDate || '',
          bidTime: data.result.bidTime || '',
          bidderName: data.result.bidderName || '',
          agencyName: data.result.agencyName || '',
          disqualificationItems: data.result.disqualificationItems || [],
          evaluationCriteria: data.result.evaluationCriteria || [],
          otherInfo: data.result.otherInfo
        }
      } else {
        alert('解析失败: ' + (data.message || '未知错误'))
      }
    } else {
      alert('解析失败')
    }
  } catch (error) {
    console.error('解析失败:', error)
    alert('解析失败')
  } finally {
    isLoading.value = false
  }
}

const saveResult = async () => {
  if (!parseResult.value || !projectName.value) {
    return
  }

  isSaving.value = true

  try {
    const response = await fetch('/api/bid-assistant/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: projectName.value,
        bidDate: parseResult.value.bidDate,
        bidTime: parseResult.value.bidTime,
        bidderName: parseResult.value.bidderName,
        agencyName: parseResult.value.agencyName,
        disqualificationItems: JSON.stringify(parseResult.value.disqualificationItems),
        evaluationCriteria: JSON.stringify(parseResult.value.evaluationCriteria),
        otherInfo: parseResult.value.otherInfo || ''
      })
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        alert('保存成功')
        loadProjects()
      } else {
        alert('保存失败: ' + (data.message || '未知错误'))
      }
    } else {
      alert('保存失败')
    }
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败')
  } finally {
    isSaving.value = false
  }
}

const copyResult = async () => {
  if (!parseResult.value) return

  const text = `项目名称：${projectName.value}
开标日期：${parseResult.value.bidDate || '-'}
开标时间：${parseResult.value.bidTime || '-'}
招标人名称：${parseResult.value.bidderName || '-'}
代理机构：${parseResult.value.agencyName || '-'}

废标项：
${parseResult.value.disqualificationItems?.map((item, i) => `${i + 1}. ${item}`).join('\n') || '暂无'}

评分标准：
${parseResult.value.evaluationCriteria?.map((item, i) => `${i + 1}. ${item}`).join('\n') || '暂无'}

其他信息：
${parseResult.value.otherInfo || '暂无'}`

  try {
    await navigator.clipboard.writeText(text)
    alert('复制成功')
  } catch (error) {
    console.error('复制失败:', error)
    alert('复制失败')
  }
}

const loadProjects = async () => {
  try {
    const response = await fetch('/api/bid-assistant/projects')
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        projectList.value = data.projects || []
      }
    }
  } catch (error) {
    console.error('加载项目列表失败:', error)
  }
}

const selectProject = (project: Project) => {
  selectedProject.value = project
  parseResult.value = {
    bidDate: project.bidDate,
    bidTime: project.bidTime,
    bidderName: project.bidderName,
    agencyName: project.agencyName,
    disqualificationItems: JSON.parse(project.disqualificationItems || '[]'),
    evaluationCriteria: JSON.parse(project.evaluationCriteria || '[]'),
    otherInfo: project.otherInfo
  }
  projectName.value = project.name
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.bid-assistant {
  display: flex;
  gap: 30px;
  width: 100%;
}

.main-section {
  flex: 1;
}

.sidebar-section {
  width: 320px;
  flex-shrink: 0;
}

.input-section {
  margin-bottom: 30px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.08) 0%, rgba(126, 200, 227, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--macaron-border);
}

.input-section h4 {
  margin-top: 0;
  margin-bottom: 20px;
  color: var(--macaron-text);
  font-size: 16px;
}

.form-row {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.form-row label {
  width: 120px;
  font-weight: 600;
  text-align: right;
  flex-shrink: 0;
  color: var(--macaron-text);
}

.form-control {
  flex: 1;
  padding: 12px 14px;
  border: 2px solid var(--macaron-border);
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.3s ease;
  background: white;
  color: var(--macaron-text);
}

.form-control:focus {
  outline: none;
  border-color: var(--macaron-mint);
  box-shadow: 0 0 0 3px rgba(168, 230, 207, 0.3);
}

.file-upload-container {
  flex: 1;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: nowrap;
}

.file-path-input {
  flex: 0 1 320px;
  max-width: 320px;
  min-width: 200px;
  background-color: white;
}

.file-input {
  display: none;
}

.file-select-btn {
  white-space: nowrap;
  padding: 10px 16px;
  flex-shrink: 0;
}

.btn {
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.btn-primary {
  background: linear-gradient(135deg, var(--macaron-coral) 0%, var(--macaron-peach) 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--macaron-coral-dark) 0%, var(--macaron-coral) 100%);
}

.btn-success {
  background: linear-gradient(135deg, var(--macaron-mint) 0%, var(--macaron-mint-dark) 100%);
  color: white;
}

.btn-secondary {
  background: linear-gradient(135deg, var(--macaron-lavender) 0%, #D4C4F0 100%);
  color: white;
}

.btn-sm {
  padding: 8px 16px;
  font-size: 13px;
}

.form-row button {
  margin-left: 136px;
}

.result-section {
  padding: 24px;
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.1) 0%, rgba(126, 200, 227, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--macaron-border);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.result-header h4 {
  margin: 0;
  color: var(--macaron-text);
  font-size: 16px;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.result-content {
  color: var(--macaron-text);
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.result-item {
  background: white;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--macaron-border);
}

.result-label {
  display: block;
  font-size: 13px;
  color: var(--macaron-text-light);
  margin-bottom: 8px;
}

.result-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--macaron-coral);
}

.result-section-item {
  background: white;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid var(--macaron-border);
  margin-bottom: 16px;
}

.result-section-item:last-child {
  margin-bottom: 0;
}

.result-section-item h5 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--macaron-text);
}

.result-list {
  margin: 0;
  padding-left: 20px;
}

.result-list li {
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--macaron-text);
}

.result-list li:last-child {
  margin-bottom: 0;
}

.result-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--macaron-text);
}

.sidebar-section {
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.08) 0%, rgba(195, 177, 225, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--macaron-border);
  padding: 20px;
}

.sidebar-section h4 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: var(--macaron-text);
}

.empty-state {
  text-align: center;
  padding: 30px 0;
  color: var(--macaron-text-light);
  font-size: 14px;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 500px;
  overflow-y: auto;
}

.project-item {
  background: white;
  padding: 14px;
  border-radius: 10px;
  border: 1px solid var(--macaron-border);
  cursor: pointer;
  transition: all 0.3s ease;
}

.project-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  border-color: var(--macaron-mint);
}

.project-item.active {
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.1) 0%, rgba(126, 200, 227, 0.1) 100%);
  border-color: var(--macaron-mint);
}

.project-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--macaron-text);
  margin-bottom: 4px;
}

.project-date {
  font-size: 12px;
  color: var(--macaron-text-light);
}
</style>