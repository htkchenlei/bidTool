<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="sidebar-logo">⚙️</span>
        <span class="sidebar-title">投标工具</span>
      </div>
      
      <nav class="sidebar-nav">
        <button 
          class="nav-item" 
          :class="{ active: activeTab === 'price-adjustment' }"
          @click="activeTab = 'price-adjustment'"
        >
          <span class="nav-icon">💰</span>
          价格调整
        </button>
        <button 
          class="nav-item" 
          :class="{ active: activeTab === 'place-search' }"
          @click="activeTab = 'place-search'"
        >
          <span class="nav-icon">📍</span>
          地名查询
        </button>
        <button 
          class="nav-item" 
          :class="{ active: activeTab === 'bid-analysis' }"
          @click="activeTab = 'bid-analysis'"
        >
          <span class="nav-icon">📄</span>
          招标解析
        </button>
      </nav>
      
      <div class="sidebar-footer">
        <button class="settings-btn" @click="showSettings = true">
          <span class="settings-icon">⚙️</span>
          设置
        </button>
      </div>
    </aside>
    
    <main class="main-content">
      <BidTool :active-tab="activeTab" @update:active-tab="activeTab = $event" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import BidTool from './views/BidTool.vue'

const activeTab = ref('price-adjustment')
const showSettings = ref(false)
</script>

<style scoped>
.app-container {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 200px;
  background: linear-gradient(180deg, var(--macaron-mint) 0%, rgba(168, 230, 207, 0.8) 100%);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  margin-bottom: 20px;
}

.sidebar-logo {
  font-size: 28px;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 700;
  color: white;
}

.sidebar-nav {
  flex: 1;
  padding: 0 12px;
}

.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  margin-bottom: 8px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: white;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.2);
}

.nav-item.active {
  background: white;
  color: var(--macaron-text);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.nav-icon {
  font-size: 18px;
}

.sidebar-footer {
  padding: 0 12px;
}

.settings-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(135deg, var(--macaron-lavender) 0%, #D4C4F0 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.settings-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  background: linear-gradient(135deg, var(--macaron-lavender-dark) 0%, var(--macaron-lavender) 100%);
}

.settings-icon {
  font-size: 16px;
}

.main-content {
  flex: 1;
  padding: 30px 40px;
  overflow-y: auto;
}
</style>