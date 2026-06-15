/**
 * 相册浏览器模块（模块化版本）
 * 处理树节点展开/收起、照片加载、目录树渲染等
 */

import { utils, api } from '../index.js';

export class AlbumBrowser {
    constructor() {
        this.currentPath = null;
        this.treeData = null;
        this.photosCache = {};
        this.currentPage = 1;
        this.pageSize = 50;
        this.allPhotos = [];
        this._photoSelection = null;
        this.filterType = 'all';
    }
    
    /**
     * 初始化相册浏览器
     */
    async init() {
        console.log('初始化相册浏览器');
        
        await this.loadTree();
        this.bindEvents();
    }

    /**
     * 加载目录树
     */
    async loadTree() {
        try {
            console.log('加载目录树...');
            const response = await api.album.getAlbumTree();
            
            this.treeData = response;
            if (window.app) {
                window.app.albumTree = response;
            }
            console.log('目录树数据:', response);
            
            if (response.error) {
                console.error('目录树API返回错误:', response.error);
                document.getElementById('tree-container').innerHTML = 
                    '<div class="error">' + response.error + '</div>';
                document.getElementById('photos-container').innerHTML = 
                    '<div class="empty">请先设置相册路径</div>';
                document.getElementById('content-title').textContent = '相册管理';
                return;
            }
            
            this.renderTree(response);
            this.renderYearJumper(response);
            
            if (response.children && response.children.length > 0) {
                const firstWithPhotos = response.children.find(child => child.count > 0);
                const targetNode = firstWithPhotos || response.children[0];
                this.selectNode(targetNode.path, targetNode.name);
            }
        } catch (error) {
            console.error('加载目录树失败:', error);
            document.getElementById('tree-container').innerHTML = 
                '<div class="error">加载目录树失败</div>';
            document.getElementById('photos-container').innerHTML = 
                '<div class="empty">请先设置相册路径</div>';
            document.getElementById('content-title').textContent = 'FrameAlbum';
        }
    }

    /**
     * 渲染目录树（递归，支持任意深度）
     */
    renderTree(data) {
        const container = document.getElementById('tree-container');
        container.innerHTML = '';

        if (!data || !data.children || data.children.length === 0) {
            container.innerHTML = '<div class="empty">📭 相册为空</div>';
            return;
        }

        const sortChildren = (children) => [...children].sort((a, b) => {
            const aHas = (a.count || 0) > 0;
            const bHas = (b.count || 0) > 0;
            if (aHas && !bHas) return -1;
            if (!aHas && bHas) return 1;
            return a.name.localeCompare(b.name);
        });

        const buildNode = (node, depth = 0) => {
            const hasChildren = node.children && node.children.length > 0;

            const li = document.createElement('li');
            li.className = 'tree-item' + (hasChildren ? ' expandable' : ' tree-leaf');

            const content = document.createElement('div');
            content.className = 'tree-item-content';

            const toggle = document.createElement('span');
            toggle.className = 'tree-item-toggle';

            const icon = document.createElement('span');
            icon.className = 'tree-item-icon';

            const label = document.createElement('span');
            label.className = 'tree-item-label';
            label.textContent = node.name;
            label.dataset.path = node.path;
            label.dataset.count = node.count || 0;

            const count = document.createElement('span');
            count.className = 'tree-item-count';
            if ((node.count || 0) > 0) {
                count.textContent = node.count;
            }

            content.appendChild(toggle);
            content.appendChild(icon);
            content.appendChild(label);
            content.appendChild(count);
            li.appendChild(content);

            content.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectNode(node.path, node.name);
            });

            if (hasChildren) {
                const childList = document.createElement('ul');
                childList.className = 'tree-children';

                if (depth <= 1) {
                    li.classList.add('expanded');
                }

                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleNode(li);
                });

                sortChildren(node.children).forEach(child => {
                    childList.appendChild(buildNode(child, depth + 1));
                });

                li.appendChild(childList);
            }

            return li;
        };

        const rootList = document.createElement('ul');
        rootList.className = 'tree-list';

        const rootNode = buildNode(data, 0);
        if (rootNode) {
            rootNode.classList.add('expanded');
            rootList.appendChild(rootNode);
        }

        container.appendChild(rootList);
    }

    /**
     * 选中节点
     */
    async selectNode(path, name) {
        console.log('选中节点:', path, name);
        
        this.currentPath = path;
        
        document.querySelectorAll('.tree-item').forEach(item => {
            item.classList.remove('selected');
            const label = item.querySelector('.tree-item-label');
            if (label && label.dataset.path === path) {
                item.classList.add('selected');
            }
        });
        
        const contentTitle = document.getElementById('content-title');
        if (contentTitle) contentTitle.textContent = name;
        
        await this.loadPhotos(path);
    }

    /**
     * 加载照片列表
     */
    async loadPhotos(path) {
        try {
            console.log('加载照片:', path);
            
            this.filterType = 'all';
            this._syncFilterButtons();

            if (this.photosCache[path]) {
                this.allPhotos = this.photosCache[path];
                this.currentPage = 1;
                this.renderPhotosWithPagination();
                this._updateFilterGroupVisibility();
                return;
            }
            
            const container = document.getElementById('photos-container');
            container.innerHTML = '<div class="loading">加载中...</div>';
            
            const response = await api.album.getPhotos(path);
            const photos = response.photos || [];
            console.log('获取到照片:', photos.length, '张');
            
            this.photosCache[path] = photos;
            this.allPhotos = photos;
            this.currentPage = 1;
            
            this.renderPhotosWithPagination();
            this._updateFilterGroupVisibility();
        } catch (error) {
            console.error('加载照片失败:', error);
            document.getElementById('photos-container').innerHTML = 
                '<div class="error">加载照片失败</div>';
        }
    }

    /**
     * 构建照片卡片 DOM
     */
    _buildPhotoCard(photo) {
        const item = document.createElement('div');
        item.className = 'photo-item';
        item.dataset.path = photo.path || '';
        item.dataset.name = photo.name || '';
        item.dataset.url = photo.url || photo.thumbnail_url || '';
        item.dataset.size = photo.size || 0;

        const checkbox = document.createElement('div');
        checkbox.className = 'photo-checkbox';
        item.appendChild(checkbox);

        const img = document.createElement('img');
        img.src = photo.thumbnail_url || photo.url;
        img.alt = photo.name;
        img.className = 'photo-image';
        img.loading = 'lazy';
        img.onerror = () => {
            img.onerror = null;
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'photo-error-placeholder';
            const isVideo = photo.type === 'video';
            placeholder.innerHTML = `<span>${isVideo ? '🎬' : '🖼'}</span><small>${isVideo ? '视频' : '图片加载失败'}</small>`;
            item.insertBefore(placeholder, img.nextSibling);
        };

        item.appendChild(img);

        if (photo.type === 'video') {
            const badge = document.createElement('div');
            badge.className = 'photo-type-badge';
            badge.textContent = '🎬 视频';
            item.appendChild(badge);
        }

        const overlay = document.createElement('div');
        overlay.className = 'photo-hover-overlay';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'photo-hover-name';
        nameSpan.textContent = photo.name;
        nameSpan.title = photo.name;
        overlay.appendChild(nameSpan);

        if (photo.size) {
            const sizeSpan = document.createElement('span');
            sizeSpan.className = 'photo-hover-size';
            const kb = Math.round(photo.size / 1024);
            sizeSpan.textContent = kb >= 1024 ? (kb / 1024).toFixed(1) + ' MB' : kb + ' KB';
            overlay.appendChild(sizeSpan);
        }

        item.appendChild(overlay);

        item.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this._showContextMenu(e, photo, item);
        });

        return item;
    }

    /**
     * 渲染照片网格（带分页功能）
     */
    renderPhotosWithPagination() {
        const container = document.getElementById('photos-container');
        const btnQuickDelete = document.getElementById('btn-quick-delete');
        
        if (!this.allPhotos || this.allPhotos.length === 0) {
            container.innerHTML = '<div class="empty">此目录下暂无照片</div>';
            if (btnQuickDelete) btnQuickDelete.style.display = 'none';
            return;
        }

        const filtered = this.filterType === 'all'
            ? this.allPhotos
            : this.allPhotos.filter(p => p.type === this.filterType);

        if (filtered.length === 0) {
            container.innerHTML = `<div class="empty">当前过滤条件下无${this.filterType === 'photo' ? '照片' : '视频'}</div>`;
            if (btnQuickDelete) btnQuickDelete.style.display = 'none';
            return;
        }

        if (btnQuickDelete && !this._photoSelection?.isSelectionMode) {
            btnQuickDelete.style.display = '';
        }
        
        const totalPhotos = filtered.length;
        const totalPages = Math.ceil(totalPhotos / this.pageSize);
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const currentPhotos = filtered.slice(startIndex, endIndex);
        
        container.innerHTML = '';
        
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        currentPhotos.forEach(photo => {
            const item = this._buildPhotoCard(photo);
            grid.appendChild(item);
        });
        
        container.appendChild(grid);

        if (this._photoSelection) {
            this._photoSelection.attachToGrid(grid);
        }
        
        this.renderPagination(totalPages);
    }
    
    /**
     * 渲染分页控件
     */
    renderPagination(totalPages) {
        if (totalPages <= 1) {
            return;
        }
        
        const container = document.getElementById('photos-container');
        
        const pagination = document.createElement('div');
        pagination.className = 'pagination';
        
        const prevBtn = document.createElement('button');
        prevBtn.className = 'btn-page';
        prevBtn.textContent = '上一页';
        prevBtn.disabled = this.currentPage === 1;
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.renderPhotosWithPagination();
            }
        });
        pagination.appendChild(prevBtn);
        
        const pageNumbers = [];
        
        let startPage = Math.max(1, this.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            pageNumbers.push(i);
        }
        
        pageNumbers.forEach(pageNum => {
            const pageBtn = document.createElement('button');
            pageBtn.className = `btn-page ${this.currentPage === pageNum ? 'active' : ''}`;
            pageBtn.textContent = pageNum;
            pageBtn.addEventListener('click', () => {
                this.currentPage = pageNum;
                this.renderPhotosWithPagination();
            });
            pagination.appendChild(pageBtn);
        });
        
        const nextBtn = document.createElement('button');
        nextBtn.className = 'btn-page';
        nextBtn.textContent = '下一页';
        nextBtn.disabled = this.currentPage === totalPages;
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.renderPhotosWithPagination();
            }
        });
        pagination.appendChild(nextBtn);
        
        const pageInfo = document.createElement('span');
        pageInfo.className = 'page-info';
        pageInfo.textContent = `第 ${this.currentPage}/${totalPages} 页`;
        pagination.appendChild(pageInfo);
        
        container.appendChild(pagination);
    }
    
    /**
     * 渲染照片网格（兼容旧代码）
     */
    renderPhotos(photos) {
        this.allPhotos = photos;
        this.currentPage = 1;
        this.renderPhotosWithPagination();
    }

    /**
     * 预览照片
     */
    previewPhoto(photo) {
        if (window.app && typeof window.app.previewPhoto === 'function') {
            const list = this.allPhotos || [photo];
            window.app.previewPhoto(photo, list);
        } else {
            console.warn('app.previewPhoto 不可用，降级预览');
        }
    }

    /**
     * 展开节点
     */
    expandNode(nodeElement) {
        nodeElement.classList.add('expanded');
    }

    /**
     * 收起节点
     */
    collapseNode(nodeElement) {
        nodeElement.classList.remove('expanded');
    }

    /**
     * 切换节点
     */
    toggleNode(nodeElement) {
        if (nodeElement.classList.contains('expanded')) {
            this.collapseNode(nodeElement);
        } else {
            this.expandNode(nodeElement);
        }
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        this._initPhotoSelection();

        const filterGroup = document.getElementById('media-filter-group');
        if (filterGroup) {
            filterGroup.addEventListener('click', (e) => {
                const btn = e.target.closest('.filter-btn');
                if (!btn) return;
                const type = btn.dataset.filter;
                if (!type || type === this.filterType) return;
                this.filterType = type;
                this._syncFilterButtons();
                this.currentPage = 1;
                this.renderPhotosWithPagination();
            });
        }

        const btnToggle = document.getElementById('btn-toggle-selection');
        if (btnToggle) {
            btnToggle.addEventListener('click', () => {
                if (this._photoSelection) {
                    if (this._photoSelection.isSelectionMode) {
                        this._photoSelection.exitSelectionMode();
                    } else {
                        this._photoSelection.enterSelectionMode();
                    }
                }
            });
        }

        const btnCancel = document.getElementById('btn-cancel-selection');
        if (btnCancel) {
            btnCancel.addEventListener('click', () => {
                if (this._photoSelection) {
                    this._photoSelection.exitSelectionMode();
                }
            });
        }

        const btnDelete = document.getElementById('btn-delete-selected');
        if (btnDelete) {
            btnDelete.addEventListener('click', () => {
                this._deleteSelectedPhotos();
            });
        }

        const btnQuickDelete = document.getElementById('btn-quick-delete');
        if (btnQuickDelete) {
            btnQuickDelete.addEventListener('click', () => {
                if (this._photoSelection) {
                    if (this._photoSelection.isSelectionMode && this._photoSelection.getSelectedPaths().size > 0) {
                        this._deleteSelectedPhotos();
                    } else {
                        this._photoSelection.enterSelectionMode();
                    }
                }
            });
        }
    }

    /**
     * 初始化 PhotoSelection 实例
     */
    _initPhotoSelection() {
        if (this._photoSelection) {
            this._photoSelection.destroy();
        }

        if (typeof PhotoSelection !== 'undefined') {
            this._photoSelection = new PhotoSelection({
                onPreview: (photo) => {
                    this.previewPhoto(photo);
                },
                onEnterMode: () => {
                    this._updateSelectionToolbar(true);
                },
                onExitMode: () => {
                    this._updateSelectionToolbar(false);
                },
                onSelectionChange: (selectedPaths) => {
                    const count = selectedPaths.size;
                    const countEl = document.getElementById('selection-count');
                    if (countEl) countEl.textContent = count;
                    const btnDelete = document.getElementById('btn-delete-selected');
                    if (btnDelete) btnDelete.disabled = count === 0;
                }
            });
        }
    }

    /**
     * 切换工具栏显示状态
     */
    _updateSelectionToolbar(isSelectionMode) {
        const btnToggle = document.getElementById('btn-toggle-selection');
        const toolbar = document.getElementById('selection-toolbar');
        const btnQuickDelete = document.getElementById('btn-quick-delete');
        if (btnToggle) {
            btnToggle.style.display = isSelectionMode ? 'none' : '';
        }
        if (toolbar) {
            toolbar.classList.toggle('visible', isSelectionMode);
        }
        if (btnQuickDelete) {
            if (isSelectionMode) {
                btnQuickDelete.style.display = 'none';
            } else {
                const hasPhotos = !!document.querySelector('#photos-container .photo-item');
                btnQuickDelete.style.display = hasPhotos ? '' : 'none';
            }
        }
        const grid = document.querySelector('#photos-container .photos-grid');
        if (grid) {
            grid.classList.toggle('photos-grid--selection-mode', isSelectionMode);
        }
    }

    /**
     * 批量删除已选照片
     */
    async _deleteSelectedPhotos() {
        if (!this._photoSelection) return;
        const paths = [...this._photoSelection.getSelectedPaths()];
        if (paths.length === 0) return;

        const confirmed = await this._showDeleteConfirm(
            `确定要删除选中的 ${paths.length} 张照片吗？此操作不可撤销。`
        );
        if (!confirmed) return;

        // 立即退出选择模式并从缓存中移除被删除的照片
        this._photoSelection.exitSelectionMode();
        const deletedPathsSet = new Set(paths);

        // 从缓存中移除被删除的照片（避免不必要的重新加载）
        if (this.currentPath && this.photosCache[this.currentPath]) {
            this.photosCache[this.currentPath] = this.photosCache[this.currentPath].filter(
                photo => !deletedPathsSet.has(photo.path)
            );
        }

        try {
            const response = await api.client.post('/files/delete', { paths });
            if (response.status === 'completed' || response.deleted_count !== undefined) {
                const deletedCount = response.deleted_count !== undefined ? response.deleted_count : paths.length;
                if (window.app) window.app.showSuccess(`已删除 ${deletedCount} 张照片`);
                // 仅刷新当前视图，不重新加载整个目录树
                if (this.currentPath) {
                    this.renderPhotos(this.photosCache[this.currentPath] || []);
                }
                // 异步刷新统计信息（不阻塞 UI）
                if (window.app && typeof window.app.loadAlbumStats === 'function') {
                    window.app.loadAlbumStats().catch(() => {});
                }
            } else {
                if (window.app) window.app.showError('删除失败：' + (response.error || '未知错误'));
            }
        } catch (error) {
            console.error('删除照片失败:', error);
            if (window.app) window.app.showError('删除失败，请检查网络连接');
        }
    }

    /**
     * 显示自定义删除确认对话框
     */
    _showDeleteConfirm(message) {
        return new Promise((resolve) => {
            const dialog = document.getElementById('delete-confirm-dialog');
            if (!dialog) {
                resolve(confirm(message));
                return;
            }
            const msgEl = document.getElementById('delete-confirm-message');
            if (msgEl) msgEl.textContent = message;
            dialog.style.display = 'flex';

            const onConfirm = () => { cleanup(); resolve(true); };
            const onCancel  = () => { cleanup(); resolve(false); };
            const onOverlay = (e) => { if (e.target === dialog) { cleanup(); resolve(false); } };

            function cleanup() {
                dialog.style.display = 'none';
                document.getElementById('delete-confirm-btn').removeEventListener('click', onConfirm);
                document.getElementById('delete-cancel-btn').removeEventListener('click', onCancel);
                dialog.removeEventListener('click', onOverlay);
            }

            document.getElementById('delete-confirm-btn').addEventListener('click', onConfirm);
            document.getElementById('delete-cancel-btn').addEventListener('click', onCancel);
            dialog.addEventListener('click', onOverlay);
        });
    }

    /**
     * 显示照片右键菜单
     */
    _showContextMenu(event, photo, cardEl) {
        const menu = document.getElementById('photo-context-menu');
        if (!menu) return;

        menu.style.display = 'block';
        let x = event.clientX;
        let y = event.clientY;
        const mw = menu.offsetWidth  || 160;
        const mh = menu.offsetHeight || 120;
        if (x + mw > window.innerWidth)  x = window.innerWidth  - mw - 8;
        if (y + mh > window.innerHeight) y = window.innerHeight - mh - 8;
        menu.style.left = x + 'px';
        menu.style.top  = y + 'px';

        const newMenu = menu.cloneNode(true);
        menu.parentNode.replaceChild(newMenu, menu);
        newMenu.style.display = 'block';
        newMenu.style.left = x + 'px';
        newMenu.style.top  = y + 'px';

        const closeMenu = () => { newMenu.style.display = 'none'; };

        newMenu.querySelector('#ctx-preview').addEventListener('click', () => {
            closeMenu();
            this.previewPhoto(photo);
        });
        newMenu.querySelector('#ctx-open').addEventListener('click', () => {
            closeMenu();
            if (window.app && typeof window.app.openPhoto === 'function') {
                window.app.openPhoto(photo);
            }
        });
        newMenu.querySelector('#ctx-delete').addEventListener('click', async () => {
            closeMenu();
            const confirmed = await this._showDeleteConfirm(`确定要删除 "${photo.name}" 吗？`);
            if (!confirmed) return;
            try {
                const response = await api.client.post('/files/delete', { paths: [photo.path] });
                if (response.status === 'completed' || response.deleted_count !== undefined) {
                    if (window.app) window.app.showSuccess(`已删除 "${photo.name}"`);
                    if (this.currentPath) {
                        delete this.photosCache[this.currentPath];
                        await this.loadPhotos(this.currentPath);
                    }
                    if (window.app && typeof window.app.loadAlbumStats === 'function') {
                        window.app.loadAlbumStats();
                    }
                } else {
                    if (window.app) window.app.showError('删除失败：' + (response.error || '未知错误'));
                }
            } catch (err) {
                if (window.app) window.app.showError('删除失败，请检查连接');
            }
        });

        const closeOnOutside = (e) => {
            if (!newMenu.contains(e.target)) {
                closeMenu();
                document.removeEventListener('click', closeOnOutside, true);
            }
        };
        setTimeout(() => document.addEventListener('click', closeOnOutside, true), 0);
    }

    /**
     * 根据 treeData 渲染年份跳转下拉框
     */
    renderYearJumper(treeData) {
        const jumper = document.getElementById('year-jumper');
        const select = document.getElementById('year-jump-select');
        if (!jumper || !select) return;

        const years = (treeData.children || [])
            .filter(n => /^\d{4}$/.test(n.name))
            .sort((a, b) => b.name.localeCompare(a.name));

        if (years.length === 0) {
            jumper.style.display = 'none';
            return;
        }

        select.innerHTML = '<option value="">— 跳转到年份 —</option>';
        years.forEach(y => {
            const opt = document.createElement('option');
            opt.value = y.path;
            opt.textContent = `${y.name} 年（${y.count} 张）`;
            select.appendChild(opt);
        });
        jumper.style.display = 'block';

        select.onchange = () => {
            const path = select.value;
            if (!path) return;
            select.value = '';
            const node = (this.treeData?.children || []).find(n => n.path === path);
            if (node) {
                this.selectNode(node.path, node.name);
                const treeContainer = document.getElementById('tree-container');
                const nodeEl = treeContainer?.querySelector(`[data-path="${CSS.escape(path)}"]`);
                if (nodeEl) nodeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        };
    }

    /**
     * 同步过滤按钮的 active 状态
     */
    _syncFilterButtons() {
        const filterGroup = document.getElementById('media-filter-group');
        if (!filterGroup) return;
        filterGroup.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === this.filterType);
        });
    }

    /**
     * 根据 allPhotos 内容决定是否展示过滤按钮组
     */
    _updateFilterGroupVisibility() {
        const filterGroup = document.getElementById('media-filter-group');
        if (!filterGroup) return;
        const hasVideo = this.allPhotos.some(p => p.type === 'video');
        filterGroup.style.display = hasVideo ? 'flex' : 'none';
    }
}
