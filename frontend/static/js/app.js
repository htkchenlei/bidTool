/**
 * BidTool — 投标工具 Vue 3 应用逻辑
 * 7 个导航模块：工作台 / 文件管理 / 招标分析 / 资质管理 / 区域查询 / 报价调整 / 历史记录
 * + 底部设置入口
 */
const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

createApp({
  setup() {
    // ── 状态 ────────────────────────────────────────────────
    const activeView = ref('dashboard');
    const sidebarCollapsed = ref(false);
    const apiStatus = ref(true);
    const searchQuery = ref('');

    // ── 导航项 ──────────────────────────────────────────────
    const mainNavItems = ref([
      {
        id: 'dashboard',
        label: '工作台',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.8"/>
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.8"/>
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.8"/>
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.8"/>
        </svg>`,
      },
      {
        id: 'files',
        label: '文件管理',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        </svg>`,
        count: null,
      },
      {
        id: 'certs',
        label: '资质管理',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="8" r="6" stroke="currentColor" stroke-width="1.8"/>
          <path d="M8.56 14.3a4 4 0 1 0 6.88 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        </svg>`,
      },
      {
        id: 'performance',
        label: '业绩管理',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2l3 6 6.5 1-4.7 4.6 1.1 6.4L12 17.5 6.1 20l1.1-6.4L2.5 9 9 8z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        </svg>`,
      },
      {
        id: 'analysis',
        label: '招标分析',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
        count: null,
      },
      {
        id: 'bid_compare',
        label: '投标比对',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M12 3v18" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
        </svg>`,
      },
      {
        id: 'region',
        label: '区域查询',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" stroke-width="1.8"/>
          <circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="1.8"/>
        </svg>`,
      },
      {
        id: 'pricing',
        label: '报价调整',
        icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <line x1="12" y1="1" x2="12" y2="23" stroke="currentColor" stroke-width="1.8"/>
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
      },
    ]);

    const toolNavItems = ref([]);

    // ── 文件管理 ────────────────────────────────────────────
    const files = ref([]);
    const folders = ref([]);
    const currentFolder = ref('');
    const showNewFolder = ref(false);
    const newFolderName = ref('');
    const creating = ref(false);

    const loadFiles = async () => {
      try {
        const url = currentFolder.value ? `/api/files?folder=${encodeURIComponent(currentFolder.value)}` : '/api/files';
        const res = await fetch(url);
        const data = await res.json();
        files.value = data.files || [];
        folders.value = data.folders || [];
      } catch { apiStatus.value = false; }
    };

    const uploadFiles = async (e) => {
      const fileList = e.target.files;
      if (!fileList.length) return;
      const form = new FormData();
      if (currentFolder.value) form.append('folder', currentFolder.value);
      for (const f of fileList) form.append('file', f);
      try {
        await fetch('/api/files/upload', { method: 'POST', body: form });
        await loadFiles();
      } catch {}
      e.target.value = '';
    };

    const createFolder = async () => {
      const name = newFolderName.value.trim();
      if (!name || creating.value) return;
      creating.value = true;
      try {
        const body = { name };
        if (currentFolder.value) body.parent = currentFolder.value;
        const res = await fetch('/api/files/folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (data.success) {
          newFolderName.value = '';
          showNewFolder.value = false;
          await loadFiles();
        } else {
          alert(data.message || '创建失败');
        }
      } catch (e) {
        alert('创建失败：服务未连接，请确认后端已启动');
      }
      creating.value = false;
    };

    const enterFolder = async (name) => {
      currentFolder.value = currentFolder.value ? `${currentFolder.value}/${name}` : name;
      await loadFiles();
    };

    const navigateToFolder = async (path) => {
      currentFolder.value = path;
      await loadFiles();
    };

    const deleteFolder = async (name) => {
      if (!confirm(`确认删除文件夹「${name}」及其所有内容？`)) return;
      const folderPath = currentFolder.value ? `${currentFolder.value}/${name}` : name;
      await fetch(`/api/files/folder/${encodeURIComponent(folderPath)}`, { method: 'DELETE' });
      await loadFiles();
    };

    const deleteFile = async (name) => {
      if (!confirm(`确认删除文件「${name}」？`)) return;
      const filePath = currentFolder.value ? `${currentFolder.value}/${name}` : name;
      await fetch(`/api/files/${encodeURIComponent(filePath)}`, { method: 'DELETE' });
      await loadFiles();
    };

    const formatSize = (bytes) => {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    const formatDate = (ts) => {
      const d = new Date(ts * 1000);
      return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    };

    const getFileEmoji = (type) => {
      const map = { PDF: '📄', DOCX: '📝', DOC: '📝', XLSX: '📊', XLS: '📊', ZIP: '🗜', RAR: '🗜', PNG: '🖼', JPG: '🖼', JPEG: '🖼' };
      return map[type] || '📁';
    };

    // ── 项目管理 ────────────────────────────────────────────
    const projects = ref([]);
    const currentProject = ref(null);
    const projectFiles = ref([]);
    const currentProjectFields = ref([]);
    const currentProjectRisks = ref([]);
    const projectTab = ref('fields');
    const projectSearchKeyword = ref('');
    const showNewProject = ref(false);
    const newProject = reactive({
      announcement_url: '',
      creating: false
    });
    const newProjectFiles = ref([]);
    const newProjectUploadDragover = ref(false);
    const newProjectFilesInput = ref(null);
    const analyzingProjects = reactive({});
    const reAnalyzing = ref(false);
    const extracting = ref(false);
    const editingField = ref(null);
    const fieldEditValue = ref('');

    const loadProjects = async () => {
      try {
        const params = new URLSearchParams();
        if (projectSearchKeyword.value) params.set('keyword', projectSearchKeyword.value);
        const res = await fetch(`/api/projects?${params.toString()}`);
        const data = await res.json();
        projects.value = data.projects || [];
      } catch {}
    };

    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    };

    // 取消新建项目：重置全部状态
    const cancelNewProject = () => {
      showNewProject.value = false;
      newProject.announcement_url = '';
      newProject.creating = false;
      newProjectFiles.value = [];
    };

    // 删除项目
    const deleteProject = async (projectId, event) => {
      if (event) event.stopPropagation();
      if (!confirm('确定删除该项目？所有关联文件、字段和风险数据都将被删除。')) {
        return;
      }
      try {
        const res = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); }
        catch { alert('服务器返回异常，请刷新页面后重试'); return; }
        if (data.success) {
          // 如果当前打开的就是被删除的项目，回到列表
          if (currentProject.value && currentProject.value.id === projectId) {
            currentProject.value = null;
          }
          await loadProjects();
        } else {
          alert('删除失败: ' + (data.message || '未知错误'));
        }
      } catch (e) {
        console.error('删除项目失败:', e);
        alert('删除项目失败: ' + (e.message || e));
      }
    };

    // 处理文件拖放
    const handleNewProjectFileDrop = (e) => {
      newProjectUploadDragover.value = false;
      const files = Array.from(e.dataTransfer.files);
      addNewProjectFiles(files);
    };

    // 处理文件选择
    const handleNewProjectFileSelect = (e) => {
      const files = Array.from(e.target.files);
      addNewProjectFiles(files);
      e.target.value = '';
    };

    // 添加文件到列表
    const addNewProjectFiles = (files) => {
      const allowedTypes = ['.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.zip', '.rar'];
      for (const file of files) {
        const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
        if (allowedTypes.includes(ext)) {
          // 避免重复添加
          if (!newProjectFiles.value.some(f => f.name === file.name && f.size === file.size)) {
            newProjectFiles.value.push(file);
          }
        }
      }
    };

    // 移除文件
    const removeNewProjectFile = (idx) => {
      newProjectFiles.value.splice(idx, 1);
    };

    // 创建项目（后端会自动抓取公告并上传文件）
    const createProject = async () => {
      if (!newProject.announcement_url) return;
      newProject.creating = true;
      try {
        const form = new FormData();
        form.append('url', newProject.announcement_url);
        for (const file of newProjectFiles.value) {
          form.append('files', file);
        }
        const res = await fetch('/api/projects', { method: 'POST', body: form });
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); } catch { alert('服务器返回异常，请刷新页面重试'); return; }
        if (!data.success) {
          alert(data.message || '创建失败');
          return;
        }
        showNewProject.value = false;
        newProject.announcement_url = '';
        newProject.creating = false;
        newProjectFiles.value = [];
        await loadProjects();
      } catch (e) {
        console.error('创建项目失败:', e);
        alert('创建项目失败：' + (e.message || e));
      } finally {
        newProject.creating = false;
      }
    };

    // 开始分析：解析文件并调用 AI 提取
    const analyzeProject = async (projectId) => {
      analyzingProjects[projectId] = true;
      // 乐观更新本地列表状态，使列表页也能正确显示"分析中"
      const proj = projects.value.find(p => p.id === projectId);
      if (proj) proj.status = 'analyzing';
      try {
        const res = await fetch(`/api/projects/${projectId}/analyze`, { method: 'POST' });
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); }
        catch { alert('服务器返回异常，请刷新页面后重试'); return; }
        if (!data.success) {
          alert(data.message || '分析失败');
          // 分析失败，恢复原状态
          if (proj) proj.status = data.status || proj.status || 'pending';
        } else {
          await loadProjects();
        }
      } catch (e) {
        console.error('分析失败:', e);
        alert('分析失败：' + (e.message || e));
        // 异常时恢复原状态
        if (proj) proj.status = proj.status === 'analyzing' ? 'pending' : proj.status;
      } finally {
        analyzingProjects[projectId] = false;
      }
    };

    // 重新分析：在项目详情页使用，用当前AI模型重新提取字段和风险
    const reAnalyzeProject = async (projectId) => {
      if (!confirm('确定要重新分析吗？将使用当前设置的 AI 模型，对公告网页和上传文件重新提取信息。')) return;
      reAnalyzing.value = true;
      // 乐观更新本地列表状态和当前项目状态，使列表页也能正确显示"分析中"
      const proj = projects.value.find(p => p.id === projectId);
      if (proj) proj.status = 'analyzing';
      if (currentProject.value && currentProject.value.id === projectId) {
        currentProject.value.status = 'analyzing';
      }
      try {
        const res = await fetch(`/api/projects/${projectId}/analyze`, { method: 'POST' });
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); }
        catch { alert('服务器返回异常，请重试'); return; }
        if (!data.success) {
          alert(data.message || '重新分析失败');
          // 分析失败，恢复原状态
          if (proj) proj.status = data.status || proj.status || 'completed';
          if (currentProject.value && currentProject.value.id === projectId) {
            currentProject.value.status = proj ? proj.status : 'completed';
          }
        } else {
          // 刷新当前项目详情（字段和风险）
          await openProject(projectId);
          await loadProjects();
        }
      } catch (e) {
        console.error('重新分析失败:', e);
        alert('重新分析失败：' + (e.message || e));
        // 异常时恢复原状态
        if (proj) proj.status = proj.status === 'analyzing' ? 'completed' : proj.status;
        if (currentProject.value && currentProject.value.id === projectId) {
          currentProject.value.status = proj ? proj.status : 'completed';
        }
      } finally {
        reAnalyzing.value = false;
      }
    };

    const openProject = async (projectId) => {
      try {
        const res = await fetch(`/api/projects/${projectId}`);
        const data = await res.json();
        if (data.project) {
          currentProject.value = data.project;
          projectFiles.value = data.files || [];
          currentProjectFields.value = data.fields || [];
          currentProjectRisks.value = data.risks || [];
          projectTab.value = 'fields';
        }
      } catch {}
    };

    const closeProject = () => {
      currentProject.value = null;
      projectFiles.value = [];
      currentProjectFields.value = [];
      currentProjectRisks.value = [];
    };

    const uploadProjectFiles = async (e) => {
      const fileList = e.target.files;
      if (!fileList.length || !currentProject.value) return;
      for (const f of fileList) {
        const form = new FormData();
        form.append('file', f);
        try {
          await fetch(`/api/projects/${currentProject.value.id}/files`, { method: 'POST', body: form });
        } catch {}
      }
      e.target.value = '';
      await loadProjectFiles();
    };

    const loadProjectFiles = async () => {
      if (!currentProject.value) return;
      try {
        const res = await fetch(`/api/projects/${currentProject.value.id}/files`);
        const data = await res.json();
        projectFiles.value = data.files || [];
      } catch {}
    };

    const parseProjectFile = async (file) => {
      try {
        await fetch(`/api/projects/${currentProject.value.id}/files/${file.id}/parse`, { method: 'POST' });
        await loadProjectFiles();
      } catch {}
    };

    const parseAllProjectFiles = async () => {
      try {
        await fetch(`/api/projects/${currentProject.value.id}/parse-all`, { method: 'POST' });
        await loadProjectFiles();
      } catch {}
    };

    const extractProjectInfo = async () => {
      if (!currentProject.value) return;
      extracting.value = true;
      try {
        const res = await fetch(`/api/projects/${currentProject.value.id}/extract`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          await openProject(currentProject.value.id);
        } else {
          alert(data.message || 'AI 提取失败');
        }
      } catch (e) {
        alert('AI 提取请求失败');
      }
      extracting.value = false;
    };

    const deleteProjectFile = async (file) => {
      if (!confirm(`确认删除文件「${file.original_name}」？`)) return;
      try {
        await fetch(`/api/projects/${currentProject.value.id}/files/${file.id}`, { method: 'DELETE' });
        await loadProjectFiles();
      } catch {}
    };

    const downloadProjectFile = (file) => {
      window.open(`/api/projects/${currentProject.value.id}/files/${file.id}/download`, '_blank');
    };

    const startEditField = (field) => {
      editingField.value = field.id;
      fieldEditValue.value = field.confirmed_value || field.machine_value || '';
    };

    const saveFieldReview = async (field) => {
      try {
        await fetch(`/api/projects/${currentProject.value.id}/fields/${field.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmed_value: fieldEditValue.value, review_status: 'modified' }),
        });
        field.confirmed_value = fieldEditValue.value;
        field.review_status = 'modified';
        editingField.value = null;
      } catch {}
    };

    const copyFieldValue = async (field) => {
      const value = field.machine_value || '';
      try {
        await navigator.clipboard.writeText(value);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = value;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch {}
        document.body.removeChild(ta);
      }
    };

    const confirmRisk = async (risk) => {
      try {
        await fetch(`/api/projects/${currentProject.value.id}/risks/${risk.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ review_status: 'confirmed' }),
        });
        risk.review_status = 'confirmed';
      } catch {}
    };

    const ignoreRisk = async (risk) => {
      try {
        await fetch(`/api/projects/${currentProject.value.id}/risks/${risk.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ review_status: 'ignored' }),
        });
        risk.review_status = 'ignored';
      } catch {}
    };

    const exportProjectFields = () => {
      if (currentProject.value) {
        window.open(`/api/projects/${currentProject.value.id}/export/fields`, '_blank');
      }
    };

    const exportProjectRisks = () => {
      if (currentProject.value) {
        window.open(`/api/projects/${currentProject.value.id}/export/risks`, '_blank');
      }
    };

    const fieldReviewStats = computed(() => {
      const fields = currentProjectFields.value;
      return {
        total: fields.length,
        pending: fields.filter(f => f.review_status === 'pending').length,
        confirmed: fields.filter(f => f.review_status === 'confirmed').length,
        modified: fields.filter(f => f.review_status === 'modified').length,
      };
    });

    const riskReviewStats = computed(() => {
      const risks = currentProjectRisks.value;
      return {
        total: risks.length,
        pending: risks.filter(r => r.review_status === 'pending').length,
        confirmed: risks.filter(r => r.review_status === 'confirmed').length,
      };
    });

    const riskStats = computed(() => {
      const risks = currentProjectRisks.value;
      return {
        high: risks.filter(r => r.severity === 'high').length,
        medium: risks.filter(r => r.severity === 'medium').length,
        low: risks.filter(r => r.severity === 'low').length,
      };
    });

    const getProjectStatusLabel = (status) => {
      const map = { pending: '待分析', analyzing: '分析中', completed: '已完成', parsing: '解析中', parsed: '已解析', extracting: 'AI分析中', reviewing: '复核中' };
      return map[status] || status;
    };

    const getParseStatusLabel = (status) => {
      const map = { pending: '待解析', parsing: '解析中', done: '已解析', failed: '解析失败' };
      return map[status] || status;
    };

    const getFieldReviewLabel = (status) => {
      const map = { pending: '待复核', confirmed: '已确认', modified: '已修改', ignored: '已忽略' };
      return map[status] || status;
    };

    const getRiskReviewLabel = (status) => {
      const map = { pending: '待复核', confirmed: '已确认', ignored: '已忽略' };
      return map[status] || status;
    };

    const getRiskSeverityLabel = (severity) => {
      const map = { high: '高风险', medium: '中风险', low: '低风险', unknown: '待确认' };
      return map[severity] || severity;
    };

    // 兼容旧的分析记录
    const analysisRecords = ref([]);
    const newAnalysis = reactive({ title: '', file: '', options: ['key_info'] });
    const analysisOptions = [
      { value: 'key_info', label: '提取关键信息（时间、金额、条件）' },
      { value: 'risk', label: '风险点分析' },
    ];

    const loadAnalysis = async () => {
      await loadProjects();
      analysisRecords.value = projects.value.slice(0, 5).map(p => ({
        id: p.id, title: p.name, file: '', status: p.status === 'completed' ? 'done' : 'pending', created_at: p.created_at
      }));
    };

    const startAnalysis = async () => {
      if (!newAnalysis.title) return;
      await createProject();
      newAnalysis.title = '';
    };

    // ── 资质管理 ────────────────────────────────────────────
    const certs = ref([]);
    const certCategories = ref([]);
    const certCatFilter = ref('');
    const certFilter = ref('all');
    const showAddCert = ref(false);
    const newCert = reactive({ name: '', type: '', issuer: '', expire: '', category: '' });
    const certFileInput = ref(null);
    const certUploading = ref(false);
    const certOcrDone = ref(false);
    const certUploadDragover = ref(false);
    const certUploadedFile = ref(null);

    // 编辑证书
    const showEditCert = ref(false);
    const editCert = reactive({ id: '', name: '', category: '', issuer: '', expire: '', file_path: '' });

    // 预览证书
    const showPreviewCert = ref(false);
    const currentPreviewCert = ref(null);
    const previewCertUrl = computed(() => {
      if (!currentPreviewCert.value?.file_path) return '';
      const ext = currentPreviewCert.value.file_path.split('.').pop().toLowerCase();
      if (['jpg', 'jpeg', 'png', 'bmp', 'webp'].includes(ext)) {
        return `/api/certs/file/${encodeURIComponent(currentPreviewCert.value.file_path)}`;
      }
      return '';
    });

    // 分类管理
    const showAddCertCat = ref(false);
    const newCertCatName = ref('');
    const renameCertCatTarget = ref(null);
    const renameCertCatName = ref('');

    const filteredCerts = computed(() => {
      let result = certs.value;
      if (certCatFilter.value) {
        result = result.filter(c => (c.category || '未分类') === certCatFilter.value);
      }
      if (certFilter.value === 'valid') {
        result = result.filter(c => c.status !== 'expired');
      } else if (certFilter.value === 'expired') {
        result = result.filter(c => c.status === 'expired');
      }
      return result;
    });

    const loadCerts = async (category = '') => {
      try {
        const url = category ? `/api/certs?category=${encodeURIComponent(category)}` : '/api/certs';
        const res = await fetch(url);
        const data = await res.json();
        certs.value = data.certs || [];
      } catch {}
    };

    const loadCertCategories = async () => {
      try {
        const res = await fetch('/api/certs/categories');
        const data = await res.json();
        certCategories.value = data.categories || [];
      } catch {}
    };

    const loadAllCertsData = async () => {
      await Promise.all([loadCerts(), loadCertCategories()]);
    };

    const resetCertForm = () => {
      Object.assign(newCert, { name: '', type: '', issuer: '', expire: '', category: '' });
      certOcrDone.value = false;
      certUploadedFile.value = null;
    };

    const closeAddCert = () => {
      showAddCert.value = false;
      resetCertForm();
    };

    const triggerCertFileInput = () => {
      if (!certUploading.value) certFileInput.value?.click();
    };

    const uploadCertFileAndRecognize = async (file) => {
      if (!file) return;
      certUploading.value = true;
      certOcrDone.value = false;
      certUploadedFile.value = null;
      try {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/certs/ocr', { method: 'POST', body: form });
        const data = await res.json();
        if (data.success && data.data) {
          Object.assign(newCert, {
            name: data.data.name || '',
            type: data.data.type || '',
            issuer: data.data.issuer || '',
            expire: data.data.expire || '',
            category: data.data.type || '',
          });
          if (data.file) {
            certUploadedFile.value = data.file;
          }
          certOcrDone.value = true;
        } else {
          alert(data.message || '识别失败，请手动填写');
        }
      } catch (e) {
        alert('识别请求失败：服务未连接或模型未配置，请先在设置中启用大模型');
      }
      certUploading.value = false;
    };

    const handleCertFileChange = (e) => {
      const file = e.target.files[0];
      if (file) uploadCertFileAndRecognize(file);
      e.target.value = '';
    };

    const handleCertFileDrop = (e) => {
      certUploadDragover.value = false;
      const file = e.dataTransfer.files[0];
      if (file) uploadCertFileAndRecognize(file);
    };

    const addCert = async () => {
      if (!newCert.name) return;
      const body = {
        name: newCert.name,
        type: newCert.type,
        issuer: newCert.issuer,
        expire: newCert.expire,
        category: newCert.category || newCert.type || '未分类',
      };
      if (certUploadedFile.value) {
        body.file_name = certUploadedFile.value.name;
        body.file_path = certUploadedFile.value.path;
        body.file_size = certUploadedFile.value.size;
      }
      await fetch('/api/certs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      resetCertForm();
      showAddCert.value = false;
      await loadAllCertsData();
    };

    const deleteCert = async (id) => {
      if (!confirm('确认删除该证书？关联文件也将被删除。')) return;
      await fetch(`/api/certs/${id}`, { method: 'DELETE' });
      await loadAllCertsData();
    };

    const downloadCertFile = (cert) => {
      if (cert.id) {
        window.open(`/api/certs/${cert.id}/download`, '_blank');
      }
    };

    // 编辑证书
    const openEditCert = (cert) => {
      Object.assign(editCert, {
        id: cert.id,
        name: cert.name || '',
        category: cert.category || '',
        issuer: cert.issuer || '',
        expire: cert.expire || '',
        file_path: cert.file_path || '',
      });
      showEditCert.value = true;
    };

    const closeEditCert = () => {
      showEditCert.value = false;
    };

    const saveEditCert = async () => {
      if (!editCert.name) return;
      const body = {
        name: editCert.name,
        category: editCert.category,
        issuer: editCert.issuer,
        expire: editCert.expire,
      };
      await fetch(`/api/certs/${editCert.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      showEditCert.value = false;
      await loadAllCertsData();
    };

    // 预览证书
    const previewCert = (cert) => {
      currentPreviewCert.value = cert;
      showPreviewCert.value = true;
    };

    const addCertCategory = async () => {
      const name = newCertCatName.value.trim();
      if (!name) return;
      try {
        await fetch('/api/certs/categories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name }),
        });
      } catch {}
      newCertCatName.value = '';
      showAddCertCat.value = false;
      await loadAllCertsData();
    };

    const startRenameCat = (cat) => {
      renameCertCatTarget.value = cat.name;
      renameCertCatName.value = cat.name;
    };

    const doRenameCat = async () => {
      const newName = renameCertCatName.value.trim();
      if (!newName || !renameCertCatTarget.value) return;
      try {
        await fetch(`/api/certs/categories/${encodeURIComponent(renameCertCatTarget.value)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newName }),
        });
      } catch {}
      renameCertCatTarget.value = null;
      await loadAllCertsData();
    };

    const deleteCertCat = async (cat) => {
      if (!confirm(`确认删除分类「${cat.name}」？分类下的证书将移到「未分类」。`)) return;
      try {
        await fetch(`/api/certs/categories/${encodeURIComponent(cat.name)}`, { method: 'DELETE' });
      } catch {}
      await loadAllCertsData();
    };

    const getCertStatusClass = (cert) => {
      if (cert.status === 'expired') return 'cert-status--expired';
      if (!cert.expire) return 'cert-status--valid';
      const diff = (new Date(cert.expire) - new Date()) / (1000 * 86400);
      if (diff < 0)   return 'cert-status--expired';
      if (diff < 90)  return 'cert-status--warning';
      return 'cert-status--valid';
    };

    const getCertStatusLabel = (cert) => {
      if (cert.status === 'expired') return '已过期';
      if (!cert.expire) return '有效';
      const diff = (new Date(cert.expire) - new Date()) / (1000 * 86400);
      if (diff < 0)  return '已过期';
      if (diff < 30) return `${Math.ceil(diff)} 天后到期`;
      if (diff < 90) return '即将到期';
      return '有效';
    };

    // ── 仪表盘统计 ──────────────────────────────────────────
    const fileCount = computed(() => files.value.length);
    const analysisCount = computed(() => analysisRecords.value.length);
    const certCount = computed(() => certs.value.length);

    const expiringSoon = computed(() => {
      return certs.value.filter(c => {
        if (c.status === 'expired') return true;
        if (!c.expire) return false;
        const diff = (new Date(c.expire) - new Date()) / (1000 * 86400);
        return diff < 90;
      });
    });

    const expiringSoonCount = computed(() => expiringSoon.value.length);

    // ── 区域查询 ────────────────────────────────────────────
    const regions = ref([]);
    const biddingList = ref([]);
    const biddingTotal = ref(0);
    const biddingPage = ref(1);
    const biddingPerPage = ref(15);
    const biddingTotalPages = ref(1);
    const biddingRefreshing = ref(false);
    const bidSearchKeyword = ref('');
    const bidProvinceFilter = ref('');
    const bidCityFilter = ref('');
    const bidCategoryFilter = ref('');
    const bidStatusFilter = ref('');
    const bidCategories = ref([]);
    const bidDetailVisible = ref(false);
    const bidDetail = ref(null);
    const biddingStats = ref({ total: 0, bidding: 0, expiring_soon: 0, awarded: 0 });

    const bidFilterCities = computed(() => {
      const found = regions.value.find(r => r.province === bidProvinceFilter.value);
      return found ? found.cities : [];
    });

    const loadRegions = async () => {
      try {
        const res = await fetch('/api/regions');
        const data = await res.json();
        regions.value = data.regions || [];
        // 提取类别
        const cats = new Set();
        data.regions?.forEach(r => r.cities?.forEach(() => {}));
        bidCategories.value = ['工程建设', 'IT 服务', '咨询服务', '物资采购', '设备采购', '物业服务', '设计服务', '监理服务'];
      } catch {}
    };

    const loadBidding = async (page = 1) => {
      try {
        const params = new URLSearchParams();
        params.set('page', page);
        params.set('per_page', biddingPerPage.value);
        if (bidProvinceFilter.value) params.set('province', bidProvinceFilter.value);
        if (bidCityFilter.value) params.set('city', bidCityFilter.value);
        if (bidCategoryFilter.value) params.set('category', bidCategoryFilter.value);
        if (bidStatusFilter.value) params.set('status', bidStatusFilter.value);
        if (bidSearchKeyword.value) params.set('keyword', bidSearchKeyword.value);

        const res = await fetch(`/api/bidding?${params.toString()}`);
        const data = await res.json();
        biddingList.value = data.items || [];
        biddingTotal.value = data.total || 0;
        biddingPage.value = data.page || 1;
        biddingTotalPages.value = data.total_pages || 1;
      } catch {}
    };

    const loadBiddingStats = async () => {
      try {
        const res = await fetch('/api/bidding/stats');
        const data = await res.json();
        biddingStats.value = {
          total: data.total || 0,
          bidding: data.by_status?.['招标中'] || 0,
          expiring_soon: data.expiring_soon || 0,
          awarded: data.by_status?.['已中标'] || 0,
        };
      } catch {}
    };

    const searchBidding = async () => {
      await loadBidding(1);
    };

    const onBidProvinceChange = () => {
      bidCityFilter.value = '';
      loadBidding(1);
    };

    const goBidPage = async (page) => {
      await loadBidding(page);
    };

    const refreshBidding = async () => {
      biddingRefreshing.value = true;
      try {
        await fetch('/api/bidding/refresh', { method: 'POST' });
        await Promise.all([loadBidding(1), loadBiddingStats()]);
      } catch {}
      biddingRefreshing.value = false;
    };

    const showBidDetail = (item) => {
      bidDetail.value = item;
      bidDetailVisible.value = true;
    };

    const isBidExpiringSoon = (item) => {
      if (!item.deadline || item.status !== '招标中') return false;
      const diff = (new Date(item.deadline) - new Date()) / (1000 * 86400);
      return diff >= 0 && diff <= 7;
    };

    const getBidStatusClass = (item) => {
      if (item.status === '招标中') return 'active';
      if (item.status === '已截止') return 'closed';
      if (item.status === '已中标') return 'awarded';
      return '';
    };

    // ── 报价调整 ────────────────────────────────────────────
    const pricingProjects = ref([]);
    const currentPricingId = ref(null);
    const currentPricing = ref(null);
    const pricingForm = reactive({ name: '', description: '', strategy: 'balanced', profit_rate: 15, tax_rate: 6, discount: 0 });
    const pricingStrategies = ref([
      { id: 'aggressive', name: '激进策略', color: 'peach', desc: '薄利多销' },
      { id: 'balanced', name: '平衡策略', color: 'purple', desc: '兼顾利润与竞争力' },
      { id: 'conservative', name: '保守策略', color: 'mint', desc: '高利润空间' },
    ]);
    const pricingCategories = ref([
      { id: 'labor', name: '人工成本' },
      { id: 'material', name: '材料成本' },
      { id: 'equipment', name: '设备成本' },
      { id: 'service', name: '服务费用' },
      { id: 'travel', name: '差旅费用' },
      { id: 'other', name: '其他费用' },
    ]);
    const showNewPricing = ref(false);
    const newPricingName = ref('');
    const newPricingDesc = ref('');
    const showAddPricingItem = ref(false);
    const newItem = reactive({ name: '', category: 'labor', unit_price: 0, quantity: 1, unit: '项', note: '' });
    let savePricingMetaTimer = null;

    const loadPricingProjects = async () => {
      try {
        const res = await fetch('/api/pricing');
        const data = await res.json();
        pricingProjects.value = data.projects || [];
      } catch {}
    };

    const startNewPricing = () => {
      newPricingName.value = '';
      newPricingDesc.value = '';
      showNewPricing.value = true;
    };

    const createPricingProject = async () => {
      if (!newPricingName.value.trim()) return;
      try {
        const res = await fetch('/api/pricing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newPricingName.value.trim(), description: newPricingDesc.value.trim() }),
        });
        const data = await res.json();
        if (data.success) {
          showNewPricing.value = false;
          await loadPricingProjects();
          await selectPricingProject(data.project.id);
        }
      } catch {}
    };

    const selectPricingProject = async (id) => {
      try {
        const res = await fetch(`/api/pricing/${id}`);
        const data = await res.json();
        if (data.success) {
          currentPricingId.value = id;
          currentPricing.value = data.project;
          Object.assign(pricingForm, {
            name: data.project.name || '',
            description: data.project.description || '',
            strategy: data.project.strategy || 'balanced',
            profit_rate: data.project.profit_rate ?? 15,
            tax_rate: data.project.tax_rate ?? 6,
            discount: data.project.discount ?? 0,
          });
        }
      } catch {}
    };

    const deletePricingProject = async (id) => {
      if (!confirm('确认删除该报价项目？')) return;
      try {
        await fetch(`/api/pricing/${id}`, { method: 'DELETE' });
        if (currentPricingId.value === id) {
          currentPricingId.value = null;
          currentPricing.value = null;
        }
        await loadPricingProjects();
      } catch {}
    };

    const savePricingMeta = async () => {
      if (!currentPricingId.value) return;
      try {
        const res = await fetch(`/api/pricing/${currentPricingId.value}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: pricingForm.name,
            description: pricingForm.description,
            strategy: pricingForm.strategy,
            profit_rate: pricingForm.profit_rate,
            tax_rate: pricingForm.tax_rate,
            discount: pricingForm.discount,
          }),
        });
        const data = await res.json();
        if (data.success) {
          currentPricing.value = data.project;
          await loadPricingProjects();
        }
      } catch {}
    };

    const savePricingMetaDebounced = () => {
      if (savePricingMetaTimer) clearTimeout(savePricingMetaTimer);
      savePricingMetaTimer = setTimeout(savePricingMeta, 400);
    };

    const openAddItem = () => {
      Object.assign(newItem, { name: '', category: 'labor', unit_price: 0, quantity: 1, unit: '项', note: '' });
      showAddPricingItem.value = true;
    };

    const addPricingItem = async () => {
      if (!newItem.name.trim() || !currentPricingId.value) return;
      try {
        const res = await fetch(`/api/pricing/${currentPricingId.value}/items`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newItem),
        });
        const data = await res.json();
        if (data.success) {
          currentPricing.value.items = [...(currentPricing.value.items || []), data.item];
          currentPricing.value.summary = data.summary;
          showAddPricingItem.value = false;
        }
      } catch {}
    };

    const saveItem = async (item) => {
      if (!currentPricingId.value) return;
      try {
        const res = await fetch(`/api/pricing/${currentPricingId.value}/items/${item.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item),
        });
        const data = await res.json();
        if (data.success) {
          currentPricing.value.summary = data.summary;
        }
      } catch {}
    };

    const deleteItem = async (itemId) => {
      if (!currentPricingId.value || !confirm('确认删除该成本项？')) return;
      try {
        const res = await fetch(`/api/pricing/${currentPricingId.value}/items/${itemId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
          currentPricing.value.items = currentPricing.value.items.filter(i => i.id !== itemId);
          currentPricing.value.summary = data.summary;
        }
      } catch {}
    };

    const formatPricingNum = (n) => {
      if (n === undefined || n === null) return '0';
      return Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    // ── 设置 ────────────────────────────────────────────────
    const modelConfigs = ref([]);
    const activeModel = ref('');          // 下拉框当前选中值（编辑态）
    const savedActiveModel = ref('');     // 已保存的活跃模型（用于顶部栏展示）
    const activeModelInfo = computed(() => {
      if (!activeModel.value || !modelConfigs.value.length) return null;
      return modelConfigs.value.find(m => m.id === activeModel.value) || null;
    });
    const savedActiveModelInfo = computed(() => {
      if (!savedActiveModel.value || !modelConfigs.value.length) return null;
      return modelConfigs.value.find(m => m.id === savedActiveModel.value) || null;
    });
    const saving = ref(false);
    const toastVisible = ref(false);
    const showKey = ref({});
    const testingModel = ref(null);
    const testResults = reactive({});

    // 新建模型模态框
    const showNewModelModal = ref(false);
    const newModelForm = reactive({
      name: '',
      api_key: '',
      base_url: '',
      model: '',
      supports_vision: false,
    });
    const newModelTesting = ref(false);
    const newModelTestResult = ref(null); // { ok: bool, msg: string }
    const newModelCreating = ref(false);
    const newModelShowKey = ref(false);

    const resetNewModelForm = () => {
      newModelForm.name = '';
      newModelForm.api_key = '';
      newModelForm.base_url = '';
      newModelForm.model = '';
      newModelForm.supports_vision = false;
      newModelTestResult.value = null;
      newModelShowKey.value = false;
    };

    const openNewModelModal = () => {
      resetNewModelForm();
      showNewModelModal.value = true;
    };

    const testNewModel = async () => {
      if (!newModelForm.api_key || !newModelForm.base_url || !newModelForm.model) {
        newModelTestResult.value = { ok: false, msg: '请填写完整的 API Key / Base URL / 模型名称' };
        return;
      }
      newModelTesting.value = true;
      newModelTestResult.value = null;
      try {
        const res = await fetch('/api/settings/test-model', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_key: newModelForm.api_key,
            base_url: newModelForm.base_url,
            model: newModelForm.model,
          }),
        });
        const data = await res.json();
        newModelTestResult.value = { ok: data.success, msg: data.message };
      } catch (e) {
        newModelTestResult.value = { ok: false, msg: '网络请求失败，请检查后端服务是否运行' };
      }
      newModelTesting.value = false;
    };

    const createModel = async () => {
      if (!newModelForm.name || !newModelForm.api_key || !newModelForm.base_url || !newModelForm.model) {
        newModelTestResult.value = { ok: false, msg: '请填写完整的信息' };
        return;
      }
      // 要求先测试连接
      if (!newModelTestResult.value || !newModelTestResult.value.ok) {
        newModelTestResult.value = { ok: false, msg: '请先测试连接成功后再创建' };
        return;
      }
      newModelCreating.value = true;
      try {
        const res = await fetch('/api/settings/models', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: newModelForm.name,
            api_key: newModelForm.api_key,
            base_url: newModelForm.base_url,
            model: newModelForm.model,
            supports_vision: newModelForm.supports_vision,
          }),
        });
        const data = await res.json();
        if (data.success) {
          toastVisible.value = true;
          setTimeout(() => { toastVisible.value = false; }, 2800);
          showNewModelModal.value = false;
          await loadConfig();
        } else {
          newModelTestResult.value = { ok: false, msg: data.message || '创建失败' };
        }
      } catch (e) {
        newModelTestResult.value = { ok: false, msg: '网络请求失败，请检查后端服务是否运行' };
      }
      newModelCreating.value = false;
    };

    const deleteModel = async (model) => {
      if (!model.is_custom && model.id !== 'custom') {
        return;
      }
      if (!confirm(`确认删除「${model.name}」？`)) return;
      try {
        const res = await fetch(`/api/settings/models/${encodeURIComponent(model.id)}`, {
          method: 'DELETE',
        });
        const data = await res.json();
        if (data.success) {
          toastVisible.value = true;
          setTimeout(() => { toastVisible.value = false; }, 2800);
          await loadConfig();
        } else {
          alert(data.message || '删除失败');
        }
      } catch {}
    };

    const loadConfig = async () => {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();
        modelConfigs.value = (data.models || []).map(m => ({
          ...m,
          supports_vision: m.supports_vision !== undefined ? m.supports_vision : false,
          is_custom: m.is_custom || m.id === 'custom',
        }));
        activeModel.value = data.active_model || '';
        savedActiveModel.value = data.active_model || '';
        const keys = {};
        modelConfigs.value.forEach(m => { keys[m.id] = false; });
        showKey.value = keys;
      } catch {}
    };

    const toggleKeyVisibility = (id) => {
      showKey.value = { ...showKey.value, [id]: !showKey.value[id] };
    };

    const testModel = async (model) => {
      testingModel.value = model.id;
      delete testResults[model.id];
      try {
        // 同时发送 model_id 和当前表单值，后端优先用表单值测试（未保存时也能测）
        const res = await fetch('/api/settings/test-model', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model_id: model.id,
            api_key: model.api_key || '',
            base_url: model.base_url || '',
            model: model.model || '',
          }),
        });
        const data = await res.json();
        testResults[model.id] = { ok: data.success, msg: data.message };
      } catch (e) {
        testResults[model.id] = { ok: false, msg: '网络请求失败，请检查后端服务是否运行' };
      }
      testingModel.value = null;
    };

    const saveSettings = async () => {
      saving.value = true;
      try {
        // 构建保存时的 payload — 保留 api_key 的处理：如果用户未显式修改，后端会根据 api_key_masked 保留原值
        const payload = modelConfigs.value.map(m => ({
          id: m.id,
          name: m.name,
          api_key: m.api_key || '',
          api_key_masked: m.api_key_masked || '',
          base_url: m.base_url,
          model: m.model,
          enabled: m.enabled,
          supports_vision: m.supports_vision,
          is_custom: m.is_custom,
        }));
        await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            models: payload,
            active_model: activeModel.value,
          }),
        });
        savedActiveModel.value = activeModel.value; // 保存成功后，顶部栏才更新
        toastVisible.value = true;
        setTimeout(() => { toastVisible.value = false; }, 2800);
      } catch {}
      saving.value = false;
    };

    // ── 导航 ─────────────────────────────────────────────────
    const setView = (id) => {
      activeView.value = id;
    };

    // ── 初始化 ───────────────────────────────────────────────
    onMounted(async () => {
      await Promise.all([loadFiles(), loadAnalysis(), loadAllCertsData(), loadConfig(), loadRegions(), loadBidding(), loadBiddingStats(), loadPricingProjects()]);
    });

    // ── 区域筛选器变化监听 ─────────────────────────────────
    watch([bidCategoryFilter, bidStatusFilter], () => {
      loadBidding(1);
    });

    return {
      activeView, sidebarCollapsed, apiStatus, searchQuery,
      mainNavItems, toolNavItems,
      files, folders, currentFolder, showNewFolder, newFolderName, creating,
      uploadFiles, createFolder, enterFolder, navigateToFolder,
      deleteFile, deleteFolder, formatSize, formatDate, getFileEmoji,
      // 项目管理
      projects, currentProject, projectFiles, currentProjectFields, currentProjectRisks,
      projectTab, projectSearchKeyword, showNewProject, newProject, extracting,
      editingField, fieldEditValue,
      newProjectFiles, newProjectFilesInput, newProjectUploadDragover,
      loadProjects, openProject, closeProject, deleteProject, cancelNewProject,
      handleNewProjectFileDrop, handleNewProjectFileSelect,
      removeNewProjectFile, formatFileSize, createProject, analyzeProject, analyzingProjects,
      reAnalyzeProject, reAnalyzing,
      uploadProjectFiles, loadProjectFiles, parseProjectFile, parseAllProjectFiles,
      extractProjectInfo, deleteProjectFile, downloadProjectFile,
      startEditField, saveFieldReview, copyFieldValue, confirmRisk, ignoreRisk,
      exportProjectFields, exportProjectRisks,
      fieldReviewStats, riskReviewStats, riskStats,
      getProjectStatusLabel, getParseStatusLabel, getFieldReviewLabel,
      getRiskReviewLabel, getRiskSeverityLabel,
      // 兼容旧的分析记录
      analysisRecords, newAnalysis, analysisOptions, startAnalysis,
      certs, certCategories, certCatFilter, certFilter, filteredCerts, showAddCert, newCert, certFileInput,
      certUploading, certOcrDone, certUploadDragover, certUploadedFile,
      showAddCertCat, newCertCatName, renameCertCatTarget, renameCertCatName,
      loadCerts, loadAllCertsData, resetCertForm, closeAddCert,
      triggerCertFileInput, uploadCertFileAndRecognize,
      handleCertFileChange, handleCertFileDrop,
      addCert, deleteCert, downloadCertFile,
      showEditCert, editCert, openEditCert, closeEditCert, saveEditCert,
      showPreviewCert, currentPreviewCert, previewCert, previewCertUrl,
      addCertCategory, startRenameCat, doRenameCat, deleteCertCat,
      getCertStatusClass, getCertStatusLabel,
      fileCount, analysisCount, certCount, expiringSoon, expiringSoonCount,
      modelConfigs, activeModel, activeModelInfo, savedActiveModel, savedActiveModelInfo, saving, saveSettings, toastVisible, showKey, toggleKeyVisibility,
      testingModel, testResults, testModel,
      showNewModelModal, newModelForm, newModelTesting, newModelTestResult, newModelCreating,
      newModelShowKey,
      openNewModelModal, resetNewModelForm, testNewModel, createModel, deleteModel,
      setView,
      // 区域查询
      regions, biddingList, biddingTotal, biddingPage, biddingPerPage, biddingTotalPages,
      biddingRefreshing, bidSearchKeyword, bidProvinceFilter, bidCityFilter, bidCategoryFilter,
      bidStatusFilter, bidCategories, bidFilterCities, bidDetailVisible, bidDetail,
      biddingStats, searchBidding, onBidProvinceChange, goBidPage, refreshBidding,
      showBidDetail, isBidExpiringSoon, getBidStatusClass,
      // 报价调整
      pricingProjects, currentPricingId, currentPricing, pricingForm, pricingStrategies,
      pricingCategories, showNewPricing, newPricingName, newPricingDesc,
      showAddPricingItem, newItem,
      startNewPricing, createPricingProject, selectPricingProject, deletePricingProject,
      savePricingMeta, savePricingMetaDebounced, openAddItem, addPricingItem,
      saveItem, deleteItem, formatPricingNum,
    };
  },
}).mount('#app');
