/**
 * 导入对话框模块（模块化版本）
 * 处理导入流程：路径选择 -> 预览 -> 导入 -> 进度显示
 */

import { api } from '../index.js';

export class ImportDialog {
    constructor() {
        this.dialog = null;
        this.sourcePath = null;
        this.targetPath = null;
        this.currentImportId = null;
        this.progressInterval = null;
        this.isCheckingSource = false;
        this.checkCancelled = false;
        this.checkRequestId = 0;
        this.selectedDuplicatePhotos = new Set();
        this.selectedSourceDuplicates = new Set();
        this.importMode = 'copy';
        this.escKeyHandler = null;
    }

    /**
     * 初始化（需在 DOM 解析完成后调用）
     */
    init() {
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
        
        const observer = new MutationObserver(() => {
            const step1 = this.dialog.querySelector('.import-step-1').style.display;
            const step2 = this.dialog.querySelector('.import-step-2').style.display;
            const step3 = this.dialog.querySelector('.import-step-3').style.display;
            
            const selectPathBtn = document.getElementById('select-source-path');
            const startImportBtn = document.getElementById('start-import-btn');
            const cancelImportBtn = document.getElementById('cancel-import-btn');
            const pauseImportBtn = document.getElementById('pause-import-btn');
            
            const isImportEnded = this.currentImportId && this._importEnded;
            
            if (selectPathBtn) selectPathBtn.style.display = step1 !== 'none' ? 'block' : 'none';
            if (startImportBtn) startImportBtn.style.display = step2 !== 'none' ? 'block' : 'none';
            
            if (step3 !== 'none') {
                if (cancelImportBtn) cancelImportBtn.style.display = isImportEnded ? 'none' : 'block';
                if (pauseImportBtn) pauseImportBtn.style.display = isImportEnded ? 'none' : 'block';
            } else {
                if (cancelImportBtn) cancelImportBtn.style.display = 'none';
                if (pauseImportBtn) pauseImportBtn.style.display = 'none';
            }
        });
        
        observer.observe(this.dialog, { subtree: true, attributes: true });
        
        const selectPathBtn = document.getElementById('select-source-path');
        if (selectPathBtn) selectPathBtn.style.display = 'block';
    }

    /**
     * 触发按钮可见性更新
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
        const closeBtn = this.dialog?.querySelector('.close-import-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        const cancelBtn = this.dialog?.querySelector('.cancel-import-dialog');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }

        const browseSourceBtn = this.dialog?.querySelector('#btn-browse-source');
        if (browseSourceBtn) {
            browseSourceBtn.addEventListener('click', () => this.browseSourcePath());
        }

        const selectSourceBtn = this.dialog?.querySelector('#select-source-path');
        if (selectSourceBtn) {
            selectSourceBtn.addEventListener('click', () => this.selectSourcePath());
        }

        const startBtn = document.getElementById('start-import-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startImport());
        }

        const cancelImportBtn = document.getElementById('cancel-import-btn');
        if (cancelImportBtn) {
            cancelImportBtn.addEventListener('click', () => this.cancelCurrentImport());
        }

        const pauseImportBtn = document.getElementById('pause-import-btn');
        if (pauseImportBtn) {
            pauseImportBtn.addEventListener('click', () => this.togglePauseImport());
        }
    }

    /**
     * 打开对话框
     */
    async open(targetPath) {
        this.sourcePath = null;
        this.resetUI();

        if (!targetPath) {
            try {
                const config = await api.settings.getAlbumPath();
                targetPath = config && config.album_path ? config.album_path : null;
            } catch (e) {
                console.warn('[ImportDialog] 获取相册路径失败，targetPath 将为 null', e);
                targetPath = null;
            }
        }
        this.targetPath = targetPath;
        
        this.dialog.style.display = 'flex';
        this.dialog.setAttribute('aria-hidden', 'false');
        
        const modalContent = this.dialog.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.maxWidth = '600px';
        }
        
        this.bindKeyboardEvents();
        this.focusFirstInteractiveElement();
        document.body.style.overflow = 'hidden';
    }

    /**
     * 关闭对话框
     */
    close() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        this.isCheckingSource = false;
        this.checkCancelled = false;
        
        this.dialog.style.display = 'none';
        this.dialog.setAttribute('aria-hidden', 'true');
        
        this.unbindKeyboardEvents();
        document.body.style.overflow = 'auto';
    }
    
    /**
     * 绑定键盘事件
     */
    bindKeyboardEvents() {
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
        const step1 = this.dialog.querySelector('.import-step-1');
        const step2 = this.dialog.querySelector('.import-step-2');
        const step3 = this.dialog.querySelector('.import-step-3');

        if (step1) step1.style.display = 'block';
        if (step2) step2.style.display = 'none';
        if (step3) step3.style.display = 'none';

        const sourcePathInput = this.dialog.querySelector('#source-path-input');
        if (sourcePathInput) sourcePathInput.value = '';

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
            if (window.pywebview && window.pywebview.api) {
                console.log('使用 PyWebView API 选择源文件夹...');
                const path = await window.pywebview.api.select_folder();
                
                if (path && typeof path === 'string' && path.trim()) {
                    console.log('选择的源路径:', path);
                    const pathInput = this.dialog.querySelector('#source-path-input');
                    if (pathInput) {
                        pathInput.value = path;
                    }
                } else {
                    console.log('用户取消了文件夹选择');
                }
            } else {
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
            const result = await api.importApi.checkImportPath(sourcePath, (progress, progressData) => {
                if (!this.isCheckingSource || this.checkCancelled || requestId !== this.checkRequestId) return;
                
                const progressBar = document.getElementById('step1-progress-bar');
                if (progressBar) {
                    const percentage = Math.round(progress * 100);
                    progressBar.style.width = `${percentage}%`;
                    progressBar.setAttribute('aria-valuenow', percentage);
                }
                
                const progressPercentage = document.getElementById('step1-progress-percentage');
                if (progressPercentage) {
                    const percentage = Math.round(progress * 100);
                    progressPercentage.textContent = `${percentage}%`;
                }

                this.updateStep1ProgressStatus(progressData);
            }, () => this.checkCancelled || requestId !== this.checkRequestId || !this.isCheckingSource);
            
            if (this.checkCancelled || requestId !== this.checkRequestId) {
                console.log('[selectSourcePath] 检查结果已忽略（已取消或过期请求）');
                return;
            }
            
            if (result.status === 'valid') {
                this.sourcePath = result.source_path;
                this.moveToStep2();
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
     * 移动到步骤2
     */
    moveToStep2() {
        const step1 = this.dialog.querySelector('.import-step-1');
        const step2 = this.dialog.querySelector('.import-step-2');
        if (step1) step1.style.display = 'none';
        if (step2) step2.style.display = 'block';
    }

    /**
     * 显示预览
     */
    showPreview(data) {
        this.previewData = data;
        
        const step2 = this.dialog.querySelector('.import-step-2');
        if (step2) {
            const targetDupCount = data.target_duplicates ? Object.keys(data.target_duplicates).length : 0;
            const sourceDupCount = data.source_duplicates ? Object.keys(data.source_duplicates).length : 0;
            const dateFolderCount = data.date_folders ? data.date_folders.length : 0;

            step2.innerHTML = `
                <h3>步骤 2: 预览文件</h3>
                <div class="file-preview" aria-live="polite">
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
                    
                    <div class="tab-nav">
                        <button class="tab-btn active" data-tab="date-folders">📅 时间线 <span class="tab-badge">${dateFolderCount}</span></button>
                        <button class="tab-btn" data-tab="target-duplicates">⚠️ 已在相册${targetDupCount > 0 ? ` <span class="tab-badge tab-badge--warn">${targetDupCount}</span>` : ''}</button>
                        <button class="tab-btn" data-tab="source-duplicates">🗂 文件夹内重复${sourceDupCount > 0 ? ` <span class="tab-badge tab-badge--warn">${sourceDupCount}</span>` : ''}</button>
                    </div>
                    
                    <div class="tab-content">
                        <div class="tab-pane active" id="date-folders">
                            <p class="tab-hint">按拍摄日期浏览待导入的照片，确认内容无误后点击「开始导入」。</p>
                            <div class="duplicates-info timeline-actions-bar">
                                <span><strong>待导入：</strong> ${data.media_count} 个文件</span>
                                <div class="duplicates-actions">
                                    <button class="btn btn-sm btn-danger-ghost" id="btn-delete-timeline-selected" disabled title="删除选中的文件（从源文件夹）">🗑 删除所选</button>
                                </div>
                            </div>
                            <div class="date-view-container">
                                <div class="date-filter-panel">
                                    <h4>日期筛选</h4>
                                    <div class="date-filter-list">
                                        ${data.date_folders && data.date_folders.length > 0 ?
                                            data.date_folders.map(folder => {
                                                const safeName = this._escapeHtml(folder.name);
                                                return `
                                                <div class="date-filter-item" data-date="${safeName}">
                                                    <div class="date-filter-name">${safeName}</div>
                                                    <div class="date-filter-count">${folder.count} 个文件</div>
                                                </div>`;
                                            }).join('') :
                                            '<div class="empty-state"><p>没有按日期组织的文件夹</p></div>'
                                        }
                                    </div>
                                </div>
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
                                <div class="duplicates-list-panel">
                                    <h4>重复文件组</h4>
                                    <div class="duplicates-list">
                                        ${sourceDupCount > 0 ? 
                                            Object.entries(data.source_duplicates).map(([hash, files]) => {
                                                const f = files[0];
                                                const p = f ? (typeof f === 'string' ? f : (f.path || f.name || '')) : '';
                                                const firstName = p.split(/[\/]/).pop() || hash.slice(0, 8);
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
            
            this.bindTabEvents();
            this.bindDateFilterEvents();
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
                    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
                    
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
                dateFilterItems.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                
                const selectedDate = item.dataset.date;
                const selectedDateFolder = this.previewData.date_folders.find(folder => folder.name === selectedDate);
                
                if (selectedDateFolder && selectedDateFolder.files) {
                    this.renderPhotosGrid(selectedDateFolder.files, photosContainer);
                } else {
                    photosContainer.innerHTML = `
                        <div class="empty-state">
                            <p>该日期没有照片</p>
                        </div>
                    `;
                }
            });
        });

        const firstItem = this.dialog.querySelector('.date-filter-item');
        if (firstItem) firstItem.click();
    }
    
    /**
     * 渲染照片网格
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

        if (window.PhotoSelection) {
            if (this._timelineSelection) {
                this._timelineSelection.exitSelectionMode();
            }
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
     * 创建照片图像元素
     */
    _createPhotoImage(photo) {
        const img = document.createElement('img');
        img.src = photo.thumbnail_url || photo.url;
        img.alt = photo.name;
        img.className = 'photo-image';
        img.loading = 'lazy';
        return img;
    }
    
    /**
     * 预览照片
     */
    previewPhoto(photo) {
        const modal = document.getElementById('photo-preview-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
        
        const previewImage = document.getElementById('preview-image');
        const previewTitle = document.getElementById('preview-title');
        const previewName = document.getElementById('preview-name');
        const previewSize = document.getElementById('preview-size');
        const previewPath = document.getElementById('preview-path');
        
        if (previewImage) {
            previewImage.src = photo.thumbnail_url || photo.url;
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
        
        if (!window.app) {
            window.app = {};
        }
        window.app.currentPreviewPhoto = photo;
        
        this.bindPreviewModalEvents();
    }
    
    /**
     * 绑定预览模态框事件
     */
    bindPreviewModalEvents() {
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
        
        const openBtn = document.getElementById('open-file-btn');
        if (openBtn) {
            openBtn.onclick = () => {
                if (window.app && window.app.currentPreviewPhoto) {
                    this.openPhoto(window.app.currentPreviewPhoto);
                }
            };
        }
        
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
        
        if (window.app) {
            window.app.currentPreviewPhoto = null;
        }
    }
    
    /**
     * 打开照片
     */
    openPhoto(photo) {
        try {
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
                        alert(`照片路径: ${photo.path}\n\n请手动打开此文件。`);
                    });
            } else {
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
        const targetDuplicateItems = this.dialog.querySelectorAll('#target-duplicates .duplicate-item');
        const targetPreviewContainer = document.getElementById('target-duplicates-preview');
        
        targetDuplicateItems.forEach(item => {
            item.addEventListener('click', (e) => {
                targetDuplicateItems.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                
                const selectedHash = item.dataset.hash;
                const duplicateFiles = this.previewData.target_duplicates[selectedHash];
                
                if (duplicateFiles) {
                    this.renderTargetDuplicatePhotos(duplicateFiles, targetPreviewContainer, selectedHash);
                } else {
                    targetPreviewContainer.innerHTML = `
                        <div class="empty-state">
                            <p>该重复文件组没有文件</p>
                        </div>
                    `;
                }
            });
        });
        
        const sourceDuplicateItems = this.dialog.querySelectorAll('#source-duplicates .duplicate-item');
        const sourcePreviewContainer = document.getElementById('source-duplicates-preview');
        
        sourceDuplicateItems.forEach(item => {
            item.addEventListener('click', (e) => {
                sourceDuplicateItems.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                
                const selectedHash = item.dataset.hash;
                const duplicateFiles = this.previewData.source_duplicates[selectedHash];
                
                if (duplicateFiles) {
                    this.renderSourceDuplicatePhotos(duplicateFiles, sourcePreviewContainer, selectedHash);
                } else {
                    sourcePreviewContainer.innerHTML = `
                        <div class="empty-state">
                            <p>该重复文件组没有文件</p>
                        </div>
                    `;
                }
            });
        });
        
        this.bindSelectDuplicatesButton();
        this.bindClearSelectionButton();
        this.bindSelectSourceDuplicatesButton();
        this.bindClearSourceSelectionButton();
        this.bindTimelineDeleteButton();
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
                
                if (this.previewData && this.previewData.target_duplicates) {
                    for (const [hash, files] of Object.entries(this.previewData.target_duplicates)) {
                        files.forEach(file => {
                            let filePath = typeof file === 'string' ? file : (file.path || '');
                            if (!filePath.startsWith(albumPath)) {
                                this.selectedDuplicatePhotos.add(filePath);
                            }
                        });
                    }
                }
                
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
                    if (this._targetDupSelection && this.selectedDuplicatePhotos.size > 0) {
                        this._targetDupSelection.enterSelectionMode();
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

        const allFiles = (this.previewData.date_folders || []).reduce((sum, folder) => sum + (folder.count || 0), 0);
        const totalSize = (this.previewData.date_folders || []).reduce((sum, folder) => sum + (folder.size || 0), 0);
        this.previewData.media_count = allFiles;
    }

    /**
     * 渲染目标重复照片
     */
    renderTargetDuplicatePhotos(files, container, hash) {
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        files.forEach(file => {
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.dataset.path = this._extractPath(file);
            photoItem.dataset.name = typeof file === 'string' ? file.split(/[\/]/).pop() : (file.name || '');
            photoItem.dataset.url = file.url || file.thumbnail_url || '';
            photoItem.dataset.size = file.size || 0;

            const checkbox = document.createElement('div');
            checkbox.className = 'photo-checkbox';
            photoItem.appendChild(checkbox);

            photoItem.appendChild(this._createPhotoImage(file));
            
            const name = document.createElement('div');
            name.className = 'photo-name';
            name.textContent = photoItem.dataset.name;
            name.title = photoItem.dataset.name;
            photoItem.appendChild(name);
            
            grid.appendChild(photoItem);
        });
        
        container.innerHTML = '';
        container.appendChild(grid);
    }

    /**
     * 渲染源重复照片
     */
    renderSourceDuplicatePhotos(files, container, hash) {
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        files.forEach(file => {
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.dataset.path = this._extractPath(file);
            photoItem.dataset.name = typeof file === 'string' ? file.split(/[\/]/).pop() : (file.name || '');
            photoItem.dataset.url = file.url || file.thumbnail_url || '';
            photoItem.dataset.size = file.size || 0;

            const checkbox = document.createElement('div');
            checkbox.className = 'photo-checkbox';
            photoItem.appendChild(checkbox);

            photoItem.appendChild(this._createPhotoImage(file));
            
            const name = document.createElement('div');
            name.className = 'photo-name';
            name.textContent = photoItem.dataset.name;
            name.title = photoItem.dataset.name;
            photoItem.appendChild(name);
            
            grid.appendChild(photoItem);
        });
        
        container.innerHTML = '';
        container.appendChild(grid);
    }

    /**
     * 绑定清除选择按钮
     */
    bindClearSelectionButton() {
        const clearBtn = document.getElementById('btn-clear-selection');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.selectedDuplicatePhotos.clear();
                const previewContainer = document.getElementById('target-duplicates-preview');
                if (previewContainer) {
                    previewContainer.querySelectorAll('.photo-item').forEach(item => {
                        item.classList.remove('selected');
                    });
                }
                clearBtn.disabled = true;
                this.updateDuplicatesStats();
            });
        }
    }

    /**
     * 绑定源重复选择按钮
     */
    bindSelectSourceDuplicatesButton() {
        const selectBtn = document.getElementById('btn-select-source-duplicates');
        const clearBtn = document.getElementById('btn-clear-source-selection');
        
        if (selectBtn) {
            selectBtn.addEventListener('click', () => {
                this.selectedSourceDuplicates = new Set();
                
                if (this.previewData && this.previewData.source_duplicates) {
                    for (const [hash, files] of Object.entries(this.previewData.source_duplicates)) {
                        files.forEach(file => {
                            let filePath = typeof file === 'string' ? file : (file.path || '');
                            this.selectedSourceDuplicates.add(filePath);
                        });
                    }
                }
                
                const previewContainer = document.getElementById('source-duplicates-preview');
                if (previewContainer) {
                    previewContainer.querySelectorAll('.photo-item').forEach(item => {
                        const path = item.dataset.path;
                        if (this.selectedSourceDuplicates.has(path)) {
                            item.classList.add('selected');
                        } else {
                            item.classList.remove('selected');
                        }
                    });
                }
                
                if (clearBtn) {
                    clearBtn.disabled = this.selectedSourceDuplicates.size === 0;
                }
            });
        }
    }

    /**
     * 绑定源重复清除选择按钮
     */
    bindClearSourceSelectionButton() {
        const clearBtn = document.getElementById('btn-clear-source-selection');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.selectedSourceDuplicates.clear();
                const previewContainer = document.getElementById('source-duplicates-preview');
                if (previewContainer) {
                    previewContainer.querySelectorAll('.photo-item').forEach(item => {
                        item.classList.remove('selected');
                    });
                }
                clearBtn.disabled = true;
            });
        }
    }

    /**
     * 绑定时间线删除按钮
     */
    bindTimelineDeleteButton() {
        const deleteBtn = document.getElementById('btn-delete-timeline-selected');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                // 时间线删除功能实现
                this._deleteTimelineSelectedPhotos();
            });
        }
    }

    /**
     * 删除时间线选中的照片
     */
    async _deleteTimelineSelectedPhotos() {
        // 实现删除逻辑
        if (this._timelineSelectedPaths && this._timelineSelectedPaths.size > 0) {
            if (confirm(`确定要删除选中的 ${this._timelineSelectedPaths.size} 个文件吗？`)) {
                // 调用 API 删除文件
                try {
                    const paths = Array.from(this._timelineSelectedPaths);
                    await api.client.post('/files/delete', { paths });
                    // 更新预览数据
                    this.applyDeletedPathsToPreviewData(paths);
                    // 重新渲染
                    this.showPreview(this.previewData);
                } catch (error) {
                    console.error('删除文件失败:', error);
                    alert(`删除失败: ${error.message}`);
                }
            }
        }
    }

    /**
     * 更新重复文件统计
     */
    updateDuplicatesStats() {
        // 更新重复文件统计
    }

    /**
     * 开始导入
     */
    async startImport() {
        try {
            const skipTargetDuplicates = document.getElementById('skip-target-duplicates')?.checked || false;
            const skipSourceDuplicates = document.getElementById('skip-source-duplicates-mode')?.checked || false;
            
            const result = await api.importApi.startImport(
                this.sourcePath,
                this.targetPath,
                this.importMode,
                skipSourceDuplicates,
                skipTargetDuplicates
            );
            
            if (result.import_id) {
                this.currentImportId = result.import_id;
                this.moveToStep3();
                this.startProgressPolling();
            }
        } catch (error) {
            console.error('启动导入失败:', error);
            alert(`启动导入失败: ${error.message}`);
        }
    }

    /**
     * 移动到步骤3
     */
    moveToStep3() {
        const step2 = this.dialog.querySelector('.import-step-2');
        const step3 = this.dialog.querySelector('.import-step-3');
        if (step2) step2.style.display = 'none';
        if (step3) step3.style.display = 'block';
        
        const modalContent = this.dialog.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.maxWidth = '800px';
        }
    }

    /**
     * 开始进度轮询
     */
    startProgressPolling() {
        this.progressInterval = setInterval(async () => {
            try {
                const progress = await api.importApi.getImportProgress(this.currentImportId);
                this.updateImportProgress(progress);
                
                if (progress.status === 'completed' || progress.status === 'failed') {
                    this.stopProgressPolling();
                    this._importEnded = true;
                    this._triggerButtonVisibilityUpdate();
                }
            } catch (error) {
                console.error('获取导入进度失败:', error);
                this.stopProgressPolling();
            }
        }, 1000);
    }

    /**
     * 停止进度轮询
     */
    stopProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    /**
     * 更新导入进度
     */
    updateImportProgress(progress) {
        const container = this.dialog.querySelector('.import-step-3 .import-progress');
        if (container) {
            container.innerHTML = `
                <div class="progress-info">
                    <h4>导入进度</h4>
                    <div class="progress">
                        <div class="progress-bar" style="width: ${progress.progress || 0}%;"></div>
                    </div>
                    <div class="progress-text">${progress.status === 'completed' ? '导入完成' : 
                        progress.status === 'failed' ? '导入失败' : 
                        `正在导入: ${progress.current || 0}/${progress.total || 0} 个文件`}
                    </div>
                    ${progress.error ? `<div class="error-text">错误: ${progress.error}</div>` : ''}
                </div>
            `;
        }
    }

    /**
     * 取消当前导入
     */
    async cancelCurrentImport() {
        if (this.currentImportId) {
            try {
                await api.importApi.cancelImport(this.currentImportId);
                this.stopProgressPolling();
                this.close();
            } catch (error) {
                console.error('取消导入失败:', error);
                alert(`取消导入失败: ${error.message}`);
            }
        }
    }

    /**
     * 切换暂停/继续导入
     */
    async togglePauseImport() {
        if (this.currentImportId) {
            try {
                const pauseBtn = document.getElementById('pause-import-btn');
                if (pauseBtn.textContent === '暂停') {
                    await api.importApi.pauseImport(this.currentImportId);
                    pauseBtn.textContent = '继续';
                } else {
                    await api.importApi.resumeImport(this.currentImportId);
                    pauseBtn.textContent = '暂停';
                }
            } catch (error) {
                console.error('暂停/继续导入失败:', error);
                alert(`操作失败: ${error.message}`);
            }
        }
    }

    /**
     * HTML 转义
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
