/**
 * 应用主程序
 * 初始化应用，管理全局状态，处理事件
 */

/**
 * 防抖工具：连续触发时只在最后一次停止后 delay ms 执行一次
 * @param {Function} fn
 * @param {number} delay - 毫秒
 */
function debounce(fn, delay) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

class App {
    constructor() {
        this.isReady = false;
        this.currentPath = null;
        this.albumTree = null;
        this.albumStats = null;
        this.init();
    }

    /**
     * 应用初始化
     */
    async init() {
        try {
            console.log('🚀 应用初始化中...');
            
            // 0. 等待 PyWebView API 准备就绪（关键步骤）
            if (window.pywebviewReady) {
                console.log('⏳ 等待 PyWebView API 准备就绪...');
                try {
                    await window.pywebviewReady.wait(5000);
                    console.log('✅ PyWebView API 已准备就绪');
                } catch (err) {
                    console.warn('⚠️ PyWebView API 准备超时:', err.message);
                    // 继续执行，有些功能可能不可用
                }
            }
            
            // 1. 等待 DOM 准备就绪
            await this.waitForDOM();
            console.log('[init] DOM 已准备就绪');
            
            // 2. 检查是否需要初始化（相册路径是否已设置）
            console.log('[init] 开始检查初始化状态...');
            const needsInitialization = await this.checkInitializationStatus();
            console.log('[init] 初始化状态检查完成，需要初始化:', needsInitialization);
            
            // 检查初始化屏幕和主界面的状态
            const initScreen = document.getElementById('initialization-screen');
            const appContainer = document.querySelector('.app-container');
            console.log('[init] 初始化屏幕元素:', initScreen);
            console.log('[init] 主界面容器元素:', appContainer);
            
            if (needsInitialization) {
                console.log('📋 首次启动，显示初始化屏幕');
                // 使用全局 initScreen 实例
                if (window.initScreen) {
                    console.log('✅ 使用全局 initScreen 实例');
                    window.initScreen.init();
                    window.initScreen.show();
                } else {
                    console.warn('⚠️ 全局 initScreen 实例不存在，创建新实例');
                    const initScreen = new InitializationScreen();
                    initScreen.init();
                    initScreen.show();
                }
                // 确保主界面隐藏
                if (appContainer) {
                    appContainer.classList.remove('shown');
                    console.log('[init] 主界面已隐藏');
                }
                return;  // 等待用户选择相册路径
            } else {
                console.log('✅ 相册已初始化，显示主界面');
                // 初始化屏幕默认已隐藏（CSS display:none），无需操作
                // 确保主界面显示
                if (appContainer) {
                    appContainer.classList.add('shown');
                    console.log('[init] 主界面已显示');
                }
            }
            
            // 3. 绑定事件
            console.log('[init] 开始绑定事件...');
            this.bindEvents();
            console.log('[init] 事件绑定完成');
            
            // 4. 初始化 UI
            console.log('[init] 开始初始化 UI...');
            this.initUI();
            console.log('[init] UI 初始化完成');
            
            // 5. 加载数据
            console.log('[init] 开始加载初始数据...');
            await this.loadInitialData();
            console.log('[init] 数据加载完成');
            
            this.isReady = true;
            console.log('✅ 应用初始化完成');
            
        } catch (error) {
            console.error('❌ 应用初始化失败:', error);
            console.error('错误堆栈:', error.stack);
            this.showError('应用初始化失败: ' + error.message);
        }
    }

    /**
     * 检查是否需要初始化
     * 返回 true = 需要初始化（显示初始化屏幕）
     * 返回 false = 已初始化（显示主界面）
     */
    async checkInitializationStatus() {
        console.log('=== 开始检查初始化状态 ===');
        
        // 简化逻辑，直接测试获取相册路径API
        try {
            console.log('[checkInitializationStatus] 直接检查相册路径设置...');
            
            // 使用相对路径（PyWebView 环境中更可靠）
            const albumPathUrl = '/api/settings/album-path';
            console.log('[checkInitializationStatus] 直接调用API URL:', albumPathUrl);
            
            const response = await fetch(albumPathUrl);
            console.log('[checkInitializationStatus] API响应状态:', response.status);
            
            if (response.ok) {
                const result = await response.json();
                console.log('[checkInitializationStatus] API响应内容:', result);
                console.log('[checkInitializationStatus] 相册路径值:', result.album_path);
                
                if (result.album_path && result.album_path !== '') {
                    console.log('[checkInitializationStatus] ✅ 相册已初始化，可以显示主界面');
                    return false; // 不需要初始化
                } else {
                    console.log('[checkInitializationStatus] ⚠️ 相册路径未设置，需要初始化');
                    return true; // 需要初始化
                }
            } else {
                console.error('[checkInitializationStatus] ❌ API请求失败，状态码:', response.status);
                // API请求失败，尝试使用绝对URL
                return await this.checkInitializationStatusFallback();
            }
        } catch (error) {
            console.error('[checkInitializationStatus] ❌ 检查初始化状态异常:', error);
            console.error('[checkInitializationStatus] 错误堆栈:', error.stack);
            // 发生异常，尝试使用绝对URL
            return await this.checkInitializationStatusFallback();
        }
    }

    /**
     * 备用检查方法（使用绝对URL）
     */
    async checkInitializationStatusFallback() {
        try {
            console.log('[checkInitializationStatusFallback] 尝试使用绝对URL...');
            const albumPathUrl = 'http://127.0.0.1:5000/api/settings/album-path';

            const response = await fetch(albumPathUrl);

            if (response.ok) {
                const result = await response.json();
                console.log('[checkInitializationStatusFallback] API响应内容:', result);

                if (result.album_path && result.album_path !== '') {
                    console.log('[checkInitializationStatusFallback] ✅ 相册已初始化');
                    return false;
                } else {
                    console.log('[checkInitializationStatusFallback] ⚠️ 相册路径未设置');
                    return true;
                }
            }
        } catch (error) {
            console.error('[checkInitializationStatusFallback] ❌ 备用检查也失败:', error);
        }

        // Both methods failed - show error to user
        console.error('[checkInitializationStatusFallback] API 完全不可用');
        if (window.app && typeof window.app.showError === 'function') {
            window.app.showError('无法连接到服务器，请检查服务器是否正在运行');
        }

        // Return false to show main interface (better UX than blank screen)
        return false;
    }

    /**
     * 等待 DOM 准备就绪
     */
    waitForDOM() {
        return new Promise(resolve => {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', resolve);
            } else {
                resolve();
            }
        });
    }

    /**
     * 绑定事件处理
     */
    bindEvents() {
        console.log('[bindEvents] 开始绑定事件...');
        
        // 顶部按钮
        const btnSettings = document.getElementById('btn-settings');
        if (btnSettings) {
            btnSettings.addEventListener('click', () => {
                console.log('[Event] 点击设置按钮');
                this.showSettingsDialog();
            });
            // 添加键盘支持
            btnSettings.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.showSettingsDialog();
                }
            });
            console.log('[bindEvents] btn-settings 已绑定');
        } else {
            console.error('[bindEvents] 找不到 btn-settings 元素');
        }
        
        const btnHelp = document.getElementById('btn-help');
        if (btnHelp) {
            btnHelp.addEventListener('click', () => {
                console.log('[Event] 点击帮助按钮');
                this.showHelp();
            });
            // 添加键盘支持
            btnHelp.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.showHelp();
                }
            });
            console.log('[bindEvents] btn-help 已绑定');
        } else {
            console.error('[bindEvents] 找不到 btn-help 元素');
        }
        
        // 侧边栏按钮
        const btnRefresh = document.getElementById('btn-refresh');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => {
                console.log('[Event] 点击刷新按钮');
                this.refresh();
            });
            // 添加键盘支持
            btnRefresh.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.refresh();
                }
            });
            console.log('[bindEvents] btn-refresh 已绑定');
        } else {
            console.error('[bindEvents] 找不到 btn-refresh 元素');
        }
        
        const btnImport = document.getElementById('btn-import');
        if (btnImport) {
            btnImport.addEventListener('click', () => {
                console.log('[Event] 点击导入按钮');
                this.showImportDialog();
            });
            // 添加键盘支持
            btnImport.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.showImportDialog();
                }
            });
            console.log('[bindEvents] btn-import 已绑定');
        } else {
            console.error('[bindEvents] 找不到 btn-import 元素');
        }

        // Empty State 欢迎页"导入照片"按钮
        const btnImportWelcome = document.getElementById('btn-import-welcome');
        if (btnImportWelcome) {
            btnImportWelcome.addEventListener('click', () => {
                this.showImportDialog();
            });
        }
        
        // 窗口大小变化事件（防抖 200ms，避免拖拽时频繁重排）
        window.addEventListener('resize', debounce(() => {
            this.handleWindowResize();
        }, 200));
        
        // 初始化响应式布局
        this.handleWindowResize();

        // 帮助对话框关闭按钮
        ['close-help-dialog', 'close-help-btn'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.addEventListener('click', () => {
                const dialog = document.getElementById('help-dialog');
                if (dialog) dialog.style.display = 'none';
            });
        });
        // 点击帮助对话框遮罩关闭
        const helpDialog = document.getElementById('help-dialog');
        if (helpDialog) {
            helpDialog.addEventListener('click', (e) => {
                if (e.target === helpDialog) helpDialog.style.display = 'none';
            });
        }
        
        console.log('[bindEvents] 事件绑定完成');
    }

    /**
     * 初始化 UI
     */
    initUI() {
        console.log('[initUI] 开始 UI 初始化...');
        
        try {
            // 初始化各个模块
            // AlbumBrowser: 对象字面量
            if (window.AlbumBrowser && typeof window.AlbumBrowser.init === 'function') {
                console.log('[initUI] 初始化 AlbumBrowser...');
                window.AlbumBrowser.init();
            } else {
                console.warn('[initUI] AlbumBrowser 不可用');
            }
            
            // ImportDialog: 全局实例（小写 importDialog）
            if (window.importDialog) {
                console.log('[initUI] importDialog 实例已初始化');
            } else {
                console.warn('[initUI] importDialog 实例不可用');
            }
            
            // SettingsDialog: 对象字面量
            if (window.SettingsDialog && typeof window.SettingsDialog.init === 'function') {
                console.log('[initUI] 初始化 SettingsDialog...');
                window.SettingsDialog.init();
            } else {
                console.warn('[initUI] SettingsDialog 不可用');
            }
            
            // 初始化主题设置
            this.initTheme();

            // 初始化语言（检测系统语言或加载已保存偏好）
            if (window.I18n) {
                I18n.initLanguage().catch(e => console.warn('[i18n] initLanguage 失败:', e));
            }
            
            console.log('[initUI] UI 初始化完成');
        } catch (error) {
            console.error('[initUI] UI 初始化出错:', error);
            throw error;  // 让错误传播到上层
        }
    }

    /**
     * 加载初始数据
     */
    async loadInitialData() {
        console.log('[loadInitialData] 开始加载初始数据...');
        try {
            // 测试 API 连接
            console.log('[loadInitialData] 1️⃣ 测试 API 连接...');
            const health = await API.health();
            console.log('[loadInitialData] ✅ API 服务器连接正常:', health);
            
            // 加载统计信息
            console.log('[loadInitialData] 2️⃣ 加载相册统计信息...');
            await this.loadAlbumStats();
            console.log('[loadInitialData] ✅ 统计信息加载完成');
            
            // 目录树由 AlbumBrowser.init() 负责加载和渲染，此处不重复调用
            console.log('[loadInitialData] ✅ 初始数据加载完成');
        } catch (error) {
            console.error('[loadInitialData] ❌ 加载初始数据失败:', error);
            console.error('[loadInitialData] 错误详情:', error.stack);
            throw error;
        }
    }

    /**
     * 加载相册统计信息
     */
    async loadAlbumStats() {
        try {
            this.albumStats = await API.getAlbumStats();
            this.updateStatsUI();
        } catch (error) {
            console.error('加载统计信息失败:', error);
            this.showWarning('无法加载统计信息');
        }
    }

    /**
     * 初始化主题设置
     */
    initTheme() {
        // 获取保存的主题设置，默认为system
        const savedTheme = localStorage.getItem('theme') || 'system';
        
        // 应用主题
        this.applyTheme(savedTheme);
        
        // 更新选择框
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.value = savedTheme;
            
            // 添加事件监听器
            themeSelect.addEventListener('change', (e) => {
                this.applyTheme(e.target.value);
            });
        }
    }
    
    /**
     * 应用主题设置
     * 支持三种主题：light（亮色）、dark（暗色）、deep-blue（深蓝）
     * 以及 system（跟随系统）
     */
    applyTheme(theme) {
        // 保存主题设置
        localStorage.setItem('theme', theme);
        
        // 处理系统偏好
        let actualTheme = theme;
        if (theme === 'system') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            actualTheme = prefersDark ? 'dark' : 'light';
        }
        
        // 应用data-theme属性
        document.documentElement.setAttribute('data-theme', actualTheme);
        
        // 更新选择框
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.value = theme;
        }
    }

    /**
     * 更新统计 UI
     * 文件总数使用目录树根节点的 count（与目录树显示一致）
     */
    updateStatsUI() {
        if (!this.albumStats) return;
        
        // BUG-025：所有 getElementById 结果都加 null 检查
        const totalFilesEl = document.getElementById('stat-total-files');
        if (totalFilesEl) {
            // 优先使用目录树根节点的 count（与目录树显示一致）
            const treeTotal = this.albumTree?.count;
            totalFilesEl.textContent = treeTotal != null ? String(treeTotal) : (this.albumStats.total_files || '0');
        }

        // 视频文件数
        const videoCountEl = document.getElementById('stat-video-count');
        if (videoCountEl) {
            videoCountEl.textContent = this.albumStats.video_count != null
                ? String(this.albumStats.video_count)
                : '0';
        }
        
        const totalSizeEl = document.getElementById('stat-total-size');
        if (totalSizeEl) {
            totalSizeEl.textContent = APIUtils.formatFileSize(this.albumStats.total_size || 0);
        }

        // 显示最后导入时间
        const lastImport = this.albumStats.last_import;
        const lastImportEl = document.getElementById('stat-last-import');
        if (lastImport) {
            try {
                const importDate = new Date(lastImport);
                const formattedDate = importDate.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
                if (lastImportEl) lastImportEl.textContent = formattedDate;
            } catch (e) {
                console.warn('日期格式化失败:', e);
                if (lastImportEl) lastImportEl.textContent = lastImport;
            }
        } else {
            if (lastImportEl) lastImportEl.textContent = '暂无数据';
        }
    }

    /**
     * 加载指定路径的照片
     */
    async loadPhotosForPath(path) {
        try {
            this.currentPath = path;
            const container = document.getElementById('photos-container');
            
            // 显示加载状态
            container.innerHTML = '<div class="loading-state"><div class="spinner-ring"></div><p class="loading-text">加载中...</p></div>';
            
            // 获取照片列表
            const result = await API.getPhotos(path);
            
            // 更新内容标题
            const pathName = path.split('\\').pop();
            document.getElementById('content-title').textContent = 
                pathName || '相册';
            
            // 渲染照片网格
            this.renderPhotos(result.photos);
            
        } catch (error) {
            console.error('加载照片失败:', error);
            document.getElementById('photos-container').innerHTML = 
                `<div class="error-message">加载照片失败: ${error.message}</div>`;
        }
    }

    /**
     * 渲染照片网格
     */
    renderPhotos(photos) {
        const container = document.getElementById('photos-container');
        
        if (!photos || photos.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><p class="empty-state-text">该目录中没有照片</p></div>';
            return;
        }
        
        const grid = document.createElement('div');
        grid.className = 'photo-grid';
        
        for (const photo of photos) {
            const card = this.createPhotoCard(photo);
            grid.appendChild(card);
        }
        
        container.innerHTML = '';
        container.appendChild(grid);
    }

    /**
     * 创建照片卡片
     */
    createPhotoCard(photo) {
        const card = document.createElement('div');
        card.className = 'photo-card';
        
        const typeIcon = photo.type === 'video' ? '🎬' : '🖼️';
        
        // 创建照片卡片内容（photo.name 经 _escapeHtml 转义，防 XSS）
        const safeName = this._escapeHtml(photo.name || '');
        let thumbnailHtml = '';
        if (photo.type === 'photo' && photo.thumbnail_url) {
            // 对于照片，使用后端提供的缩略图 API
            thumbnailHtml = `
                <img src="${photo.thumbnail_url}" alt="${safeName}" class="thumbnail-img" onerror="this.parentElement.innerHTML = '🖼️'">
            `;
        } else {
            // 对于视频或没有缩略图的情况，显示图标
            thumbnailHtml = `
                <div class="photo-placeholder">
                    ${typeIcon}
                    <div class="photo-file-name">${safeName}</div>
                </div>
            `;
        }
        
        card.innerHTML = `
            <div class="photo-thumbnail">
                ${thumbnailHtml}
            </div>
            <div class="photo-info">
                <div class="photo-name" title="${safeName}">${safeName}</div>
                <div class="photo-size">💾 ${APIUtils.formatFileSize(photo.size)}</div>
            </div>
        `;
        
        // 双击事件处理
        let clickTimeout;
        card.addEventListener('click', (e) => {
            e.preventDefault();
            
            if (e.detail === 1) {
                // 单击事件 - 延迟执行，防止双击时触发
                clearTimeout(clickTimeout);
                clickTimeout = setTimeout(() => {
                    console.log('单击照片:', photo);
                    this.previewPhoto(photo);
                }, 200);
            } else if (e.detail === 2) {
                // 双击事件 - 清除单击的超时
                clearTimeout(clickTimeout);
                console.log('双击照片:', photo);
                this.openPhoto(photo);
            }
        });
        
        return card;
    }
    
    /**
     * 处理窗口大小变化
     */
    handleWindowResize() {
        const width = window.innerWidth;
        const appContainer = document.querySelector('.app-container');

        // BUG-024：appContainer 在初始化屏幕阶段可能不存在，需做 null 检查
        if (!appContainer) return;
        
        // 根据屏幕宽度应用不同的布局策略
        if (width < 768) {
            // 移动端布局
            appContainer.classList.add('mobile-layout');
        } else {
            // 桌面端布局
            appContainer.classList.remove('mobile-layout');
        }
        
        // 刷新当前照片网格的渲染，确保响应式布局正确应用
        // 委托给 AlbumBrowser 以保留分页/多选状态
        if (window.AlbumBrowser && window.AlbumBrowser.currentPath) {
            window.AlbumBrowser.renderPhotosWithPagination();
        }
    }

    /**
     * 打开照片文件
     */
    openPhoto(photo) {
        try {
            // 使用 PyWebView API 打开文件
            if (window.pywebview && window.pywebview.api && window.pywebview.api.open_file) {
                console.log('使用 PyWebView API 打开文件:', photo.path);
                window.pywebview.api.open_file(photo.path)
                    .then(result => {
                        console.log('打开文件结果:', result);
                        if (!result.success) {
                            console.error('打开文件失败:', result.error);
                            alert(`无法打开文件: ${result.error}\n\n文件路径: ${photo.path}`);
                        }
                    })
                    .catch(error => {
                        console.error('调用 API 失败:', error);
                        // 降级方案：显示文件路径
                        alert(`照片路径: ${photo.path}\n\n请手动打开此文件。`);
                    });
            } else {
                // 降级方案：显示文件路径
                alert(`照片路径: ${photo.path}\n\n请手动打开此文件。`);
            }
        } catch (error) {
            console.error('打开文件失败:', error);
            alert(`无法打开文件: ${error.message}\n\n文件路径: ${photo.path}`);
        }
    }
    
    /**
     * 预览照片
     * @param {object} photo - 照片对象
     * @param {Array}  [list] - 当前照片列表（用于翻页），可选
     */
    previewPhoto(photo, list) {
        console.log('[previewPhoto] 预览照片:', photo);
        console.log('[previewPhoto] photo.path:', photo.path);
        console.log('[previewPhoto] photo.name:', photo.name);
        console.log('[previewPhoto] photo.type:', photo.type);
        console.log('[previewPhoto] photo.preview_url:', photo.preview_url);
        console.log('[previewPhoto] photo.thumbnail_url:', photo.thumbnail_url);
        console.log('[previewPhoto] list length:', list ? list.length : 0);

        if (!photo || !photo.path) {
            console.error('[previewPhoto] 无效的 photo 对象:', photo);
            return;
        }

        // 保存预览列表和当前索引（用于翻页）
        if (list && list.length > 0) {
            this._previewList = list;
            this._previewIndex = list.findIndex(p => p.path === photo.path);
            if (this._previewIndex < 0) this._previewIndex = 0;
        } else if (!this._previewList) {
            this._previewList = [photo];
            this._previewIndex = 0;
        }

        console.log('[previewPhoto] 调用 _showPreviewItem，索引:', this._previewIndex);
        this._showPreviewItem(this._previewIndex);
    }

    /**
     * 显示预览列表中指定索引的照片/视频
     */
    _showPreviewItem(index) {
        console.log('[_showPreviewItem] 开始显示预览，索引:', index);

        const list = this._previewList || [];
        if (!list.length) {
            console.error('[_showPreviewItem] 预览列表为空');
            return;
        }

        // 边界保护
        index = Math.max(0, Math.min(index, list.length - 1));
        this._previewIndex = index;
        const photo = list[index];
        this.currentPreviewPhoto = photo;

        console.log('[_showPreviewItem] 当前照片:', photo);
        console.log('[_showPreviewItem] photo.type:', photo.type);

        // 停止上一个视频（翻页时避免后台播放）
        const videoEl = document.getElementById('preview-video');
        const unsupportedEl = document.getElementById('preview-video-unsupported');
        if (videoEl) {
            videoEl.pause();
            videoEl.removeAttribute('controls');
            videoEl.style.display = 'none';
            videoEl.style.visibility = 'hidden';
            // 先清除事件处理函数，避免清空src时触发错误
            videoEl.onerror = null;
            videoEl.onloadedmetadata = null;
            // 然后清空src
            videoEl.src = '';
        }
        // 隐藏不支持提示
        if (unsupportedEl) unsupportedEl.style.display = 'none';

        // 显示预览模态框
        const modal = document.getElementById('photo-preview-modal');
        if (modal) modal.style.display = 'flex';

        // 更新索引标签
        const badge = document.getElementById('preview-index-badge');
        if (badge) badge.textContent = list.length > 1 ? `${index + 1} / ${list.length}` : '';

        // 更新翻页按钮
        const prevBtn = document.getElementById('preview-prev-btn');
        const nextBtn = document.getElementById('preview-next-btn');
        if (prevBtn) prevBtn.disabled = (index === 0);
        if (nextBtn) nextBtn.disabled = (index === list.length - 1);

        // 隐藏翻页按钮（单张时）
        if (prevBtn) prevBtn.style.visibility = list.length > 1 ? '' : 'hidden';
        if (nextBtn) nextBtn.style.visibility = list.length > 1 ? '' : 'hidden';

        // 更新文字信息
        const previewTitle = document.getElementById('preview-title');
        const previewName  = document.getElementById('preview-name');
        const previewSize  = document.getElementById('preview-size');
        const previewPath  = document.getElementById('preview-path');
        if (previewTitle) previewTitle.textContent = `${photo.type === 'video' ? '视频' : '照片'}预览: ${photo.name}`;
        if (previewName)  previewName.textContent  = `文件名: ${photo.name}`;
        if (previewSize)  previewSize.textContent  = `文件大小: ${APIUtils.formatFileSize(photo.size)}`;
        if (previewPath)  previewPath.textContent  = `文件路径: ${photo.path}`;

        // 隐藏视频专属信息（切换时重置）
        const durationEl   = document.getElementById('preview-video-duration');
        const resolutionEl = document.getElementById('preview-video-resolution');
        if (durationEl)   { durationEl.style.display = 'none'; durationEl.textContent = ''; }
        if (resolutionEl) { resolutionEl.style.display = 'none'; resolutionEl.textContent = ''; }

        const previewImage = document.getElementById('preview-image');
        const previewVideo = document.getElementById('preview-video');
        const loadingEl    = document.getElementById('preview-loading');

        if (photo.type === 'video') {
            // ── 视频模式 ──
            if (previewImage) previewImage.style.display = 'none';
            if (unsupportedEl) unsupportedEl.style.display = 'none';

            if (previewVideo) {
                // 先停止之前的视频（如果有）
                previewVideo.pause();
                previewVideo.removeAttribute('controls');
                previewVideo.style.display = 'none';
                previewVideo.style.visibility = 'hidden';
                previewVideo.src = '';

                // 恢复视频显示
                previewVideo.setAttribute('controls', '');
                previewVideo.style.display = 'block';
                previewVideo.style.visibility = 'visible';
                // 先显示 loading，等浏览器加载到足够元数据后再隐藏
                if (loadingEl) loadingEl.classList.add('visible');
                previewVideo.src = photo.url || '';
                // 加载失败时显示降级提示
                previewVideo.onerror = () => {
                    previewVideo.style.display = 'none';
                    if (unsupportedEl) unsupportedEl.style.display = 'flex';
                    if (loadingEl) loadingEl.classList.remove('visible');
                };
                previewVideo.onloadedmetadata = () => {
                    if (loadingEl) loadingEl.classList.remove('visible');
                };
            }

            // 异步加载视频 metadata（时长、分辨率）
            if (photo.url || photo.path) {
                const metaUrl = `/api/video/metadata?path=${encodeURIComponent(photo.path)}`;
                fetch(metaUrl)
                    .then(r => r.json())
                    .then(meta => {
                        // 确保仍在同一个视频
                        if (!this.currentPreviewPhoto || this.currentPreviewPhoto.path !== photo.path) return;
                        if (!meta.available) return;
                        if (durationEl && meta.duration_formatted) {
                            durationEl.textContent = `时长: ${meta.duration_formatted}`;
                            durationEl.style.display = '';
                        }
                        if (resolutionEl && meta.resolution) {
                            resolutionEl.textContent = `分辨率: ${meta.resolution}`;
                            resolutionEl.style.display = '';
                        }
                    })
                    .catch(() => { /* FFmpeg 不可用时静默失败 */ });
            }

        } else {
            // ── 图片模式 ──
            // 先停止视频播放并清理
            if (previewVideo) {
                previewVideo.pause();
                previewVideo.removeAttribute('controls');
                previewVideo.style.display = 'none';
                previewVideo.style.visibility = 'hidden';
                previewVideo.src = '';
                // 不调用 load()，避免触发视频元素的渲染
            }
            if (unsupportedEl) unsupportedEl.style.display = 'none';

            if (previewImage) {
                previewImage.style.display = 'block';

                const previewUrl = photo.preview_url || photo.url || photo.thumbnail_url || '';

                // 清除之前的事件处理函数
                previewImage.onerror = null;
                previewImage.onload = null;

                if (photo.thumbnail_url || previewUrl) {
                    // 先用缩略图快速占位
                    previewImage.src = photo.thumbnail_url || '';
                    previewImage.alt = photo.name;

                    // 设置图片加载错误处理
                    previewImage.onerror = () => {
                        console.error('[预览] 缩略图加载失败:', photo.thumbnail_url);
                        // 尝试加载 preview_url
                        if (previewUrl && previewUrl !== photo.thumbnail_url) {
                            previewImage.onerror = () => {
                                console.error('[预览] 预览图加载失败:', previewUrl);
                                if (loadingEl) loadingEl.classList.remove('visible');
                                // 显示错误提示
                                previewImage.alt = `加载失败: ${photo.name}`;
                            };
                            previewImage.src = previewUrl;
                        } else {
                            if (loadingEl) loadingEl.classList.remove('visible');
                        }
                    };

                    // 再加载 preview_url（已是可被浏览器渲染的格式）
                    // 若 previewUrl 与缩略图 URL 相同，无需二次加载
                    if (previewUrl && previewUrl !== photo.thumbnail_url) {
                        if (loadingEl) loadingEl.classList.add('visible');
                        const origImg = new Image();
                        origImg.onload = () => {
                            // 确认仍是同一张
                            if (this.currentPreviewPhoto && this.currentPreviewPhoto.path === photo.path) {
                                previewImage.src = origImg.src;
                                if (loadingEl) loadingEl.classList.remove('visible');
                            }
                        };
                        origImg.onerror = () => {
                            // preview_url 失败（如 HEIC 转换出错），保持缩略图
                            console.error('[预览] 高清预览图加载失败:', previewUrl);
                            if (loadingEl) loadingEl.classList.remove('visible');
                        };
                        origImg.src = previewUrl;
                    }
                } else {
                    // 没有可用的URL
                    if (loadingEl) loadingEl.classList.remove('visible');
                    previewImage.alt = `无法加载: ${photo.name}`;
                }
            }
        }

        // 绑定模态框事件（只绑一次）
        if (!this._previewEventsBound) {
            this._bindPreviewModalEvents();
        }

        // 翻页时重置缩放
        this._resetPreviewZoom();

        // 异步加载 EXIF（非阻塞）
        this._loadExifInfo(photo).catch(() => {});
    }

    /**
     * 绑定预览模态框事件（只执行一次）
     */
    _bindPreviewModalEvents() {
        this._previewEventsBound = true;

        const bind = (id, fn) => {
            const el = document.getElementById(id);
            if (el) el.onclick = fn;
        };

        bind('close-preview-btn',   () => this.closePreviewModal());
        bind('close-preview-modal', () => this.closePreviewModal());
        bind('open-file-btn',       () => { if (this.currentPreviewPhoto) this.openPhoto(this.currentPreviewPhoto); });
        bind('preview-prev-btn',    () => { if (this._previewIndex > 0) this._showPreviewItem(this._previewIndex - 1); });
        bind('preview-next-btn',    () => {
            if (this._previewList && this._previewIndex < this._previewList.length - 1)
                this._showPreviewItem(this._previewIndex + 1);
        });

        // 点击遮罩关闭
        const modal = document.getElementById('photo-preview-modal');
        if (modal) {
            modal.onclick = (e) => { if (e.target === modal) this.closePreviewModal(); };
        }

        // 初始化预览图片缩放/拖拽（只绑定一次）
        this._initPreviewZoom();

        // 绑定 EXIF 面板折叠按钮
        const exifToggle = document.getElementById('exif-panel-toggle');
        if (exifToggle) {
            exifToggle.onclick = () => {
                const panel = document.getElementById('exif-panel');
                const body  = document.getElementById('exif-panel-body');
                if (!panel || !body) return;
                const expanded = panel.classList.toggle('expanded');
                body.style.display = expanded ? 'block' : 'none';
                exifToggle.setAttribute('aria-expanded', String(expanded));
            };
        }
    }

    /**
     * 绑定预览模态框事件（兼容旧调用，实际转发到 _bindPreviewModalEvents）
     */
    bindPreviewModalEvents() {
        this._bindPreviewModalEvents();
    }
    
    /**
     * 关闭预览模态框
     */
    closePreviewModal() {
        const modal = document.getElementById('photo-preview-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        // 停止视频播放，释放网络资源
        const videoEl = document.getElementById('preview-video');
        if (videoEl) {
            videoEl.pause();
            videoEl.src = '';
            videoEl.load();  // 强制重置视频元素
        }
        this.currentPreviewPhoto = null;
        this._previewList  = null;
        this._previewIndex = 0;
        // 重置缩放状态
        this._resetPreviewZoom();
        // 隐藏 EXIF 面板
        const exifPanel = document.getElementById('exif-panel');
        if (exifPanel) exifPanel.style.display = 'none';
    }

    /* ──────────────────────────────────────────────────────────
     * 预览图片缩放 / 拖拽（v0.1）
     * ────────────────────────────────────────────────────────── */

    /**
     * 初始化缩放/拖拽事件监听（只绑定一次，挂在 wrapper 上）
     */
    _initPreviewZoom() {
        const wrapper = document.getElementById('preview-img-wrapper');
        const img     = document.getElementById('preview-image');
        if (!wrapper || !img || this._zoomInited) return;
        this._zoomInited = true;

        // 缩放状态
        this._zoom = { scale: 1, tx: 0, ty: 0, dragging: false, startX: 0, startY: 0, startTx: 0, startTy: 0 };

        const applyTransform = () => {
            const z = this._zoom;
            img.style.transform = `translate(${z.tx}px, ${z.ty}px) scale(${z.scale})`;
            // 更新光标
            img.classList.remove('zoomed', 'zoomable');
            img.classList.add(z.scale > 1 ? 'zoomed' : 'zoomable');
            // 缩放徽标
            let badge = wrapper.querySelector('.zoom-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'zoom-badge';
                wrapper.appendChild(badge);
            }
            badge.textContent = `${Math.round(z.scale * 100)}%`;
            badge.classList.toggle('visible', z.scale !== 1);
        };

        const clampTranslate = () => {
            const z    = this._zoom;
            const wW   = wrapper.clientWidth;
            const wH   = wrapper.clientHeight;
            const iW   = img.naturalWidth  || img.clientWidth;
            const iH   = img.naturalHeight || img.clientHeight;
            // 显示尺寸（受 CSS max-width/max-height 限制）
            const dispW = Math.min(iW, wW) * z.scale;
            const dispH = Math.min(iH, wH) * z.scale;
            const maxTx = Math.max(0, (dispW - wW) / 2);
            const maxTy = Math.max(0, (dispH - wH) / 2);
            z.tx = Math.max(-maxTx, Math.min(maxTx, z.tx));
            z.ty = Math.max(-maxTy, Math.min(maxTy, z.ty));
        };

        // 滚轮缩放
        wrapper.addEventListener('wheel', (e) => {
            const imgVisible = img.style.display !== 'none' && img.src;
            if (!imgVisible) return;
            e.preventDefault();
            const z     = this._zoom;
            const delta = e.deltaY > 0 ? -0.15 : 0.15;
            const newScale = Math.min(4, Math.max(0.25, z.scale + delta));
            // 以鼠标位置为缩放原点
            const rect  = wrapper.getBoundingClientRect();
            const cx    = e.clientX - rect.left - wrapper.clientWidth  / 2;
            const cy    = e.clientY - rect.top  - wrapper.clientHeight / 2;
            z.tx = cx + (z.tx - cx) * (newScale / z.scale);
            z.ty = cy + (z.ty - cy) * (newScale / z.scale);
            z.scale = newScale;
            clampTranslate();
            applyTransform();
        }, { passive: false });

        // 双击重置
        img.addEventListener('dblclick', () => {
            const z = this._zoom;
            z.scale = 1; z.tx = 0; z.ty = 0;
            applyTransform();
        });

        // 拖拽平移
        img.addEventListener('mousedown', (e) => {
            if (this._zoom.scale <= 1) return;
            e.preventDefault();
            const z = this._zoom;
            z.dragging = true;
            z.startX   = e.clientX;
            z.startY   = e.clientY;
            z.startTx  = z.tx;
            z.startTy  = z.ty;
            img.classList.add('dragging');
        });

        document.addEventListener('mousemove', (e) => {
            const z = this._zoom;
            if (!z.dragging) return;
            z.tx = z.startTx + (e.clientX - z.startX);
            z.ty = z.startTy + (e.clientY - z.startY);
            clampTranslate();
            applyTransform();
        });

        document.addEventListener('mouseup', () => {
            if (!this._zoom.dragging) return;
            this._zoom.dragging = false;
            img.classList.remove('dragging');
        });
    }

    /**
     * 重置缩放状态（翻页或关闭时调用）
     */
    _resetPreviewZoom() {
        if (!this._zoom) return;
        this._zoom.scale = 1;
        this._zoom.tx    = 0;
        this._zoom.ty    = 0;
        const img = document.getElementById('preview-image');
        if (img) {
            img.style.transform = '';
            img.classList.remove('zoomed', 'dragging');
            img.classList.add('zoomable');
        }
        const wrapper = document.getElementById('preview-img-wrapper');
        if (wrapper) {
            const badge = wrapper.querySelector('.zoom-badge');
            if (badge) badge.classList.remove('visible');
        }
    }

    /* ──────────────────────────────────────────────────────────
     * EXIF 详情异步加载（v0.1）
     * ────────────────────────────────────────────────────────── */

    /**
     * 异步加载并展示 EXIF 面板（仅图片调用，视频跳过）
     */
    async _loadExifInfo(photo) {
        const panel = document.getElementById('exif-panel');
        const grid  = document.getElementById('exif-grid');
        if (!panel || !grid) return;

        // 隐藏并重置
        panel.style.display = 'none';
        panel.classList.remove('expanded');
        const body = document.getElementById('exif-panel-body');
        if (body) body.style.display = 'none';
        const toggle = document.getElementById('exif-panel-toggle');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');

        if (photo.type === 'video') return;

        try {
            const filePath = photo.file_path || photo.path || '';
            if (!filePath) return;
            const res = await fetch(`/api/album/exif?path=${encodeURIComponent(filePath)}`);
            if (!res.ok) return;
            const exif = await res.json();
            if (!exif || Object.keys(exif).length === 0) return;

            // 构建显示字段列表
            const T = (key) => window.I18n ? I18n.t(key) : key;
            const fields = [
                { key: 'make',              label: T('exif.camera') },
                { key: 'model',             label: T('exif.lens'),    wide: true },
                { key: 'datetime_original', label: T('exif.datetime'), wide: true },
                { key: 'focal_length',      label: T('exif.focal') },
                { key: 'focal_length_35mm', label: window.I18n ? (I18n.getLanguage()==='en' ? '35mm Equiv.' : '等效焦距') : '等效焦距' },
                { key: 'f_number',          label: T('exif.aperture') },
                { key: 'exposure_time',     label: T('exif.shutter') },
                { key: 'iso',               label: T('exif.iso') },
                { key: 'exposure_bias',     label: window.I18n ? (I18n.getLanguage()==='en' ? 'Exp. Comp.' : '曝光补偿') : '曝光补偿' },
                { key: 'white_balance',     label: window.I18n ? (I18n.getLanguage()==='en' ? 'White Balance' : '白平衡') : '白平衡' },
                { key: 'flash',             label: window.I18n ? (I18n.getLanguage()==='en' ? 'Flash' : '闪光灯') : '闪光灯' },
                { key: 'image_width',       label: window.I18n ? (I18n.getLanguage()==='en' ? 'Width' : '宽度') : '宽度', fmt: v => `${v}px` },
                { key: 'image_height',      label: window.I18n ? (I18n.getLanguage()==='en' ? 'Height' : '高度') : '高度', fmt: v => `${v}px` },
            ];

            const items = fields
                .filter(f => exif[f.key] !== null && exif[f.key] !== undefined && exif[f.key] !== '')
                .map(f => {
                    const val = f.fmt ? f.fmt(exif[f.key]) : String(exif[f.key]);
                    return `<div class="exif-item${f.wide ? ' exif-wide' : ''}">
                        <span class="exif-label">${f.label}</span>
                        <span class="exif-value">${val}</span>
                    </div>`;
                });

            // GPS
            if (exif.gps && exif.gps.lat !== undefined) {
                const gpsLabel = window.I18n ? I18n.t('exif.gps') : 'GPS';
                items.push(`<div class="exif-item exif-wide">
                    <span class="exif-label">${gpsLabel}</span>
                    <span class="exif-value">${exif.gps.lat.toFixed(5)}, ${exif.gps.lng.toFixed(5)}</span>
                </div>`);
            }

            if (items.length === 0) return;

            grid.innerHTML = items.join('');
            panel.style.display = 'block';
        } catch (e) {
            console.warn('[EXIF] 加载失败（非致命）:', e);
        }
    }

    /**
     * 刷新应用数据
     */
    async refresh() {
        try {
            console.log('🔄 刷新中...');
            await this.loadAlbumStats();
            // 目录树由 AlbumBrowser 统一管理
            if (window.AlbumBrowser) {
                await window.AlbumBrowser.loadTree();
            }
            // 如果当前有选中目录，也刷新照片列表（委托给 AlbumBrowser 以保留分页/多选状态）
            const currentPath = window.AlbumBrowser && window.AlbumBrowser.currentPath;
            if (currentPath) {
                delete window.AlbumBrowser.photosCache[currentPath]; // 清除缓存确保重新加载
                await window.AlbumBrowser.loadPhotos(currentPath);
            }
            console.log('✅ 刷新完成');
            this.showSuccess('刷新成功');
        } catch (error) {
            console.error('刷新失败:', error);
            this.showError('刷新失败: ' + error.message);
        }
    }

    /**
     * 显示导入对话框
     */
    showImportDialog() {
        if (window.importDialog && typeof window.importDialog.open === 'function') {
            // 目录树数据统一由 AlbumBrowser 管理
            const treeData = (window.AlbumBrowser && window.AlbumBrowser.treeData) || this.albumTree;
            window.importDialog.open(treeData?.path || null);
        } else {
            console.error('[showImportDialog] importDialog 实例不可用');
            alert('导入功能未加载，请刷新页面');
        }
    }

    /**
     * 显示设置对话框
     */
    showSettingsDialog() {
        console.log('[Event] 显示设置对话框');
        if (window.SettingsDialog && typeof window.SettingsDialog.open === 'function') {
            window.SettingsDialog.open();
        } else {
            console.error('SettingsDialog 不可用');
            alert('设置功能未加载，请刷新页面');
        }
    }

    /**
     * 加载设置信息
     */
    async loadSettings() {
        try {
            const config = await API.getAlbumPath();
            document.getElementById('settings-album-path').value = config.album_path || '-';
        } catch (error) {
            console.error('加载设置失败:', error);
        }
    }

    /**
     * 显示帮助
     */
    showHelp() {
        const dialog = document.getElementById('help-dialog');
        if (dialog) {
            dialog.style.display = 'flex';
        }
    }

    /**
     * 显示成功提示
     */
    showSuccess(message) {
        console.log('✅', message);
        this.showNotification(message, 'success');
    }

    /**
     * 显示错误提示
     */
    showError(message) {
        console.error('❌', message);
        this.showNotification(message, 'error');
    }

    /**
     * 显示警告提示
     */
    showWarning(message) {
        console.warn('⚠️', message);
        this.showNotification(message, 'warning');
    }

    /**
     * 显示通知（Toast）
     * @param {string} message
     * @param {'info'|'success'|'warning'|'error'} type
     * @param {number} duration - 自动消失毫秒数，0=不自动消失
     */
    showNotification(message, type = 'info', duration = 3500) {
        const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
        const container = document.getElementById('toast-container');
        if (!container) {
            console.log(`[${type}] ${message}`);
            return;
        }

        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;

        const iconSpan = document.createElement('span');
        iconSpan.className = 'toast-icon';
        iconSpan.textContent = icons[type] || 'ℹ️';

        const msgSpan = document.createElement('span');
        msgSpan.className = 'toast-message';
        msgSpan.textContent = message;  // 安全注入，防止 XSS

        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', '关闭');
        closeBtn.textContent = '✕';

        toast.appendChild(iconSpan);
        toast.appendChild(msgSpan);
        toast.appendChild(closeBtn);

        const remove = () => {
            toast.classList.add('toast--out');
            toast.addEventListener('animationend', () => toast.remove(), { once: true });
        };

        closeBtn.addEventListener('click', remove);
        container.appendChild(toast);

        if (duration > 0) {
            setTimeout(remove, duration);
        }
    }

    /**
     * 清空缓存
     */
    clearAppCache() {
        // 这可以用于清空本地缓存
        console.log('缓存已清空');
    }

    /**
     * HTML 转义，防止 XSS（BUG-020）
     * @param {*} str - 任意值，将被强制转换为字符串
     * @returns {string} 转义后的安全字符串
     */
    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}

/**
 * 应用启动
 */
window.app = new App();

// 快捷键处理
document.addEventListener('keydown', (e) => {
    // ESC 关闭最顶层的弹窗（按 z-index 从高到低）
    if (e.key === 'Escape') {
        const previewModal    = document.getElementById('photo-preview-modal');
        const importDialog    = document.getElementById('import-dialog');
        const settingsDialog  = document.getElementById('settings-dialog');
        const helpDialog      = document.getElementById('help-dialog');
        const deleteDialog    = document.getElementById('delete-confirm-dialog');
        const ctxMenu         = document.getElementById('photo-context-menu');

        if (ctxMenu && ctxMenu.style.display !== 'none') {
            ctxMenu.style.display = 'none';
        } else if (previewModal && previewModal.style.display !== 'none') {
            app.closePreviewModal();  // 预览弹窗在最上层
        } else if (deleteDialog && deleteDialog.style.display !== 'none') {
            deleteDialog.style.display = 'none';
        } else if (importDialog && importDialog.style.display !== 'none') {
            importDialog.style.display = 'none';  // 导入对话框
        } else if (settingsDialog && settingsDialog.style.display !== 'none') {
            settingsDialog.style.display = 'none';  // 设置对话框
        } else if (helpDialog && helpDialog.style.display !== 'none') {
            helpDialog.style.display = 'none';
        }
        return;
    }
    // ← → 预览翻页
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        const previewModal = document.getElementById('photo-preview-modal');
        if (previewModal && previewModal.style.display !== 'none') {
            e.preventDefault();
            if (e.key === 'ArrowLeft' && app._previewIndex > 0) {
                app._showPreviewItem(app._previewIndex - 1);
            } else if (e.key === 'ArrowRight' && app._previewList && app._previewIndex < app._previewList.length - 1) {
                app._showPreviewItem(app._previewIndex + 1);
            }
        }
        return;
    }
    // F5 刷新
    if (e.key === 'F5') {
        e.preventDefault();
        app.refresh();
    }
});
