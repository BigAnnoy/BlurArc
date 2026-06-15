/**
 * 导入对话框模块
 * 处理导入流程：路径选择 -> 预览 -> 导入 -> 进度显示
 */

class ImportDialog {
    constructor() {
        this.dialog = null;  // DOM 尚未解析，暂不查询
        this.sourcePath = null;
        this.targetPath = null;
        this.currentImportId = null;
        this.progressInterval = null;
        this.isCheckingSource = false;
        this.checkCancelled = false;
        this.checkRequestId = 0;
        this.selectedDuplicatePhotos = new Set();  // 目标重复选中的照片
        this.selectedSourceDuplicates = new Set();  // 源重复选中的照片
        this.importMode = 'copy';  // 导入模式：'copy' 复制 | 'move' 剪切
    }

    /**
     * 初始化（需在 DOM 解析完成后调用）
     */
    init() {
        // 此时 DOM 已解析，可以安全获取元素
        this.dialog = document.getElementById('import-dialog');
        if (!this.dialog) {
            console.error('[ImportDialog] 找不到 #import-dialog 元素');
            return;
        }
        this.bindEvents();
        this.setupButtonVisibilityObserver();
    }

    /**
     * 设置按钮可见性观察器
     * 根据导入步骤动态显示/隐藏对应的按钮
     */
    setupButtonVisibilityObserver() {
        if (!this.dialog) return;
        
        this._buttonObserver = new MutationObserver(() => {
            const step1 = this.dialog.querySelector('.import-step-1').style.display;
            const step2 = this.dialog.querySelector('.import-step-2').style.display;
            const step3 = this.dialog.querySelector('.import-step-3').style.display;
            
            const selectPathBtn = document.getElementById('select-source-path');
            const startImportBtn = document.getElementById('start-import-btn');
            const cancelImportBtn = document.getElementById('cancel-import-btn');
            const pauseImportBtn = document.getElementById('pause-import-btn');
            
            // 检查导入是否已结束（用于 step3 时隐藏按钮）
            const isImportEnded = this.currentImportId && this._importEnded;
            
            if (selectPathBtn) selectPathBtn.style.display = step1 !== 'none' ? 'block' : 'none';
            if (startImportBtn) startImportBtn.style.display = step2 !== 'none' ? 'block' : 'none';
            
            // step3 时，如果导入已结束则隐藏按钮，否则显示
            if (step3 !== 'none') {
                if (cancelImportBtn) cancelImportBtn.style.display = isImportEnded ? 'none' : 'block';
                if (pauseImportBtn) pauseImportBtn.style.display = isImportEnded ? 'none' : 'block';
            } else {
                if (cancelImportBtn) cancelImportBtn.style.display = 'none';
                if (pauseImportBtn) pauseImportBtn.style.display = 'none';
            }
        });
        
        const steps = this.dialog.querySelectorAll('.import-step-1, .import-step-2, .import-step-3');
        steps.forEach(step => {
            this._buttonObserver.observe(step, { attributes: true, attributeFilter: ['style'] });
        });
        
        // 初始显示第一步按钮
        const selectPathBtn = document.getElementById('select-source-path');
        if (selectPathBtn) selectPathBtn.style.display = 'block';
    }

    /**
     * 触发按钮可见性更新
     * 用于导入完成后强制刷新按钮状态
     */
    _triggerButtonVisibilityUpdate() {
        const step3 = this.dialog?.querySelector('.import-step-3');
        const cancelImportBtn = document.getElementById('cancel-import-btn');
        const pauseImportBtn = document.getElementById('pause-import-btn');
        
        if (step3 && step3.style.display !== 'none') {
            if (cancelImportBtn) cancelImportBtn.style.display = 'none';
            if (pauseImportBtn) pauseImportBtn.style.display = 'none';
        }
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 关闭按钮
        const closeBtn = this.dialog?.querySelector('.close-import-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // 取消按钮
        const cancelBtn = this.dialog?.querySelector('.cancel-import-dialog');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }

        // 浏览源文件夹按钮
        const browseSourceBtn = this.dialog?.querySelector('#btn-browse-source');
        if (browseSourceBtn) {
            browseSourceBtn.addEventListener('click', () => this.browseSourcePath());
        }

        // 选择源路径
        const selectSourceBtn = this.dialog?.querySelector('#select-source-path');
        if (selectSourceBtn) {
            selectSourceBtn.addEventListener('click', () => this.selectSourcePath());
        }

        // 开始导入
        const startBtn = this.dialog?.querySelector('#start-import-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startImport());
        }

        // 取消导入
        const cancelImportBtn = this.dialog?.querySelector('#cancel-import-btn');
        if (cancelImportBtn) {
            cancelImportBtn.addEventListener('click', () => this.cancelCurrentImport());
        }

        // 暂停/继续导入
        const pauseImportBtn = this.dialog?.querySelector('#pause-import-btn');
        if (pauseImportBtn) {
            pauseImportBtn.addEventListener('click', () => this.togglePauseImport());
        }

        // 注：导入完成和失败的弹窗已移除，改为纯 Toast 提示
    }

    /**
     * 打开对话框
     */
    async open(targetPath) {
        this.sourcePath = null;
        this.resetUI();

        // 若调用方未传入 targetPath，从 settings API 获取配置中的相册路径
        if (!targetPath) {
            try {
                const config = await window.api.get('/settings/album-path');
                targetPath = config && config.album_path ? config.album_path : null;
            } catch (e) {
                console.warn('[ImportDialog] 获取相册路径失败，targetPath 将为 null', e);
                targetPath = null;
            }
        }
        this.targetPath = targetPath;
        
        // 设置对话框显示
        this.dialog.style.display = 'flex';
        this.dialog.setAttribute('aria-hidden', 'false');
        
        // 步骤1：设置较窄的宽度
        const modalContent = this.dialog.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.maxWidth = '600px';
        }
        
        // 重新设置按钮可见性观察器（因为 close() 时会断开）
        this.setupButtonVisibilityObserver();
        
        // 添加键盘事件监听
        this.bindKeyboardEvents();
        
        // 设置焦点到对话框的第一个可交互元素
        this.focusFirstInteractiveElement();
        
        // 禁用背景滚动
        document.body.style.overflow = 'hidden';
    }

    /**
     * 关闭对话框
     */
    close() {
        if (!this.dialog) return;
        
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        // 清理 MutationObserver
        if (this._buttonObserver) {
            this._buttonObserver.disconnect();
            this._buttonObserver = null;
        }
        
        // 清理 PhotoSelection 实例
        if (this._targetDupSelection) {
            this._targetDupSelection.exitSelectionMode();
            this._targetDupSelection = null;
        }
        if (this._sourceDupSelection) {
            this._sourceDupSelection.exitSelectionMode();
            this._sourceDupSelection = null;
        }
        if (this._timelineSelection) {
            this._timelineSelection.exitSelectionMode();
            this._timelineSelection = null;
        }
        
        this.isCheckingSource = false;
        this.checkCancelled = false;
        
        // 隐藏对话框
        this.dialog.style.display = 'none';
        this.dialog.setAttribute('aria-hidden', 'true');
        
        // 移除键盘事件监听
        this.unbindKeyboardEvents();
        
        // 恢复背景滚动
        document.body.style.overflow = 'auto';
    }
    
    /**
     * 绑定键盘事件
     */
    bindKeyboardEvents() {
        // ESC键关闭对话框
        this.escKeyHandler = (e) => {
            if (e.key === 'Escape') {
                this.close();
            }
        };
        document.addEventListener('keydown', this.escKeyHandler);
    }
    
    /**
     * 移除键盘事件监听
     */
    unbindKeyboardEvents() {
        if (this.escKeyHandler) {
            document.removeEventListener('keydown', this.escKeyHandler);
            this.escKeyHandler = null;
        }
    }
    
    /**
     * 聚焦到对话框的第一个可交互元素
     */
    focusFirstInteractiveElement() {
        const firstInput = this.dialog.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstInput) {
            firstInput.focus();
        }
    }

    /**
     * 重置 UI
     */
    resetUI() {
        // 重置为初始状态
        const step1 = this.dialog.querySelector('.import-step-1');
        const step2 = this.dialog.querySelector('.import-step-2');
        const step3 = this.dialog.querySelector('.import-step-3');

        if (step1) step1.style.display = 'block';
        if (step2) step2.style.display = 'none';
        if (step3) step3.style.display = 'none';

        // 清空文本
        const sourcePathInput = this.dialog.querySelector('#source-path-input');
        if (sourcePathInput) sourcePathInput.value = '';

        // 清空选择集
        this.selectedDuplicatePhotos.clear();
        this.selectedSourceDuplicates.clear();

        // 只清空内容区域，保留tab导航结构
        const dateFoldersInfo = this.dialog.querySelector('#date-folders .preview-info');
        const dateFoldersList = this.dialog.querySelector('#date-folders .date-folders-list');
        const targetDuplicatesInfo = this.dialog.querySelector('#target-duplicates .duplicates-info');
        const targetDuplicatesList = this.dialog.querySelector('#target-duplicates .duplicates-list');
        const sourceDuplicatesInfo = this.dialog.querySelector('#source-duplicates .source-duplicates-info');
        const sourceDuplicatesList = this.dialog.querySelector('#source-duplicates .source-duplicates-list');
        
        if (dateFoldersInfo) dateFoldersInfo.innerHTML = '';
        if (dateFoldersList) dateFoldersList.innerHTML = '';
        if (targetDuplicatesInfo) targetDuplicatesInfo.innerHTML = '';
        if (targetDuplicatesList) targetDuplicatesList.innerHTML = '';
        if (sourceDuplicatesInfo) sourceDuplicatesInfo.innerHTML = '';
        if (sourceDuplicatesList) sourceDuplicatesList.innerHTML = '';

        // 重置步骤1检查状态和进度条
        this.isCheckingSource = false;
        this.checkCancelled = false;
        this.setStep1CheckingState(false);
        this.hideStep1Progress();
    }

    setStep1CheckingState(isChecking) {
        const selectBtn = this.dialog?.querySelector('#select-source-path');
        if (!selectBtn) return;

        if (isChecking) {
            selectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 取消';
            selectBtn.className = 'btn btn-warning';
            selectBtn.disabled = false;
        } else {
            selectBtn.innerHTML = '确认';
            selectBtn.className = 'btn btn-primary';
            selectBtn.disabled = false;
        }
    }

    resetStep1Progress() {
        const progressBar = document.getElementById('step1-progress-bar');
        if (progressBar) {
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', '0');
        }

        const progressStatus = document.getElementById('step1-progress-status');
        if (progressStatus) {
            progressStatus.textContent = '正在扫描文件...';
        }

        const progressPercentage = document.getElementById('step1-progress-percentage');
        if (progressPercentage) {
            progressPercentage.textContent = '0%';
        }
    }

    updateStep1ProgressStatus(progressData) {
        const progressStatus = document.getElementById('step1-progress-status');
        if (!progressStatus || !progressData) return;

        const stageMap = {
            queued: '任务已排队',
            scanning: '正在扫描源目录...',
            grouping: '正在按日期整理预览...',
            source_duplicates: '正在检测源重复...',
            target_duplicates: '正在检测目标重复...',
            completed: '检查完成',
            failed: '检查失败'
        };

        const stageText = stageMap[progressData.stage] || '处理中...';
        const detail = progressData.detail ? ` ${progressData.detail}` : '';
        progressStatus.textContent = `${stageText}${detail}`;
    }

    showStep1Progress() {
        const progressContainer = document.getElementById('step1-progress');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
        this.resetStep1Progress();
    }

    hideStep1Progress() {
        const progressContainer = document.getElementById('step1-progress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }

    /**
     * 浏览源文件夹
     */
    async browseSourcePath() {
        try {
            // 检查 PyWebView API 是否可用
            if (window.pywebview && window.pywebview.api) {
                console.log('使用 PyWebView API 选择源文件夹...');
                console.trace('browseSourcePath 调用栈');
                const path = await window.pywebview.api.select_folder();
                
                if (path && typeof path === 'string' && path.trim()) {
                    console.log('选择的源路径:', path);
                    
                    // 更新输入框
                    const pathInput = this.dialog.querySelector('#source-path-input');
                    if (pathInput) {
                        pathInput.value = path;
                    }
                } else {
                    console.log('用户取消了文件夹选择');
                }
            } else {
                // 降级方案：提示用户使用手动输入
                console.warn('PyWebView API 不可用，使用手动输入');
                alert('无法使用文件夹选择功能，请手动输入源路径');
            }
        } catch (error) {
            console.error('选择源文件夹失败:', error);
            alert('选择源文件夹失败: ' + error.message);
        }
    }

    /**
     * 选择源路径
     */
    async selectSourcePath() {
        console.log('selectSourcePath called');

        // 同一个按钮复用“确认/取消”，检查进行中时点击即视为取消，不再重入
        if (this.isCheckingSource) {
            this.checkCancelled = true;
            this.isCheckingSource = false;
            this.setStep1CheckingState(false);
            this.updateStep1ProgressStatus({ stage: 'failed', detail: '已取消' });
            this.hideStep1Progress();
            console.log('[selectSourcePath] 用户取消步骤1检查');
            return;
        }

        const pathInput = this.dialog.querySelector('#source-path-input');
        if (!pathInput) {
            console.error('No #source-path-input element found');
            return;
        }

        const sourcePath = pathInput.value.trim();
        if (!sourcePath) {
            alert('请选择或输入源路径');
            return;
        }
        
        this.isCheckingSource = true;
        this.checkCancelled = false;
        const requestId = ++this.checkRequestId;
        this.setStep1CheckingState(true);
        this.showStep1Progress();

        try {
            // 实际API调用
            const result = await API.checkImportPath(sourcePath, (progress, progressData) => {
                // 更新进度条
                if (!this.isCheckingSource || this.checkCancelled || requestId !== this.checkRequestId) return;
                
                const progressBar = document.getElementById('step1-progress-bar');
                if (progressBar) {
                    const percentage = Math.round(progress * 100);
                    progressBar.style.width = `${percentage}%`;
                    progressBar.setAttribute('aria-valuenow', percentage);
                }
                
                // 更新百分比显示
                const progressPercentage = document.getElementById('step1-progress-percentage');
                if (progressPercentage) {
                    const percentage = Math.round(progress * 100);
                    progressPercentage.textContent = `${percentage}%`;
                }

                // 更新阶段文案
                this.updateStep1ProgressStatus(progressData);
            }, () => this.checkCancelled || requestId !== this.checkRequestId || !this.isCheckingSource);
            
            // 如果已取消，不继续处理
            if (this.checkCancelled || requestId !== this.checkRequestId) {
                console.log('[selectSourcePath] 检查结果已忽略（已取消或过期请求）');
                return;
            }
            
            console.log('Import path check result:', result);
            
            if (result.status === 'valid') {
                this.sourcePath = result.source_path;
                console.log('Moving to step 2');
                this.moveToStep2();
                console.log('Calling showPreview with result:', result);
                this.showPreview(result);
            }
        } catch (error) {
            if (error && error.message === 'CHECK_CANCELLED') {
                return;
            }
            if (this.checkCancelled || requestId !== this.checkRequestId) {
                return;
            }
            console.error('Error checking import path:', error);
            alert(`路径检查失败: ${error.message}`);
        } finally {
            if (requestId === this.checkRequestId) {
                this.isCheckingSource = false;
                this.setStep1CheckingState(false);
                this.hideStep1Progress();
            }
        }
    }

    /**
     * 显示预览
     */
    showPreview(data) {
        // 保存预览数据
        this.previewData = data;
        
        console.log('[showPreview] 收到的数据:', data);
        console.log('[showPreview] 目标重复数据:', data.target_duplicates);
        
        const step2 = this.dialog.querySelector('.import-step-2');
        if (step2) {
            // 预计算重复数量，避免在模板字符串中重复计算
            const targetDupCount = data.target_duplicates ? Object.keys(data.target_duplicates).length : 0;
            const sourceDupCount = data.source_duplicates ? Object.keys(data.source_duplicates).length : 0;
            const dateFolderCount = data.date_folders ? data.date_folders.length : 0;

            // 直接替换整个步骤2的内容，确保所有元素都存在
            step2.innerHTML = `
                <h3>步骤 2: 预览文件</h3>
                <div class="file-preview" aria-live="polite">
                    <!-- 摘要卡片 -->
                    <div class="preview-stats">
                        <div class="stat-card">
                            <div class="stat-value">${data.media_count}</div>
                            <div class="stat-label">媒体文件</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.total_size_mb} MB</div>
                            <div class="stat-label">总大小</div>
                        </div>
                        <div class="stat-card ${targetDupCount > 0 ? 'stat-card--warn' : ''}">
                            <div class="stat-value">${targetDupCount}</div>
                            <div class="stat-label">相册重复</div>
                        </div>
                        <div class="stat-card ${sourceDupCount > 0 ? 'stat-card--warn' : ''}">
                            <div class="stat-value">${sourceDupCount}</div>
                            <div class="stat-label">来源重复</div>
                        </div>
                    </div>
                    <div class="preview-path">源路径：${this._escapeHtml(data.source_path)}</div>
                    
                    <!-- Tab 导航 -->
                    <div class="tab-nav">
                        <button class="tab-btn active" data-tab="date-folders">📅 时间线 <span class="tab-badge">${dateFolderCount}</span></button>
                        <button class="tab-btn" data-tab="target-duplicates">⚠️ 已在相册${targetDupCount > 0 ? ` <span class="tab-badge tab-badge--warn">${targetDupCount}</span>` : ''}</button>
                        <button class="tab-btn" data-tab="source-duplicates">🗂 文件夹内重复${sourceDupCount > 0 ? ` <span class="tab-badge tab-badge--warn">${sourceDupCount}</span>` : ''}</button>
                    </div>
                    
                    <!-- Tab 内容区域 -->
                    <div class="tab-content">
                        <!-- 时间线 Tab -->
                        <div class="tab-pane active" id="date-folders">
                            <p class="tab-hint">按拍摄日期浏览待导入的照片，确认内容无误后点击「开始导入」。</p>
                            <div class="duplicates-info timeline-actions-bar">
                                <span><strong>待导入：</strong> ${data.media_count} 个文件</span>
                                <div class="duplicates-actions">
                                    <button class="btn btn-sm btn-danger-ghost" id="btn-delete-timeline-selected" disabled title="删除选中的文件（从源文件夹）">🗑 删除所选</button>
                                </div>
                            </div>
                            <div class="date-view-container">
                                <!-- 左边日期筛选框 -->
                                <div class="date-filter-panel">
                                    <h4>日期筛选</h4>
                                    <div class="date-filter-list">
                                        ${data.date_folders && data.date_folders.length > 0 ? 
                                            data.date_folders.map(folder => `
                                                <div class="date-filter-item" data-date="${folder.name}">
                                                    <div class="date-filter-name">${folder.name}</div>
                                                    <div class="date-filter-count">${folder.count} 个文件</div>
                                                </div>
                                            `).join('') : 
                                            '<div class="empty-state"><p>没有按日期组织的文件夹</p></div>'
                                        }
                                    </div>
                                </div>
                                
                                <!-- 右边照片预览框 -->
                                <div class="photos-preview-panel">
                                    <h4>照片预览</h4>
                                    <div class="photos-container" id="preview-photos-container">
                                        <div class="welcome-message">
                                            <p>请选择左侧的日期查看照片</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 已在相册 Tab -->
                        <div class="tab-pane" id="target-duplicates">
                            <p class="tab-hint">以下照片与相册中的文件内容完全相同。导入后将以 <code>_dup</code> 后缀保存，你可以事后手动删除，或现在从源文件夹删除以跳过导入。</p>
                            <div class="duplicates-info" style="flex-wrap: wrap;">
                                <span><strong>已在相册：</strong> ${targetDupCount} 组</span>
                                <label class="skip-target-dup-label" style="display: flex; align-items: center; gap: 6px; margin-left: 16px; font-size: 13px; color: var(--color-text-secondary); cursor: pointer;">
                                    <input type="checkbox" id="skip-target-duplicates" style="cursor: pointer;">
                                    <span>跳过这些重复文件，不导入到相册</span>
                                </label>
                                <div class="duplicates-actions">
                                    <button class="btn btn-sm btn-warning" id="btn-select-duplicates" title="选中导入的重复照片">选择重复照片</button>
                                    <button class="btn btn-sm btn-secondary" id="btn-clear-selection" title="清除选择" disabled>删除选择</button>
                                </div>
                            </div>
                            <div class="duplicates-container">
                                <!-- 左边重复文件组列表 -->
                                <div class="duplicates-list-panel">
                                    <h4>重复文件</h4>
                                    <div class="duplicates-list">
                                        ${targetDupCount > 0 ? 
                                            Object.entries(data.target_duplicates).map(([hash, files]) => {
                                                const srcFile = files[files.length - 1];
                                                const fileName = srcFile ? srcFile.name : hash.slice(0, 8);
                                                const safeFileName = this._escapeHtml(fileName);
                                                return `
                                                <div class="duplicate-item" data-hash="${hash}">
                                                    <div class="duplicate-name" title="${safeFileName}">📷 ${safeFileName}</div>
                                                    <div class="duplicate-count">与相册中文件重复</div>
                                                </div>`;
                                            }).join('') : 
                                            '<div class="empty-state"><p>没有发现相册中已有的文件</p></div>'
                                        }
                                    </div>
                                </div>
                                
                                <!-- 右边重复照片预览 -->
                                <div class="duplicates-preview-panel">
                                    <h4>重复照片预览</h4>
                                    <div class="photos-container" id="target-duplicates-preview">
                                        <div class="welcome-message">
                                            <p>请选择左侧的重复文件组查看照片</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 文件夹内重复 Tab -->
                        <div class="tab-pane" id="source-duplicates">
                            <p class="tab-hint">以下是你选择的文件夹中自身存在的重复文件（同一张照片有多个副本）。建议在导入前删除多余的副本，只保留一份。</p>
                            <div class="duplicates-info source-duplicates-info">
                                <span><strong>文件夹内重复：</strong> ${sourceDupCount} 组</span>
                                <div class="duplicates-actions">
                                    <button class="btn btn-sm btn-warning" id="btn-select-source-duplicates" title="选中所有重复照片">选择重复照片</button>
                                    <button class="btn btn-sm btn-secondary" id="btn-clear-source-selection" title="清除选择" disabled>删除选择</button>
                                </div>
                            </div>
                            <div class="duplicates-container">
                                <!-- 左边重复文件组列表 -->
                                <div class="duplicates-list-panel">
                                    <h4>重复文件组</h4>
                                    <div class="duplicates-list">
                                        ${sourceDupCount > 0 ? 
                                            Object.entries(data.source_duplicates).map(([hash, files]) => {
                                                const f = files[0];
                                                const p = f ? (typeof f === 'string' ? f : (f.path || f.name || '')) : '';
                                                const firstName = p.split(/[\\\/]/).pop() || hash.slice(0, 8);
                                                const safeFirstName = this._escapeHtml(firstName);
                                                return `
                                                <div class="duplicate-item" data-hash="${hash}">
                                                    <div class="duplicate-name" title="${safeFirstName}">📷 ${safeFirstName}</div>
                                                    <div class="duplicate-count">${files.length} 个重复文件</div>
                                                </div>`;
                                            }).join('') : 
                                            '<div class="empty-state"><p>没有发现源重复文件</p></div>'
                                        }
                                    </div>
                                </div>
                                
                                <!-- 右边重复照片预览 -->
                                <div class="duplicates-preview-panel">
                                    <h4>重复照片预览</h4>
                                    <div class="photos-container" id="source-duplicates-preview">
                                        <div class="welcome-message">
                                            <p>请选择左侧的重复文件组查看照片</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 重新绑定tab事件
            this.bindTabEvents();
            
            // 绑定日期筛选事件
            this.bindDateFilterEvents();
            
            // 绑定重复文件组事件
            this.bindDuplicatesEvents();
        }
    }
    
    /**
     * 绑定Tab事件
     */
    bindTabEvents() {
        const tabNav = this.dialog.querySelector('.tab-nav');
        if (tabNav) {
            tabNav.addEventListener('click', (e) => {
                if (e.target.classList.contains('tab-btn')) {
                    // 移除所有active类
                    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
                    
                    // 添加active类到当前点击的按钮和对应的内容
                    e.target.classList.add('active');
                    const targetTab = e.target.dataset.tab;
                    const tabPane = document.getElementById(targetTab);
                    if (tabPane) {
                        tabPane.classList.add('active');
                    }
                }
            });
        }
    }
    
    /**
     * 绑定日期筛选事件
     */
    bindDateFilterEvents() {
        const dateFilterItems = this.dialog.querySelectorAll('.date-filter-item');
        const photosContainer = document.getElementById('preview-photos-container');
        
        dateFilterItems.forEach(item => {
            item.addEventListener('click', (e) => {
                // 移除所有选中状态
                dateFilterItems.forEach(i => i.classList.remove('selected'));
                // 添加选中状态到当前点击的日期
                item.classList.add('selected');
                
                // 获取选中的日期
                const selectedDate = item.dataset.date;
                
                // 查找对应的照片
                const selectedDateFolder = this.previewData.date_folders.find(folder => folder.name === selectedDate);
                
                if (selectedDateFolder && selectedDateFolder.files) {
                    // 渲染照片网格
                    this.renderPhotosGrid(selectedDateFolder.files, photosContainer);
                } else {
                    // 显示空状态
                    photosContainer.innerHTML = `
                        <div class="empty-state">
                            <p>该日期没有照片</p>
                        </div>
                    `;
                }
            });
        });

        // 自动选中第一个日期，右侧立即显示照片
        const firstItem = this.dialog.querySelector('.date-filter-item');
        if (firstItem) firstItem.click();
    }
    
    /**
     * 渲染照片网格（时间线 Tab）
     * 单击=预览，长按/勾选框=多选模式
     */
    renderPhotosGrid(photos, container) {
        if (!photos || photos.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>没有照片可显示</p>
                </div>
            `;
            return;
        }
        
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        photos.forEach(photo => {
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.dataset.path = photo.path || '';
            photoItem.dataset.name = photo.name || '';
            photoItem.dataset.url = photo.url || photo.thumbnail_url || '';
            photoItem.dataset.size = photo.size || 0;

            // 勾选框
            const checkbox = document.createElement('div');
            checkbox.className = 'photo-checkbox';
            photoItem.appendChild(checkbox);

            photoItem.appendChild(this._createPhotoImage(photo));
            
            const name = document.createElement('div');
            name.className = 'photo-name';
            name.textContent = photo.name;
            name.title = photo.name;
            photoItem.appendChild(name);
            
            grid.appendChild(photoItem);
        });
        
        container.innerHTML = '';
        container.appendChild(grid);

        // 接入 PhotoSelection（只创建一次，复用实例以保留选中状态）
        if (window.PhotoSelection) {
            if (!this._timelineSelection) {
                this._timelineSelection = new PhotoSelection({
                    onPreview: (photoData) => {
                        this.previewPhoto({
                            name: photoData.name,
                            path: photoData.path,
                            thumbnail_url: photoData.thumbnail_url,
                            url: photoData.url,
                            size: photoData.size
                        });
                    },
                    onSelectionChange: (selectedPaths) => {
                        const btnDel = document.getElementById('btn-delete-timeline-selected');
                        if (btnDel) btnDel.disabled = selectedPaths.size === 0;
                        this._timelineSelectedPaths = new Set(selectedPaths);
                    }
                });
            }
            this._timelineSelection.attachToGrid(grid, {
                getPhoto: (item) => ({
                    name: item.dataset.name || '',
                    path: item.dataset.path || '',
                    thumbnail_url: item.querySelector('img.photo-image')?.src || '',
                    url: item.dataset.url || '',
                    size: Number(item.dataset.size) || 0
                })
            });
        }
    }
    
    /**
     * 预览照片（使用与照片管理页面相同的模态框）
     */
    previewPhoto(photo) {
        // 显示预览模态框
        const modal = document.getElementById('photo-preview-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
        
        // 设置预览内容
        const previewImage = document.getElementById('preview-image');
        const previewTitle = document.getElementById('preview-title');
        const previewName = document.getElementById('preview-name');
        const previewSize = document.getElementById('preview-size');
        const previewPath = document.getElementById('preview-path');
        
        if (previewImage) {
            // 尝试获取缩略图或使用占位符
            if (photo.thumbnail_url) {
                previewImage.src = photo.thumbnail_url;
            } else {
                // 使用占位符
                previewImage.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22 width%3D%22150%22 height%3D%22150%22 viewBox%3D%220 0 150 150%22%3E%3Crect width%3D%22150%22 height%3D%22150%22 fill%3D%22%23e0e0e0%22%2F%3E%3Ctext x%3D%2250%25%22 y%3D%2250%25%22 dominant-baseline%3D%22middle%22 text-anchor%3D%22middle%22 fill%3D%22%239e9e9e%22 font-size%3D%2214%22%3E📷%3C%2Ftext%3E%3C%2Fsvg%3E';
            }
            previewImage.alt = photo.name;
        }
        
        if (previewTitle) {
            previewTitle.textContent = `预览: ${photo.name}`;
        }
        
        if (previewName) {
            previewName.textContent = `文件名: ${photo.name}`;
        }
        
        if (previewSize) {
            const sizeMB = photo.size ? (photo.size / (1024 * 1024)).toFixed(2) : 0;
            previewSize.textContent = `文件大小: ${sizeMB} MB`;
        }
        
        if (previewPath) {
            previewPath.textContent = `文件路径: ${photo.path}`;
        }
        
        // 保存当前预览的照片信息到全局对象，以便模态框中的打开按钮使用
        if (!window.app) {
            window.app = {};
        }
        window.app.currentPreviewPhoto = photo;
        
        // 绑定模态框事件
        this.bindPreviewModalEvents();
    }
    
    /**
     * 绑定预览模态框事件
     */
    bindPreviewModalEvents() {
        // 关闭按钮
        const closeBtn = document.getElementById('close-preview-btn');
        const closeModalBtn = document.getElementById('close-preview-modal');
        
        if (closeBtn) {
            closeBtn.onclick = () => {
                this.closePreviewModal();
            };
        }
        
        if (closeModalBtn) {
            closeModalBtn.onclick = () => {
                this.closePreviewModal();
            };
        }
        
        // 打开文件按钮
        const openBtn = document.getElementById('open-file-btn');
        if (openBtn) {
            openBtn.onclick = () => {
                if (window.app && window.app.currentPreviewPhoto) {
                    this.openPhoto(window.app.currentPreviewPhoto);
                }
            };
        }
        
        // 点击模态框外部关闭
        const modal = document.getElementById('photo-preview-modal');
        if (modal) {
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closePreviewModal();
                }
            };
        }
    }
    
    /**
     * 关闭预览模态框
     */
    closePreviewModal() {
        const modal = document.getElementById('photo-preview-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        
        // 清空当前预览的照片信息
        if (window.app) {
            window.app.currentPreviewPhoto = null;
        }
    }
    
    /**
     * 打开照片
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
     * 绑定重复文件组事件
     */
    bindDuplicatesEvents() {
        console.log('[bindDuplicatesEvents] 开始绑定重复文件组事件');
        
        // 目标重复文件组事件
        const targetDuplicateItems = this.dialog.querySelectorAll('#target-duplicates .duplicate-item');
        const targetPreviewContainer = document.getElementById('target-duplicates-preview');
        
        console.log('[bindDuplicatesEvents] 找到目标重复项:', targetDuplicateItems.length);
        console.log('[bindDuplicatesEvents] targetPreviewContainer:', targetPreviewContainer);
        
        targetDuplicateItems.forEach(item => {
            item.addEventListener('click', (e) => {
                console.log('[目标重复项] 点击事件触发');
                
                // 移除所有选中状态
                targetDuplicateItems.forEach(i => i.classList.remove('selected'));
                // 添加选中状态到当前点击的文件组
                item.classList.add('selected');
                
                // 获取选中的哈希值
                const selectedHash = item.dataset.hash;
                console.log('[目标重复项] 选中的哈希值:', selectedHash);
                
                // 查找对应的文件
                const duplicateFiles = this.previewData.target_duplicates[selectedHash];
                console.log('[目标重复项] 对应文件:', duplicateFiles);
                
                if (duplicateFiles) {
                    // 渲染照片网格（目标重复需要排序：相册中已有在前）
                    this.renderTargetDuplicatePhotos(duplicateFiles, targetPreviewContainer, selectedHash);
                } else {
                    // 显示空状态
                    targetPreviewContainer.innerHTML = `
                        <div class="empty-state">
                            <p>该重复文件组没有文件</p>
                        </div>
                    `;
                }
            });
        });
        
        // 源重复文件组事件
        const sourceDuplicateItems = this.dialog.querySelectorAll('#source-duplicates .duplicate-item');
        const sourcePreviewContainer = document.getElementById('source-duplicates-preview');
        
        console.log('[bindDuplicatesEvents] 找到源重复项:', sourceDuplicateItems.length);
        
        sourceDuplicateItems.forEach(item => {
            item.addEventListener('click', (e) => {
                console.log('[源重复项] 点击事件触发');
                
                // 移除所有选中状态
                sourceDuplicateItems.forEach(i => i.classList.remove('selected'));
                // 添加选中状态到当前点击的文件组
                item.classList.add('selected');
                
                // 获取选中的哈希值
                const selectedHash = item.dataset.hash;
                
                // 查找对应的文件
                const duplicateFiles = this.previewData.source_duplicates[selectedHash];
                
                if (duplicateFiles) {
                    // 渲染照片网格（带路径显示）
                    this.renderSourceDuplicatePhotos(duplicateFiles, sourcePreviewContainer, selectedHash);
                } else {
                    // 显示空状态
                    sourcePreviewContainer.innerHTML = `
                        <div class="empty-state">
                            <p>该重复文件组没有文件</p>
                        </div>
                    `;
                }
            });
        });
        
        // 绑定"选择重复照片"按钮（目标重复）
        this.bindSelectDuplicatesButton();
        
        // 绑定"删除选择"按钮
        this.bindClearSelectionButton();
        
        // 绑定源重复按钮
        this.bindSelectSourceDuplicatesButton();
        this.bindClearSourceSelectionButton();

        // 绑定时间线删除按钮
        this.bindTimelineDeleteButton();
        
        console.log('[bindDuplicatesEvents] 绑定完成');
    }
    
    /**
     * 绑定"选择重复照片"按钮
     */
    bindSelectDuplicatesButton() {
        const selectBtn = document.getElementById('btn-select-duplicates');
        const clearBtn = document.getElementById('btn-clear-selection');
        
        if (selectBtn) {
            selectBtn.addEventListener('click', () => {
                this.selectedDuplicatePhotos = new Set();
                const albumPath = this.targetPath || '';
                
                // 遍历所有重复组，选中源文件夹里的重复文件（跳过相册里已有的）
                if (this.previewData && this.previewData.target_duplicates) {
                    for (const [hash, files] of Object.entries(this.previewData.target_duplicates)) {
                        // files[0] 是相册里已有的，选中其余源文件夹中的文件
                        files.slice(1).forEach(file => {
                            let filePath = typeof file === 'string' ? file : (file.path || '');
                            this.selectedDuplicatePhotos.add(filePath);
                        });
                    }
                }
                
                // 更新预览区域的 DOM 选中状态（通过 PhotoSelection 进入多选并标记）
                const previewContainer = document.getElementById('target-duplicates-preview');
                if (previewContainer) {
                    previewContainer.querySelectorAll('.photo-item').forEach(item => {
                        const path = item.dataset.path;
                        if (this.selectedDuplicatePhotos.has(path)) {
                            item.classList.add('selected');
                        } else {
                            item.classList.remove('selected');
                        }
                    });
                    // 如果有选中项，确保进入多选模式
                    if (this._targetDupSelection && this.selectedDuplicatePhotos.size > 0) {
                        this._targetDupSelection.enterSelectionMode();
                        // 同步 PhotoSelection 内部 Set
                        this._targetDupSelection.selectedPaths = new Set(this.selectedDuplicatePhotos);
                    }
                }
                
                if (clearBtn) {
                    clearBtn.disabled = this.selectedDuplicatePhotos.size === 0;
                }
                
                this.updateDuplicatesStats();
            });
        }
    }

    _extractPath(file) {
        return typeof file === 'string' ? file : (file && file.path ? file.path : '');
    }

    applyDeletedPathsToPreviewData(deletedPaths) {
        if (!this.previewData || !Array.isArray(deletedPaths) || deletedPaths.length === 0) {
            return;
        }

        const deletedSet = new Set(deletedPaths);

        // 1) 按日期视图：删除文件并更新 count/size，空文件夹移除
        if (Array.isArray(this.previewData.date_folders)) {
            this.previewData.date_folders = this.previewData.date_folders
                .map(folder => {
                    const files = Array.isArray(folder.files) ? folder.files : [];
                    const remained = files.filter(f => !deletedSet.has(this._extractPath(f)));
                    return {
                        ...folder,
                        files: remained,
                        count: remained.length,
                        size: remained.reduce((sum, f) => sum + (f.size || 0), 0)
                    };
                })
                .filter(folder => folder.count > 0);
        }

        // 2) 目标重复：删除条目，空组移除
        if (this.previewData.target_duplicates && typeof this.previewData.target_duplicates === 'object') {
            const nextTargetDup = {};
            for (const [hash, files] of Object.entries(this.previewData.target_duplicates)) {
                const remained = (files || []).filter(f => !deletedSet.has(this._extractPath(f)));
                if (remained.length > 0) {
                    nextTargetDup[hash] = remained;
                }
            }
            this.previewData.target_duplicates = nextTargetDup;
        }

        // 3) 源重复：删除条目，空组移除
        if (this.previewData.source_duplicates && typeof this.previewData.source_duplicates === 'object') {
            const nextSourceDup = {};
            for (const [hash, files] of Object.entries(this.previewData.source_duplicates)) {
                const remained = (files || []).filter(f => !deletedSet.has(this._extractPath(f)));
                if (remained.length > 0) {
                    nextSourceDup[hash] = remained;
                }
            }
            this.previewData.source_duplicates = nextSourceDup;
        }

        // 4) 汇总计数重新计算
        const allFiles = (this.previewData.date_folders || []).reduce((sum, folder) => sum + (folder.count || 0), 0);
        const totalSize = (this.previewData.date_folders || []).reduce((sum, folder) => sum + (folder.size || 0), 0);
        this.previewData.media_count = allFiles;
        this.previewData.total_size = totalSize;
        this.previewData.total_size_mb = Number((totalSize / (1024 * 1024)).toFixed(2));
    }

    refreshStep2TabsAfterDeletion(options = {}) {
        if (!this.previewData) return;

        const activeTabBtn = this.dialog.querySelector('.tab-btn.active');
        const activeTab = activeTabBtn ? activeTabBtn.dataset.tab : 'date-folders';
        const selectedDate = options.selectedDate || this.dialog.querySelector('.date-filter-item.selected')?.dataset.date || null;
        const selectedTargetHash = options.selectedTargetHash || this.dialog.querySelector('#target-duplicates .duplicate-item.selected')?.dataset.hash || null;
        const selectedSourceHash = options.selectedSourceHash || this.dialog.querySelector('#source-duplicates .duplicate-item.selected')?.dataset.hash || null;

        // 重建步骤2整体视图（会同步三个tab的计数和列表）
        this.showPreview(this.previewData);

        // 恢复 active tab
        const tabBtnToActivate = this.dialog.querySelector(`.tab-btn[data-tab="${activeTab}"]`);
        if (tabBtnToActivate) tabBtnToActivate.click();

        // 恢复日期选择并刷新右侧预览
        if (selectedDate) {
            const dateItem = this.dialog.querySelector(`.date-filter-item[data-date="${selectedDate}"]`);
            if (dateItem) dateItem.click();
        }

        // 恢复目标重复组选中并刷新右侧预览
        if (selectedTargetHash) {
            const targetItem = this.dialog.querySelector(`#target-duplicates .duplicate-item[data-hash="${selectedTargetHash}"]`);
            if (targetItem) targetItem.click();
        }

        // 恢复源重复组选中并刷新右侧预览
        if (selectedSourceHash) {
            const sourceItem = this.dialog.querySelector(`#source-duplicates .duplicate-item[data-hash="${selectedSourceHash}"]`);
            if (sourceItem) sourceItem.click();
        }

        // 重新同步按钮状态
        const clearTargetBtn = document.getElementById('btn-clear-selection');
        if (clearTargetBtn) clearTargetBtn.disabled = this.selectedDuplicatePhotos.size === 0;
        const clearSourceBtn = document.getElementById('btn-clear-source-selection');
        if (clearSourceBtn) clearSourceBtn.disabled = this.selectedSourceDuplicates.size === 0;

        this.updateDuplicatesStats();
        this.updateSourceDuplicatesStats();
    }
    
    /**
     * 绑定"删除选择"按钮
     */
    bindClearSelectionButton() {
        const clearBtn = document.getElementById('btn-clear-selection');
        
        if (clearBtn) {
            clearBtn.addEventListener('click', async () => {
                const selectedCount = this.selectedDuplicatePhotos.size;
                
                if (selectedCount === 0) {
                    return;
                }
                
                // 确认删除
                const confirmed = confirm(`确定要删除选中的 ${selectedCount} 个文件吗？\n\n此操作将从源文件夹中永久删除这些文件！`);
                
                if (!confirmed) {
                    return;
                }
                
                try {
                    // 调用后端API删除文件（传入源路径以允许删除源文件夹中的文件）
                    const response = await fetch('/api/files/delete', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            paths: Array.from(this.selectedDuplicatePhotos),
                            source_paths: this.sourcePath ? [this.sourcePath] : []
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const result = await response.json();
                    
                    if (result.status === 'completed') {
                        result.deleted.forEach(path => this.selectedDuplicatePhotos.delete(path));
                        result.deleted.forEach(path => this.selectedSourceDuplicates.delete(path));
                        const selectedTargetHash = document.querySelector('#target-duplicates .duplicate-item.selected')?.dataset.hash || null;
                        const selectedSourceHash = document.querySelector('#source-duplicates .duplicate-item.selected')?.dataset.hash || null;
                        const selectedDate = this.dialog.querySelector('.date-filter-item.selected')?.dataset.date || null;

                        this.applyDeletedPathsToPreviewData(result.deleted);
                        this.refreshStep2TabsAfterDeletion({ selectedDate, selectedTargetHash, selectedSourceHash });
                        
                        // 显示删除结果
                        if (result.failed_count > 0) {
                            alert(`已删除 ${result.deleted_count} 个文件\n删除失败 ${result.failed_count} 个文件`);
                        } else {
                            alert(`已成功删除 ${result.deleted_count} 个文件`);
                        }
                    } else {
                        alert('删除失败: ' + (result.error || '未知错误'));
                    }
                } catch (error) {
                    console.error('[删除文件] 错误:', error);
                    alert('删除文件时发生错误');
                }
            });
        }
    }
    
    /**
     * 绑定时间线 Tab 删除按钮
     */
    bindTimelineDeleteButton() {
        const delBtn = document.getElementById('btn-delete-timeline-selected');
        if (!delBtn) return;
        // 避免重复绑定
        if (delBtn._bound) return;
        delBtn._bound = true;

        delBtn.addEventListener('click', async () => {
            const paths = this._timelineSelectedPaths ? [...this._timelineSelectedPaths] : [];
            if (paths.length === 0) return;

            const confirmed = confirm(`确定要从源文件夹中删除选中的 ${paths.length} 个文件吗？\n\n此操作不可撤销！`);
            if (!confirmed) return;

            try {
                const response = await fetch('/api/files/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        paths,
                        source_paths: this.sourcePath ? [this.sourcePath] : []
                    })
                });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const result = await response.json();

                if (result.status === 'completed') {
                    this._timelineSelectedPaths = new Set();
                    const selectedDate = this.dialog.querySelector('.date-filter-item.selected')?.dataset.date || null;
                    const selectedTargetHash = this.dialog.querySelector('#target-duplicates .duplicate-item.selected')?.dataset.hash || null;
                    const selectedSourceHash = this.dialog.querySelector('#source-duplicates .duplicate-item.selected')?.dataset.hash || null;

                    this.applyDeletedPathsToPreviewData(result.deleted);
                    this.refreshStep2TabsAfterDeletion({ selectedDate, selectedTargetHash, selectedSourceHash });

                    if (result.failed_count > 0) {
                        alert(`已删除 ${result.deleted_count} 个文件\n删除失败 ${result.failed_count} 个文件`);
                    } else {
                        alert(`已成功删除 ${result.deleted_count} 个文件`);
                    }
                } else {
                    alert('删除失败: ' + (result.error || '未知错误'));
                }
            } catch (err) {
                console.error('[时间线删除] 错误:', err);
                alert('删除文件时发生错误');
            }
        });
    }

    /**
     * 绑定"选择重复照片"按钮（源重复）
     */
    bindSelectSourceDuplicatesButton() {
        const selectBtn = document.getElementById('btn-select-source-duplicates');
        const clearBtn = document.getElementById('btn-clear-source-selection');
        
        if (selectBtn) {
            selectBtn.addEventListener('click', () => {
                this.selectedSourceDuplicates = new Set();
                
                if (this.previewData && this.previewData.source_duplicates) {
                    for (const [hash, files] of Object.entries(this.previewData.source_duplicates)) {
                        files.slice(1).forEach(file => {
                            let filePath = typeof file === 'string' ? file : (file.path || '');
                            this.selectedSourceDuplicates.add(filePath);
                        });
                    }
                }
                
                // 更新预览区域的 DOM 选中状态
                const previewContainer = document.getElementById('source-duplicates-preview');
                if (previewContainer) {
                    previewContainer.querySelectorAll('.photo-item').forEach((item) => {
                        const path = item.dataset.path;
                        const parent = item.closest('.photos-grid');
                        const items = parent ? Array.from(parent.querySelectorAll('.photo-item')) : [item];
                        const itemIndex = items.indexOf(item);
                        
                        if (itemIndex > 0 && this.selectedSourceDuplicates.has(path)) {
                            item.classList.add('selected');
                        } else {
                            item.classList.remove('selected');
                        }
                    });
                    // 进入多选模式并同步 PhotoSelection 内部 Set
                    if (this._sourceDupSelection && this.selectedSourceDuplicates.size > 0) {
                        this._sourceDupSelection.enterSelectionMode();
                        this._sourceDupSelection.selectedPaths = new Set(this.selectedSourceDuplicates);
                    }
                }
                
                if (clearBtn) {
                    clearBtn.disabled = this.selectedSourceDuplicates.size === 0;
                }
                
                this.updateSourceDuplicatesStats();
            });
        }
    }
    
    /**
     * 绑定"删除选择"按钮（源重复）
     */
    bindClearSourceSelectionButton() {
        const clearBtn = document.getElementById('btn-clear-source-selection');
        
        if (clearBtn) {
            clearBtn.addEventListener('click', async () => {
                const selectedCount = this.selectedSourceDuplicates.size;
                
                if (selectedCount === 0) {
                    return;
                }
                
                // 确认删除
                const confirmed = confirm(`确定要删除选中的 ${selectedCount} 个文件吗？\n\n此操作将从源文件夹中永久删除这些文件！`);
                
                if (!confirmed) {
                    return;
                }
                
                try {
                    // 调用后端API删除文件（传入源路径以允许删除源文件夹中的文件）
                    const response = await fetch('/api/files/delete', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            paths: Array.from(this.selectedSourceDuplicates),
                            source_paths: this.sourcePath ? [this.sourcePath] : []
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const result = await response.json();
                    
                    if (result.status === 'completed') {
                        result.deleted.forEach(path => this.selectedSourceDuplicates.delete(path));
                        result.deleted.forEach(path => this.selectedDuplicatePhotos.delete(path));
                        const selectedTargetHash = document.querySelector('#target-duplicates .duplicate-item.selected')?.dataset.hash || null;
                        const selectedSourceHash = document.querySelector('#source-duplicates .duplicate-item.selected')?.dataset.hash || null;
                        const selectedDate = this.dialog.querySelector('.date-filter-item.selected')?.dataset.date || null;

                        this.applyDeletedPathsToPreviewData(result.deleted);
                        this.refreshStep2TabsAfterDeletion({ selectedDate, selectedTargetHash, selectedSourceHash });
                        
                        // 显示删除结果
                        if (result.failed_count > 0) {
                            alert(`已删除 ${result.deleted_count} 个文件\n删除失败 ${result.failed_count} 个文件`);
                        } else {
                            alert(`已成功删除 ${result.deleted_count} 个文件`);
                        }
                    } else {
                        alert('删除失败: ' + (result.error || '未知错误'));
                    }
                } catch (error) {
                    console.error('[删除文件] 错误:', error);
                    alert('删除文件时发生错误');
                }
            });
        }
    }
    
    /**
     * 更新源重复照片统计
     */
    updateSourceDuplicatesStats() {
        const infoContainer = document.querySelector('#source-duplicates .source-duplicates-info');
        if (!infoContainer) return;
        
        const selectedCount = this.selectedSourceDuplicates ? this.selectedSourceDuplicates.size : 0;
        
        // 查找或创建选中计数元素
        let selectedCountEl = infoContainer.querySelector('.selected-count');
        if (!selectedCountEl) {
            selectedCountEl = document.createElement('span');
            selectedCountEl.className = 'selected-count';
            infoContainer.appendChild(selectedCountEl);
        }
        
        if (selectedCount > 0) {
            selectedCountEl.innerHTML = ` <strong>已选：</strong>${selectedCount} 个文件`;
        } else {
            selectedCountEl.innerHTML = '';
        }
    }
    
    /**
     * 渲染源重复照片（带路径显示）
     * 单击=预览，长按/勾选框=多选，第一张（保留项）勾选框置灰不可选
     */
    renderSourceDuplicatePhotos(files, container, hash) {
        if (!files || files.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>没有重复照片可显示</p>
                </div>
            `;
            return;
        }
        
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        files.forEach((file, index) => {
            let photo;
            if (typeof file === 'string') {
                photo = {
                    name: file.split('\\').pop().split('/').pop(),
                    path: file,
                    size: 0
                };
            } else {
                photo = file;
            }
            
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.dataset.path = photo.path;
            photoItem.dataset.name = photo.name;
            photoItem.dataset.url = photo.thumbnail_url || photo.url || '';
            photoItem.dataset.size = photo.size || 0;

            // 勾选框（第一张保留项：置灰）
            const checkbox = document.createElement('div');
            checkbox.className = index === 0 ? 'photo-checkbox photo-checkbox--disabled' : 'photo-checkbox';
            photoItem.appendChild(checkbox);

            // 如果已选择，恢复选中样式（仅非保留项）
            if (index > 0 && this.selectedSourceDuplicates.has(photo.path)) {
                photoItem.classList.add('selected');
            }
            
            // 保留标记（第一个文件）
            if (index === 0) {
                const keepBadge = document.createElement('span');
                keepBadge.className = 'album-badge';
                keepBadge.textContent = '✓ 保留';
                photoItem.appendChild(keepBadge);
            }
            
            photoItem.appendChild(this._createPhotoImage(photo));
            
            const name = document.createElement('div');
            name.className = 'photo-name';
            name.textContent = photo.name;
            name.title = photo.name;
            
            const pathInfo = document.createElement('div');
            pathInfo.className = 'photo-path';
            pathInfo.textContent = photo.path;
            pathInfo.title = photo.path;
            
            photoItem.appendChild(name);
            photoItem.appendChild(pathInfo);
            
            grid.appendChild(photoItem);
        });
        
        container.innerHTML = '';
        container.appendChild(grid);

        // 接入 PhotoSelection（只创建一次，复用实例以保留选中状态）
        if (window.PhotoSelection) {
            if (!this._sourceDupSelection) {
                this._sourceDupSelection = new PhotoSelection({
                    onPreview: (photoData) => {
                        this.previewPhoto({
                            name: photoData.name,
                            path: photoData.path,
                            thumbnail_url: photoData.thumbnail_url,
                            url: photoData.url,
                            size: photoData.size
                        });
                    },
                    canSelect: (item) => {
                        const firstPath = typeof files[0] === 'string' ? files[0] : (files[0]?.path || '');
                        return item.dataset.path !== firstPath;
                    },
                    onSelectionChange: (selectedPaths) => {
                        files.slice(1).forEach(f => {
                            const p = typeof f === 'string' ? f : f.path;
                            if (selectedPaths.has(p)) {
                                this.selectedSourceDuplicates.add(p);
                            } else {
                                this.selectedSourceDuplicates.delete(p);
                            }
                        });
                        const clearBtn = document.getElementById('btn-clear-source-selection');
                        if (clearBtn) clearBtn.disabled = this.selectedSourceDuplicates.size === 0;
                        this.updateSourceDuplicatesStats();
                    }
                });
            } else {
                this._sourceDupSelection.onSelectionChange = (selectedPaths) => {
                    files.slice(1).forEach(f => {
                        const p = typeof f === 'string' ? f : f.path;
                        if (selectedPaths.has(p)) {
                            this.selectedSourceDuplicates.add(p);
                        } else {
                            this.selectedSourceDuplicates.delete(p);
                        }
                    });
                    const clearBtn = document.getElementById('btn-clear-source-selection');
                    if (clearBtn) clearBtn.disabled = this.selectedSourceDuplicates.size === 0;
                    this.updateSourceDuplicatesStats();
                };
            }
            this._sourceDupSelection.attachToGrid(grid, {
                getPhoto: (item) => ({
                    name: item.dataset.name || '',
                    path: item.dataset.path || '',
                    thumbnail_url: item.querySelector('img.photo-image')?.src || '',
                    url: item.dataset.url || '',
                    size: Number(item.dataset.size) || 0
                })
            });
        }
    }
    
    /**
     * 更新重复照片统计
     */
    updateDuplicatesStats() {
        const infoContainer = document.querySelector('#target-duplicates .duplicates-info');
        if (!infoContainer) return;
        
        const selectedCount = this.selectedDuplicatePhotos ? this.selectedDuplicatePhotos.size : 0;
        const totalDuplicates = this.previewData?.skipped_files || 0;
        
        // 查找或创建选中计数元素
        let selectedCountEl = infoContainer.querySelector('.selected-count');
        if (!selectedCountEl) {
            selectedCountEl = document.createElement('span');
            selectedCountEl.className = 'selected-count';
            infoContainer.appendChild(selectedCountEl);
        }
        
        if (selectedCount > 0) {
            selectedCountEl.innerHTML = ` <strong>已选：</strong>${selectedCount} 个文件`;
        } else {
            selectedCountEl.innerHTML = '';
        }
    }
    
    /**
     * 渲染目标重复照片（相册中已有排序在前）
     * 单击=预览，长按/勾选框=多选，选中照片路径同步到 selectedDuplicatePhotos
     */
    renderTargetDuplicatePhotos(files, container, hash) {
        if (!files || files.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>没有重复照片可显示</p>
                </div>
            `;
            return;
        }
        
        if (!this.selectedDuplicatePhotos) {
            this.selectedDuplicatePhotos = new Set();
        }
        
        const albumPath = this.targetPath || '';
        
        // 排序：相册中已有的放最左侧
        const sortedFiles = [...files].sort((a, b) => {
            const aPath = typeof a === 'string' ? a : a.path;
            const bPath = typeof b === 'string' ? b : b.path;
            const aIsAlbum = aPath.startsWith(albumPath);
            const bIsAlbum = bPath.startsWith(albumPath);
            if (aIsAlbum && !bIsAlbum) return -1;
            if (!aIsAlbum && bIsAlbum) return 1;
            return 0;
        });
        
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        sortedFiles.forEach((file) => {
            let photo;
            if (typeof file === 'string') {
                photo = {
                    name: file.split('\\').pop().split('/').pop(),
                    path: file,
                    size: 0,
                    isAlbum: file.startsWith(albumPath)
                };
            } else {
                photo = { ...file, isAlbum: (file.path || '').startsWith(albumPath) };
            }
            
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.dataset.path = photo.path;
            photoItem.dataset.isAlbum = photo.isAlbum;
            photoItem.dataset.name = photo.name;
            photoItem.dataset.url = photo.thumbnail_url || photo.url || '';
            photoItem.dataset.size = photo.size || 0;

            // 勾选框
            const checkbox = document.createElement('div');
            checkbox.className = 'photo-checkbox';
            photoItem.appendChild(checkbox);

            // 如果已选择，恢复选中样式
            if (this.selectedDuplicatePhotos.has(photo.path)) {
                photoItem.classList.add('selected');
            }
            
            // 相册/导入标记
            const badge = document.createElement('span');
            badge.className = photo.isAlbum ? 'album-badge' : 'import-badge';
            badge.textContent = photo.isAlbum ? '📚 相册' : '📥 导入';
            
            photoItem.appendChild(this._createPhotoImage(photo));
            photoItem.appendChild(badge);
            
            const name = document.createElement('div');
            name.className = 'photo-name';
            name.textContent = photo.name;
            name.title = photo.name;
            
            const pathInfo = document.createElement('div');
            pathInfo.className = 'photo-path';
            pathInfo.textContent = photo.path;
            pathInfo.title = photo.path;
            
            photoItem.appendChild(name);
            photoItem.appendChild(pathInfo);
            
            grid.appendChild(photoItem);
        });
        
        container.innerHTML = '';
        container.appendChild(grid);

        // 接入 PhotoSelection（只创建一次，复用实例以保留选中状态）
        if (window.PhotoSelection) {
            if (!this._targetDupSelection) {
                // 只在首次创建 PhotoSelection
                this._targetDupSelection = new PhotoSelection({
                    onPreview: (photoData) => {
                        this.previewPhoto({
                            name: photoData.name,
                            path: photoData.path,
                            thumbnail_url: photoData.thumbnail_url,
                            url: photoData.url,
                            size: photoData.size
                        });
                    },
                    onSelectionChange: (selectedPaths) => {
                        // 同步到 selectedDuplicatePhotos
                        // 只更新本次渲染的文件路径，保留其他已选
                        sortedFiles.forEach(f => {
                            const p = typeof f === 'string' ? f : f.path;
                            if (selectedPaths.has(p)) {
                                this.selectedDuplicatePhotos.add(p);
                            } else {
                                this.selectedDuplicatePhotos.delete(p);
                            }
                        });
                        // 更新删除按钮状态
                        const clearBtn = document.getElementById('btn-clear-selection');
                        if (clearBtn) clearBtn.disabled = this.selectedDuplicatePhotos.size === 0;
                        this.updateDuplicatesStats();
                    }
                });
            } else {
                // 复用已有实例，只需更新 onSelectionChange 回调（闭包引用最新的 sortedFiles）
                this._targetDupSelection.onSelectionChange = (selectedPaths) => {
                    sortedFiles.forEach(f => {
                        const p = typeof f === 'string' ? f : f.path;
                        if (selectedPaths.has(p)) {
                            this.selectedDuplicatePhotos.add(p);
                        } else {
                            this.selectedDuplicatePhotos.delete(p);
                        }
                    });
                    const clearBtn = document.getElementById('btn-clear-selection');
                    if (clearBtn) clearBtn.disabled = this.selectedDuplicatePhotos.size === 0;
                    this.updateDuplicatesStats();
                };
            }
            this._targetDupSelection.attachToGrid(grid, {
                getPhoto: (item) => ({
                    name: item.dataset.name || '',
                    path: item.dataset.path || '',
                    thumbnail_url: item.querySelector('img.photo-image')?.src || '',
                    url: item.dataset.url || '',
                    size: Number(item.dataset.size) || 0
                })
            });
        }
    }
    
    /**
     * 渲染重复照片
     */
    renderDuplicatePhotos(files, container) {
        if (!files || files.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>没有重复照片可显示</p>
                </div>
            `;
            return;
        }
        
        // 创建照片网格
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        files.forEach(filePath => {
            // 判断filePath是字符串还是对象
            let photo;
            if (typeof filePath === 'string') {
                // 如果是字符串，说明是文件路径
                photo = {
                    name: filePath.split('\\').pop().split('/').pop(), // 兼容Windows和Unix路径
                    path: filePath,
                    size: 0  // 这里没有实际的文件大小信息
                };
            } else {
                // 如果是对象，直接使用
                photo = filePath;
            }
            
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            
            photoItem.appendChild(this._createPhotoImage(photo));
            
            const name = document.createElement('div');
            name.className = 'photo-name';
            name.textContent = photo.name;
            name.title = photo.name;
            
            photoItem.appendChild(name);
            
            // 添加点击事件（可以扩展为查看大图等功能）
            photoItem.addEventListener('click', () => {
                this.previewPhoto(photo);
            });
            
            // 添加双击事件（打开照片）
            photoItem.addEventListener('dblclick', () => {
                this.openPhoto(photo);
            });
            
            grid.appendChild(photoItem);
        });
        
        // 清空容器并添加照片网格
        container.innerHTML = '';
        container.appendChild(grid);
    }
    
    /**
     * 创建照片图片元素（有缩略图时显示图片，否则显示骨架屏占位）
     * @param {object} photo - 照片对象，需含 thumbnail_url / name 字段
     * @returns {HTMLElement} wrapper div
     */
    _createPhotoImage(photo) {
        const wrapper = document.createElement('div');
        wrapper.className = 'photo-image-wrapper';

        if (photo.thumbnail_url) {
            const img = document.createElement('img');
            img.className = 'photo-image';
            img.alt = photo.name || '';
            img.src = photo.thumbnail_url;
            // 加载失败时降级为骨架屏
            img.onerror = () => {
                img.replaceWith(this._createSkeleton());
            };
            wrapper.appendChild(img);
        } else {
            wrapper.appendChild(this._createSkeleton());
        }
        return wrapper;
    }

    /**
     * 创建骨架屏占位块（带 shimmer 动画）
     * @returns {HTMLElement}
     */
    _createSkeleton() {
        const el = document.createElement('div');
        el.className = 'photo-image photo-skeleton skeleton';
        return el;
    }

    /**
     * 初始化Tab导航功能
     */
    initTabNavigation() {
        const tabBtns = this.dialog.querySelectorAll('.tab-btn');
        const tabPanes = this.dialog.querySelectorAll('.tab-pane');
        
        // 移除之前的事件监听
        tabBtns.forEach(btn => {
            btn.removeEventListener('click', this.handleTabClick);
        });
        
        // 添加新的事件监听
        this.handleTabClick = (e) => {
            const targetTab = e.target.dataset.tab;
            
            // 更新按钮状态
            tabBtns.forEach(btn => {
                btn.classList.remove('active');
            });
            e.target.classList.add('active');
            
            // 更新内容显示
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
            });
            const targetPane = document.getElementById(targetTab);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        };
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', this.handleTabClick);
        });
    }
    
    /**
     * 更新按日期查看的tab内容
     */
    updateDateFoldersTab(data) {
        console.log('updateDateFoldersTab called with data:', data);
        
        // 更新基本信息
        const infoContainer = this.dialog.querySelector('#date-folders .preview-info');
        console.log('infoContainer found:', infoContainer);
        if (infoContainer) {
            infoContainer.innerHTML = `
                <p><strong>源路径：</strong> ${data.source_path}</p>
                <p><strong>媒体文件数：</strong> ${data.media_count}</p>
                <p><strong>总大小：</strong> ${data.total_size_mb} MB</p>
            `;
            console.log('Updated infoContainer content');
        }
        
        // 更新日期文件夹列表
        const foldersList = this.dialog.querySelector('#date-folders .date-folders-list');
        console.log('foldersList found:', foldersList);
        if (foldersList) {
            if (data.date_folders && data.date_folders.length > 0) {
                console.log('date_folders data available:', data.date_folders);
                let html = '';
                for (const folder of data.date_folders) {
                    html += `
                        <div class="date-folder-item">
                            <div class="date-folder-name">${folder.name}</div>
                            <div class="date-folder-count">${folder.count} 个文件</div>
                        </div>
                    `;
                }
                foldersList.innerHTML = html;
                console.log('Updated foldersList with date folders');
            } else {
                // 如果没有日期文件夹数据，显示默认文件列表
                foldersList.innerHTML = '<div class="empty-state"><p>📁 没有按日期组织的文件夹</p></div>';
                console.log('Updated foldersList with empty state');
            }
        }
    }
    
    /**
     * 更新目标重复文件的tab内容
     */
    updateTargetDuplicatesTab(data) {
        const infoContainer = this.dialog.querySelector('#target-duplicates .duplicates-info');
        const listContainer = this.dialog.querySelector('#target-duplicates .duplicates-list');
        
        if (infoContainer) {
            const duplicateCount = data.target_duplicates ? Object.keys(data.target_duplicates).length : 0;
            infoContainer.innerHTML = `
                <p><strong>目标重复文件组：</strong> ${duplicateCount} 组</p>
                <p><strong>将跳过的文件数：</strong> ${data.skipped_files || 0}</p>
            `;
        }
        
        if (listContainer) {
            if (data.target_duplicates && Object.keys(data.target_duplicates).length > 0) {
                let html = '';
                for (const [hash, files] of Object.entries(data.target_duplicates)) {
                    const srcFile = files[files.length - 1];
                    const fileName = srcFile ? srcFile.name : hash.slice(0, 8);
                    const safeFileName = this._escapeHtml(fileName);
                    html += `
                        <div class="duplicate-item" data-hash="${this._escapeHtml(hash)}">
                            <div class="duplicate-name" title="${safeFileName}">📷 ${safeFileName}</div>
                            <div class="duplicate-count">与相册中文件重复</div>
                        </div>
                    `;
                }
                listContainer.innerHTML = html;
            } else {
                listContainer.innerHTML = '<div class="empty-state"><p>✅ 没有发现目标重复文件</p></div>';
            }
        }
    }
    
    /**
     * 更新源重复文件的tab内容
     */
    updateSourceDuplicatesTab(data) {
        const infoContainer = this.dialog.querySelector('#source-duplicates .source-duplicates-info');
        const listContainer = this.dialog.querySelector('#source-duplicates .source-duplicates-list');
        
        if (infoContainer) {
            const sourceDuplicateCount = data.source_duplicates ? Object.keys(data.source_duplicates).length : 0;
            infoContainer.innerHTML = `
                <p><strong>文件夹内重复：</strong> ${sourceDuplicateCount} 组</p>
            `;
        }
        
        if (listContainer) {
            if (data.source_duplicates && Object.keys(data.source_duplicates).length > 0) {
                let html = '';
                for (const [hash, files] of Object.entries(data.source_duplicates)) {
                    const f = files[0];
                    const p = f ? (typeof f === 'string' ? f : (f.path || f.name || '')) : '';
                    const firstName = p.split(/[\\\/]/).pop() || hash.slice(0, 8);
                    const safeFirstName = this._escapeHtml(firstName);
                    html += `
                        <div class="duplicate-item">
                            <div class="duplicate-name" title="${safeFirstName}">📷 ${safeFirstName}</div>
                            <div class="duplicate-files">
                                ${files.map(file => `
                                    <div class="duplicate-file">
                                        <span>📁 ${this._escapeHtml(typeof file === 'string' ? file : (file.path || file.name || ''))}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
                listContainer.innerHTML = html;
            } else {
                listContainer.innerHTML = '<div class="empty-state"><p>✅ 没有发现源重复文件</p></div>';
            }
        }
    }

    /**
     * 开始导入 - 先弹出模式选择弹窗
     */
    startImport() {
        if (!this.sourcePath || !this.targetPath) {
            alert('源路径或目标路径未设置');
            return;
        }
        this._showImportModeDialog();
    }

    /**
     * 显示导入模式选择弹窗
     * @returns {void}
     */
    _showImportModeDialog() {
        const modeDialog = document.getElementById('import-mode-dialog');
        if (!modeDialog) return;

        modeDialog.style.display = 'flex';

        const copyBtn = document.getElementById('import-mode-copy');
        const moveBtn = document.getElementById('import-mode-move');
        const cancelBtn = document.getElementById('import-mode-cancel');

        const close = () => {
            modeDialog.style.display = 'none';
            if (copyBtn) copyBtn.removeEventListener('click', onCopy);
            if (moveBtn) moveBtn.removeEventListener('click', onMove);
            if (cancelBtn) cancelBtn.removeEventListener('click', onCancel);
        };

        const onCopy = () => { close(); this._executeImport('copy'); };
        const onMove = () => { close(); this._executeImport('move'); };
        const onCancel = () => { close(); };

        if (copyBtn) copyBtn.addEventListener('click', onCopy);
        if (moveBtn) moveBtn.addEventListener('click', onMove);
        if (cancelBtn) cancelBtn.addEventListener('click', onCancel);

        // ESC 键关闭
        const onKey = (e) => {
            if (e.key === 'Escape') {
                close();
                document.removeEventListener('keydown', onKey);
            }
        };
        document.addEventListener('keydown', onKey);

        // 点击背景关闭
        modeDialog.addEventListener('click', (e) => {
            if (e.target === modeDialog) close();
        }, { once: true });
    }

    /**
     * 实际执行导入
     * @param {'copy'|'move'} mode - 导入模式
     */
    async _executeImport(mode) {
        // 防止重复导入
        if (this._isImporting) {
            console.warn('[ImportDialog] 导入已在进行中，忽略重复请求');
            return;
        }
        this._isImporting = true;
        this.importMode = mode;
        // 重置导入结束标志
        this._importEnded = false;
        try {
            // 获取跳过源重复文件的选项（从导入模式弹窗）
            const skipSourceDuplicatesCheckbox = document.getElementById('skip-source-duplicates-mode');
            const skipSourceDuplicates = skipSourceDuplicatesCheckbox ? skipSourceDuplicatesCheckbox.checked : false;
            
            // 获取跳过相册重复文件的选项（从导入模式弹窗）
            const skipTargetDuplicatesCheckbox = document.getElementById('skip-target-duplicates-mode');
            const skipTargetDuplicates = skipTargetDuplicatesCheckbox ? skipTargetDuplicatesCheckbox.checked : false;
            
            console.log('[_executeImport] 复选框状态:', {
                skipSourceDuplicatesCheckbox: skipSourceDuplicatesCheckbox ? 'found' : 'not found',
                skipSourceDuplicates: skipSourceDuplicates,
                skipTargetDuplicatesCheckbox: skipTargetDuplicatesCheckbox ? 'found' : 'not found',
                skipTargetDuplicates: skipTargetDuplicates
            });
            
            const result = await API.startImport(this.sourcePath, this.targetPath, this.importMode, skipSourceDuplicates, skipTargetDuplicates);
            
            if (result.status === 'started') {
                this.currentImportId = result.import_id;
                this.moveToStep3();
                this.startProgressPolling();
            }
        } catch (error) {
            alert(`启动导入失败: ${error.message}`);
            this._isImporting = false;  // 重置导入中标志
        }
    }


    /**
     * 移到第二步（预览文件）
     */
    moveToStep2() {
        const step1 = this.dialog.querySelector('.import-step-1');
        const step2 = this.dialog.querySelector('.import-step-2');
        const step3 = this.dialog.querySelector('.import-step-3');
        const modalContent = this.dialog.querySelector('.modal-content');

        if (step1) step1.style.display = 'none';
        if (step2) step2.style.display = 'block';
        if (step3) step3.style.display = 'none';
        if (modalContent) modalContent.style.maxWidth = '';
        
        console.log('[moveToStep2] ✅ 回到预览步骤');
    }

    /**
     * 移到第三步（进度显示）
     */
    moveToStep3() {
        const step2 = this.dialog.querySelector('.import-step-2');
        const step3 = this.dialog.querySelector('.import-step-3');
        const modalContent = this.dialog.querySelector('.modal-content');

        if (step2) step2.style.display = 'none';
        if (step3) step3.style.display = 'block';
        if (modalContent) modalContent.style.maxWidth = '720px';
    }

    /**
     * 启动进度轮询
     */
    startProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(() => {
            this.updateProgress();
        }, 500); // 每 500ms 更新一次
    }

    /**
     * 更新进度
     */
    async updateProgress() {
        if (!this.currentImportId) {
            return;
        }

        try {
            const progress = await API.getImportProgress(this.currentImportId);
            this.renderProgress(progress);

            // 如果导入完成或失败，停止轮询
            if (progress.status === 'completed' || progress.status === 'failed' || progress.status === 'cancelled') {
                clearInterval(this.progressInterval);
                this.progressInterval = null;
                
                // 标记导入已结束，用于控制按钮显示
                this._importEnded = true;
                this._isImporting = false;  // 重置导入中标志

                // 导入完成后发送 Windows 桌面通知和弹窗提示
                if (progress.status === 'completed') {
                    this._sendImportToast(progress);
                    this._showImportCompletionDialog(progress);
                } else if (progress.status === 'failed') {
                    this._showImportFailureDialog(progress);
                }
                
                // 触发一次观察器更新，隐藏按钮
                this._triggerButtonVisibilityUpdate();
            }
        } catch (error) {
            console.error('获取进度失败:', error);
        }
    }

    /**
     * 发送导入完成的桌面通知（通过 PyWebView API）
     * 非 PyWebView 环境（浏览器调试模式）下静默降级
     */
    _sendImportToast(progress) {
        try {
            if (!window.pywebview || !window.pywebview.api) return;
            const imported = progress.processed_files || 0;
            const skipped  = progress.skipped_files || 0;
            const failed   = progress.failed_files  || 0;
            const totalSize = progress.total_size_mb || 0;
            const elapsedTime = progress.elapsed_time || 0;
            
            // 构建通知标题和内容
            const title = failed > 0 ? 'FrameAlbum 导入完成（有失败）' : 'FrameAlbum 导入完成';
            const parts = [`✅ 已导入 ${imported} 个文件`];
            if (totalSize > 0) parts.push(`📦 ${totalSize.toFixed(1)} MB`);
            if (skipped > 0) parts.push(`⏭️ 跳过 ${skipped} 个重复`);
            if (failed  > 0) parts.push(`❌ 失败 ${failed} 个`);
            if (elapsedTime > 0) parts.push(`⏱️ 耗时 ${elapsedTime} 秒`);
            
            window.pywebview.api.send_toast(title, parts.join('\n'));
        } catch (e) {
            console.warn('[Toast] 发送通知失败（非致命）:', e);
        }
    }

    /**
     * 显示导入完成的 Toast 提示（简化版）
     */
    _showImportCompletionDialog(progress) {
        const imported = progress.processed_files || 0;
        const skipped  = progress.skipped_files || 0;
        const failed   = progress.failed_files  || 0;
        const elapsedTime = progress.elapsed_time || 0;
        
        // 显示 Toast 通知
        if (window.app && window.app.showNotification) {
            let toastMsg = `成功导入 ${imported} 个文件`;
            if (skipped > 0) toastMsg += `，跳过 ${skipped} 个重复`;
            if (failed > 0) toastMsg += `，${failed} 个失败`;
            toastMsg += `，耗时 ${elapsedTime} 秒`;
            window.app.showNotification(toastMsg, 'success', 5000);
        }
    }

    /**
     * 显示导入失败的 Toast 提示（简化版）
     */
    _showImportFailureDialog(progress) {
        const errorMessage = progress.error_message || '未知错误';
        
        // 显示错误 Toast 通知
        if (window.app && window.app.showError) {
            window.app.showError(`导入失败: ${errorMessage}`);
        }
        
        // 发送系统通知（如果可用）
        try {
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.send_toast('FrameAlbum 导入失败', `❌ 错误: ${errorMessage}`);
            }
        } catch (e) {
            console.warn('[Toast] 发送失败通知失败（非致命）:', e);
        }
    }

    /**
     * 更新按钮可见性
     */
    updateButtonVisibility() {
        console.log('[updateButtonVisibility] 更新按钮可见性');
        
        const step1 = this.dialog.querySelector('.import-step-1');
        const step2 = this.dialog.querySelector('.import-step-2');
        const step3 = this.dialog.querySelector('.import-step-3');
        
        const selectPathBtn = document.getElementById('select-source-path');
        const startImportBtn = document.getElementById('start-import-btn');
        const cancelImportBtn = document.getElementById('cancel-import-btn');
        const pauseImportBtn = document.getElementById('pause-import-btn');
        
        if (step1 && step1.style.display !== 'none') {
            // 第一步：显示"确认"按钮
            if (selectPathBtn) selectPathBtn.style.display = 'block';
            if (startImportBtn) startImportBtn.style.display = 'none';
            if (cancelImportBtn) cancelImportBtn.style.display = 'none';
            if (pauseImportBtn) pauseImportBtn.style.display = 'none';
        } else if (step2 && step2.style.display !== 'none') {
            // 第二步：显示"开始导入"按钮
            if (selectPathBtn) selectPathBtn.style.display = 'none';
            if (startImportBtn) startImportBtn.style.display = 'block';
            if (cancelImportBtn) cancelImportBtn.style.display = 'none';
            if (pauseImportBtn) pauseImportBtn.style.display = 'none';
        } else if (step3 && step3.style.display !== 'none') {
            // 第三步：显示"取消导入"和"暂停"按钮
            if (selectPathBtn) selectPathBtn.style.display = 'none';
            if (startImportBtn) startImportBtn.style.display = 'none';
            if (cancelImportBtn) cancelImportBtn.style.display = 'block';
            if (pauseImportBtn) pauseImportBtn.style.display = 'block';
        } else {
            // 默认显示"确认"按钮
            if (selectPathBtn) selectPathBtn.style.display = 'block';
            if (startImportBtn) startImportBtn.style.display = 'none';
            if (cancelImportBtn) cancelImportBtn.style.display = 'none';
        }
        
        console.log('[updateButtonVisibility] ✅ 按钮更新完成');
    }

    /**
     * 渲染进度信息
     */
    renderProgress(progress) {
        const progressContainer = this.dialog.querySelector('.import-progress');
        if (!progressContainer) return;

        const statusMap = {
            pending: '等待中...',
            scanning: '扫描源目录...',
            processing: '处理中...',
            paused: '⏸ 已暂停',
            completed: '✅ 完成',
            failed: '❌ 失败',
            cancelled: '⏹ 已取消'
        };

        const statusText = statusMap[progress.status] || progress.status;

        let html = `
            <div class="progress-status">
                <div class="status-text">${statusText}</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress.progress}%"></div>
                </div>
                <div class="progress-text">${progress.progress}% - ${progress.processed_files + progress.skipped_files + progress.failed_files}/${progress.total_files} 文件</div>
            </div>

            <div class="progress-details">
                <table class="progress-table">
                    <tr>
                        <td>总文件数：</td>
                        <td>${progress.total_files}</td>
                    </tr>
                    <tr>
                        <td>导入成功：</td>
                        <td>${progress.processed_files}</td>
                    </tr>
                    <tr>
                        <td>跳过：</td>
                        <td>${progress.skipped_files}</td>
                    </tr>
                    <tr>
                        <td>失败：</td>
                        <td>${progress.failed_files}</td>
                    </tr>
                    <tr>
                        <td>总大小：</td>
                        <td>${progress.total_size_mb} MB</td>
                    </tr>
                    <tr>
                        <td>已导入：</td>
                        <td>${progress.processed_size_mb} MB</td>
                    </tr>
                    <tr>
                        <td>耗时：</td>
                        <td>${progress.elapsed_time}s</td>
                    </tr>
                </table>
            </div>

            ${progress.error_message ? `
                <div class="progress-error">
                    <strong>错误：</strong><span class="progress-error-msg"></span>
                </div>
            ` : ''}
        `;

        progressContainer.innerHTML = html;

        // 如果有错误信息，用 textContent 安全注入（防 XSS）
        if (progress.error_message) {
            const errMsgEl = progressContainer.querySelector('.progress-error-msg');
            if (errMsgEl) {
                errMsgEl.textContent = progress.error_message;
            }
        }

        // 根据状态切换暂停按钮文字，导入结束时隐藏暂停和取消按钮
        const pauseBtn = document.getElementById('pause-import-btn');
        const cancelBtn = document.getElementById('cancel-import-btn');
        const endedStatuses = ['completed', 'failed', 'cancelled'];
        
        if (pauseBtn) {
            if (endedStatuses.includes(progress.status)) {
                pauseBtn.style.display = 'none';
            } else {
                pauseBtn.style.display = 'block';
                pauseBtn.textContent = progress.status === 'paused' ? '继续' : '暂停';
            }
        }
        
        // 导入结束时也隐藏取消按钮
        if (cancelBtn && endedStatuses.includes(progress.status)) {
            cancelBtn.style.display = 'none';
        }
    }

    /**
     * 取消当前导入
     */
    async cancelCurrentImport() {
        if (!this.currentImportId) {
            return;
        }

        if (confirm('确认取消导入？')) {
            try {
                await API.cancelImport(this.currentImportId);
                
                // 清理进度轮询
                if (this.progressInterval) {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                }
                
                // 重置导入 ID
                this.currentImportId = null;
                
                // 清理进度显示
                const progressContainer = this.dialog.querySelector('.import-progress');
                if (progressContainer) {
                    progressContainer.innerHTML = '';
                }
                
                // 回到步骤 2
                this.moveToStep2();
                
                // 更新按钮状态
                this.updateButtonVisibility();
                
                console.log('[cancelCurrentImport] ✅ 导入已取消，回到步骤 2');
            } catch (error) {
                alert(`取消导入失败: ${error.message}`);
            }
        }
    }

    /**
     * 暂停/继续当前导入（切换）
     */
    async togglePauseImport() {
        if (!this.currentImportId) return;

        const pauseBtn = document.getElementById('pause-import-btn');
        const isPaused = pauseBtn && pauseBtn.textContent === '继续';

        try {
            if (isPaused) {
                await API.resumeImport(this.currentImportId);
                console.log('[togglePauseImport] ✅ 导入已继续');
            } else {
                await API.pauseImport(this.currentImportId);
                console.log('[togglePauseImport] ✅ 导入已暂停');
            }
        } catch (error) {
            alert(`操作失败: ${error.message}`);
        }
    }
    /**
     * HTML 特殊字符转义（防 XSS）
     * @param {string} str
     * @returns {string}
     */
    _escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}

// DOMContentLoaded 后再初始化（确保 #import-dialog 元素已存在）
document.addEventListener('DOMContentLoaded', () => {
    const importDialog = new ImportDialog();
    importDialog.init();
    window.importDialog = importDialog;
});
