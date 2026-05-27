<template>
  <div class="bid-tool">
    <div v-if="activeTab === 'price-adjustment'" class="tab-content">
      <div class="upload-section">
        <div class="form-row">
          <label for="totalPrice">目标总价：</label>
          <input 
            type="number" 
            id="totalPrice" 
            v-model.number="targetTotalPrice" 
            min="0"
            step="0.01"
            class="form-control"
            placeholder="请输入目标总价"
          >
        </div>
        <div class="form-row file-upload-row">
          <label for="excelFile">上传文件：</label>
          <div class="file-upload-container">
            <input 
              type="text" 
              v-model="selectedFilePath" 
              readonly 
              class="form-control file-path-input"
              placeholder="请选择Excel文件"
            >
            <input 
              type="file" 
              id="excelFile" 
              ref="fileInput"
              accept=".xlsx, .xls"
              class="file-input"
              @change="handleFileSelect"
            >
            <button type="button" class="btn btn-secondary file-select-btn" @click="openFileDialog">选择文件</button>
            <a href="/分项报价表模板.xlsx" download="分项报价表模板.xlsx" class="btn btn-secondary file-select-btn">下载模板</a>
          </div>
        </div>
        <div class="form-row">
          <label for="limitPrice">是否限价：</label>
          <div class="radio-group">
            <label>
              <input type="radio" v-model="limitPrice" :value="false" checked>
              <span>否</span>
            </label>
            <label>
              <input type="radio" v-model="limitPrice" :value="true">
              <span>是</span>
            </label>
          </div>
          <button @click="processExcel" class="btn btn-primary">开始处理</button>
        </div>
        <div class="form-row">
          <label>价格浮动区间：</label>
          <div class="price-range-container">
            <input 
              type="number" 
              v-model.number="priceMin" 
              min="0" 
              max="100"
              step="1"
              class="form-control price-input"
              placeholder="下限(%)"
            >
            <span class="range-separator">-</span>
            <input 
              type="number" 
              v-model.number="priceMax" 
              min="0" 
              max="100"
              step="1"
              class="form-control price-input"
              placeholder="上限(%)"
            >
          </div>
        </div>
      </div>
      
      <div v-if="processedFileUrl" class="result-section">
        <div class="result-header">
          <h4>处理结果</h4>
          <span class="result-badge success">✓ 处理完成</span>
        </div>
        <p>文件处理完成，点击下方链接下载处理后的文件：</p>
        <a :href="processedFileUrl" :download="processedFileName" class="btn btn-success">
          <span>📥</span> 下载文件
        </a>
      </div>
    </div>
    
    <div v-if="activeTab === 'place-search'" class="tab-content">
      <div class="place-search-section">
        <h4>地名查询</h4>
        <div class="form-row">
          <label for="placeFile">上传文件：</label>
          <div class="file-upload-container">
            <input 
              type="text" 
              v-model="selectedPlaceFilePath" 
              readonly 
              class="form-control file-path-input"
              placeholder="请选择文件"
            >
            <input 
              type="file" 
              id="placeFile" 
              ref="placeFileInput"
              accept=".doc, .docx, .xls, .xlsx"
              class="file-input"
              @change="handlePlaceFileSelect"
            >
            <button type="button" class="btn btn-secondary file-select-btn" @click="openPlaceFileDialog">选择文件</button>
          </div>
        </div>
        <div class="form-row">
          <label for="customKeywords">自定义关键词：</label>
          <input 
            type="text" 
            id="customKeywords" 
            v-model="customKeywords" 
            class="form-control"
            placeholder="多个关键词用逗号分隔"
          >
        </div>
        <div class="form-row">
          <button @click="searchPlaces" class="btn btn-primary">开始查询</button>
        </div>
        
        <div v-if="placeResults.length > 0" class="result-section">
          <div class="result-header">
            <h4>查询结果</h4>
            <span class="result-badge info">找到 {{ placeResults.length }} 个匹配</span>
          </div>
          <div class="results-list">
            <div v-for="(result, index) in placeResults" :key="index" class="result-item">
              <div class="result-header-row">
                <span class="result-place">{{ result.place }}</span>
                <span class="result-location">{{ result.location }}</span>
              </div>
              <div class="result-text">{{ result.text }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="place-management-section">
        <div class="management-header" @click="isManagementExpanded = !isManagementExpanded">
          <h4>地名管理</h4>
          <div class="expand-icon" :class="{ rotated: isManagementExpanded }">▼</div>
        </div>
        
        <div v-if="isManagementExpanded" class="management-content">
          <div class="add-place-section">
            <h5>添加地名</h5>
            <div class="form-row">
              <label for="newPlace">地名：</label>
              <input 
                type="text" 
                id="newPlace" 
                v-model="newPlace" 
                class="form-control narrow-input"
                placeholder="请输入地名"
              >
            </div>
            <div class="form-row flex-right">
              <label for="placeLevel">级别：</label>
              <select 
                id="placeLevel" 
                v-model="placeLevel" 
                class="form-control narrow-input"
              >
                <option value="市级">市级</option>
                <option value="区级">区级</option>
              </select>
              <button @click="addPlace" class="btn btn-primary">添加地名</button>
            </div>
            
            <div class="existing-places-section">
              <div class="region-section">
                <h5>省级行政区</h5>
                <div class="region-tags">
                  <div 
                    v-for="(place, index) in allPlaces.provinces" 
                    :key="index" 
                    class="region-tag"
                  >
                    <span class="tag-name">{{ place.name || place }}</span>
                    <button 
                      v-if="place.name !== '北京市' && place.name !== '上海市' && place.name !== '天津市' && place.name !== '重庆市'" 
                      @click="deletePlace(place.name || place, '省级')"
                      class="delete-btn"
                      title="删除"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
              
              <div class="region-section">
                <h5>市级行政区</h5>
                <div class="region-tags">
                  <div 
                    v-for="(place, index) in allPlaces.cities" 
                    :key="index" 
                    class="region-tag"
                  >
                    <span class="tag-name">{{ place }}</span>
                    <button 
                      @click="deletePlace(place, '市级')"
                      class="delete-btn"
                      title="删除"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
              
              <div class="region-section">
                <h5>区级行政区</h5>
                <div class="region-tags">
                  <div 
                    v-for="(place, index) in allPlaces.districts" 
                    :key="index" 
                    class="region-tag"
                  >
                    <span class="tag-name">{{ place }}</span>
                    <button 
                      @click="deletePlace(place, '区级')"
                      class="delete-btn"
                      title="删除"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'bid-analysis'" class="tab-content">
      <BidAssistant />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, defineProps } from 'vue'
import BidAssistant from './BidAssistant.vue'

defineProps<{
  activeTab: string
}>()

const targetTotalPrice = ref(0)
const limitPrice = ref(false)
const priceMin = ref(50)
const priceMax = ref(95)
const processedFileUrl = ref('')
const processedFileName = ref('')
const fileInput = ref<HTMLInputElement>()
const selectedFilePath = ref('')

const placeFileInput = ref<HTMLInputElement>()
const selectedPlaceFilePath = ref('')
const customKeywords = ref('')
const placeResults = ref<any[]>([])

const newPlace = ref('')
const placeLevel = ref('市级')
const allPlaces = ref({
  provinces: [],
  cities: [],
  districts: []
})
const isManagementExpanded = ref(false)

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFilePath.value = target.files[0].path || target.files[0].name
  }
}

const openFileDialog = () => {
  fileInput.value?.click()
}

const processExcel = async () => {
  const file = fileInput.value?.files?.[0]
  if (!file) {
    alert('请选择Excel文件')
    return
  }
  
  if (!targetTotalPrice.value) {
    alert('请输入目标总价')
    return
  }
  
  const formData = new FormData()
  formData.append('file', file)
  formData.append('targetTotalPrice', targetTotalPrice.value.toString())
  formData.append('limitPrice', limitPrice.value.toString())
  formData.append('priceMin', priceMin.value.toString())
  formData.append('priceMax', priceMax.value.toString())
  
  try {
    const response = await fetch('/api/process-excel', {
      method: 'POST',
      body: formData
    })
    
    if (response.ok) {
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      processedFileUrl.value = url
      processedFileName.value = `NEW_${file.name}`
    } else {
      alert('文件处理失败')
    }
  } catch (error) {
    console.error('文件处理失败:', error)
    alert('文件处理失败')
  }
}

const handlePlaceFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedPlaceFilePath.value = target.files[0].path || target.files[0].name
  }
}

const openPlaceFileDialog = () => {
  placeFileInput.value?.click()
}

const searchPlaces = async () => {
  const file = placeFileInput.value?.files?.[0]
  if (!file) {
    alert('请选择文件')
    return
  }
  
  const formData = new FormData()
  formData.append('file', file)
  
  if (customKeywords.value) {
    const keywords = customKeywords.value.split(',').map(keyword => keyword.trim())
    keywords.forEach((keyword, index) => {
      formData.append(`keywords[${index}]`, keyword)
    })
  }
  
  try {
    const response = await fetch('/api/file-parse', {
      method: 'POST',
      body: formData
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        placeResults.value = data.matches || []
      } else {
        alert('文件处理失败: ' + (data.message || '未知错误'))
      }
    } else {
      alert('文件处理失败')
    }
  } catch (error) {
    console.error('文件处理失败:', error)
    alert('文件处理失败')
  }
}

const loadPlaces = async () => {
  try {
    const response = await fetch('/api/places')
    if (response.ok) {
      const data = await response.json()
      allPlaces.value = data
    }
  } catch (error) {
    console.error('获取地名数据失败:', error)
  }
}

const addPlace = async () => {
  if (!newPlace.value) {
    alert('请输入地名')
    return
  }
  
  try {
    const response = await fetch('/api/places/add', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        place: newPlace.value,
        level: placeLevel.value
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        alert('地名添加成功')
        newPlace.value = ''
        loadPlaces()
      } else {
        alert('添加失败: ' + (data.message || '未知错误'))
      }
    } else {
      alert('添加失败')
    }
  } catch (error) {
    console.error('添加地名失败:', error)
    alert('添加失败')
  }
}

const deletePlace = async (place: string, level: string) => {
  if (!confirm(`确定要删除地名 "${place}" 吗？`)) {
    return
  }
  
  try {
    const response = await fetch('/api/places/delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        place: place,
        level: level
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        alert('地名删除成功')
        loadPlaces()
      } else {
        alert('删除失败: ' + (data.message || '未知错误'))
      }
    } else {
      alert('删除失败')
    }
  } catch (error) {
    console.error('删除地名失败:', error)
    alert('删除失败')
  }
}

onMounted(() => {
  loadPlaces()
})
</script>

<style scoped>
.bid-tool {
  width: 100%;
}

.tab-content {
  min-height: 400px;
}

.upload-section,
.place-search-section {
  margin-bottom: 30px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.08) 0%, rgba(126, 200, 227, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--macaron-border);
}

.place-search-section h4 {
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

.price-range-container {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.price-input {
  width: 120px;
  text-align: center;
}

.range-separator {
  font-weight: 600;
  color: var(--macaron-text-light);
}

.radio-group {
  display: flex;
  gap: 24px;
  align-items: center;
}

.radio-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  width: auto;
  text-align: left;
  cursor: pointer;
}

.radio-group input[type="radio"] {
  width: 18px;
  height: 18px;
  accent-color: var(--macaron-coral);
}

.form-row button {
  margin-left: 136px;
}

.form-row.flex-right {
  justify-content: flex-end;
}

.form-row.flex-right label {
  text-align: left;
  width: auto;
  margin-right: 8px;
}

.form-control.narrow-input {
  max-width: 200px;
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

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.btn-primary {
  background: linear-gradient(135deg, var(--macaron-coral) 0%, var(--macaron-peach) 100%);
  color: white;
}

.btn-primary:hover {
  background: linear-gradient(135deg, var(--macaron-coral-dark) 0%, var(--macaron-coral) 100%);
}

.btn-success {
  background: linear-gradient(135deg, var(--macaron-mint) 0%, var(--macaron-mint-dark) 100%);
  color: white;
}

.btn-success:hover {
  background: linear-gradient(135deg, var(--macaron-mint-dark) 0%, #78D0B0 100%);
}

.btn-secondary {
  background: linear-gradient(135deg, var(--macaron-lavender) 0%, #D4C4F0 100%);
  color: white;
}

.btn-secondary:hover {
  background: linear-gradient(135deg, var(--macaron-lavender-dark) 0%, var(--macaron-lavender) 100%);
}

.result-section {
  margin-top: 24px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.1) 0%, rgba(126, 200, 227, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--macaron-border);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.result-header h4 {
  margin: 0;
  color: var(--macaron-text);
}

.result-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.result-badge.success {
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.3) 0%, rgba(136, 216, 176, 0.3) 100%);
  color: #27ae60;
}

.result-badge.info {
  background: linear-gradient(135deg, rgba(126, 200, 227, 0.3) 0%, rgba(107, 184, 211, 0.3) 100%);
  color: #3498db;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  background: white;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--macaron-border);
  transition: all 0.3s ease;
}

.result-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.result-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-place {
  font-weight: 600;
  color: var(--macaron-coral);
  font-size: 15px;
}

.result-location {
  font-size: 12px;
  color: var(--macaron-text-light);
  padding: 2px 8px;
  background: rgba(126, 200, 227, 0.15);
  border-radius: 12px;
}

.result-text {
  font-size: 14px;
  line-height: 1.5;
  color: var(--macaron-text);
}

.place-management-section {
  margin-top: 30px;
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.08) 0%, rgba(195, 177, 225, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--macaron-border);
  overflow: hidden;
}

.management-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.management-header:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.management-header h4 {
  margin: 0;
  color: var(--macaron-text);
  font-size: 16px;
}

.expand-icon {
  font-size: 12px;
  color: var(--macaron-text-light);
  transition: transform 0.3s ease;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.management-content {
  padding: 24px;
}

.add-place-section {
  margin-bottom: 24px;
}

.add-place-section h5,
.region-section h5 {
  margin-top: 0;
  margin-bottom: 16px;
  color: var(--macaron-text);
  font-size: 14px;
  font-weight: 600;
}

.existing-places-section {
  margin-top: 24px;
}

.region-section {
  margin-bottom: 24px;
}

.region-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  background: white;
  padding: 16px;
  border: 1px solid var(--macaron-border);
  border-radius: 10px;
}

.region-tag {
  position: relative;
  display: inline-flex;
  align-items: center;
  background: linear-gradient(135deg, rgba(168, 230, 207, 0.1) 0%, rgba(126, 200, 227, 0.1) 100%);
  border: 1px solid var(--macaron-border);
  border-radius: 20px;
  padding: 8px 14px;
  font-size: 14px;
  transition: all 0.2s ease;
}

.region-tag:hover {
  background: rgba(168, 230, 207, 0.2);
  border-color: var(--macaron-mint);
}

.tag-name {
  margin-right: 8px;
  color: var(--macaron-text);
}

.delete-btn {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border: none;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  padding: 0;
  flex-shrink: 0;
}

.region-tag:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
}

.btn-danger {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
}

.btn-danger:hover {
  background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
}

.btn-sm {
  padding: 6px 14px;
  font-size: 12px;
  border-radius: 8px;
}
</style>