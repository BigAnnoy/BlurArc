/**
 * 相册浏览器专用模块
 * 处理树节点展开/收起、照片加载、目录树渲染等
 */

const AlbumBrowser = {
    // 当前选中的路径
    currentPath: null,
    // 目录树数据
    treeData: null,
    // 缓存的照片列表
    photosCache: {},
    // 当前页码
    currentPage: 1,
    // 每页照片数量
    pageSize: 50,
    // 所有照片数据
    allPhotos: [],
    // 多选实例
    _photoSelection: null,
    // 媒体类型过滤（v0.1）: 'all' | 'photo' | 'video'
    filterType: 'all',
    
    /**
     * 初始化相册浏览器
     */
    async init() {
        console.log('初始化相册浏览器');
        
        // 加载目录树
        await this.loadTree();
        
        // 绑定事件
        this.bindEvents();
    },

    /**
     * 加载目录树
     */
    async loadTree() {
        try {
            console.log('加载目录树...');
            if (!window.api) {
                throw new Error('API 对象未初始化，请检查 api.js 是否正确加载');
            }
            const response = await window.api.get('/album/tree');
            
            this.treeData = response;
            // 同步给 App，保持单一数据源
            if (window.app) {
                window.app.albumTree = response;
            }
            console.log('目录树数据:', response);
            
            // 检查响应是否有错误
            if (response.error) {
                console.error('目录树API返回错误:', response.error);
                document.getElementById('tree-container').innerHTML = 
                    '<div class="error">' + response.error + '</div>';
                // 清空照片容器
                document.getElementById('photos-container').innerHTML = 
                    '<div class="empty">请先设置相册路径</div>';
                document.getElementById('content-title').textContent = 'Blur Arc';
                return;
            }
            
            // 渲染树
            this.renderTree(response);

            // 渲染年份快跳下拉（v0.1）
            this.renderYearJumper(response);
            
            // 默认选中第一个有照片的顶层文件夹，而不是根节点
            // 因为根节点本身不渲染到DOM中
            if (response.children && response.children.length > 0) {
                // 优先选择有照片的文件夹
                const firstWithPhotos = response.children.find(child => child.count > 0);
                const targetNode = firstWithPhotos || response.children[0];
                this.selectNode(targetNode.path, targetNode.name);
            }
        } catch (error) {
            console.error('加载目录树失败:', error);
            document.getElementById('tree-container').innerHTML = 
                '<div class="error">加载目录树失败</div>';
            // 清空照片容器
            document.getElementById('photos-container').innerHTML = 
                '<div class="empty">请先设置相册路径</div>';
            document.getElementById('content-title').textContent = 'Blur Arc';
        }
    },

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

        // 排序辅助：有照片的排前面，同类按名称升序
        const sortChildren = (children) => [...children].sort((a, b) => {
            const aHas = (a.count || 0) > 0;
            const bHas = (b.count || 0) > 0;
            if (aHas && !bHas) return -1;
            if (!aHas && bHas) return 1;
            return a.name.localeCompare(b.name);
        });

        // 递归构建节点：返回一个 <li> 元素
        // depth: 当前节点深度（0=根节点, 1=根的直接子节点）
        const buildNode = (node, depth = 0) => {
            const hasChildren = node.children && node.children.length > 0;

            const li = document.createElement('li');
            li.className = 'tree-item' + (hasChildren ? ' expandable' : ' tree-leaf');

            // 节点内容容器
            const content = document.createElement('div');
            content.className = 'tree-item-content';

            // 折叠图标
            const toggle = document.createElement('span');
            toggle.className = 'tree-item-toggle';

            // 文件夹图标
            const icon = document.createElement('span');
            icon.className = 'tree-item-icon';

            // 节点标签
            const label = document.createElement('span');
            label.className = 'tree-item-label';
            label.textContent = node.name;
            label.dataset.path = node.path;
            label.dataset.count = node.count || 0;

            // 照片数量（如果有）
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

            // 点击选中
            content.addEventListener('click', (e) => {
                e.stopPropagation();
                AlbumBrowser.selectNode(node.path, node.name);
            });

            if (hasChildren) {
                const childList = document.createElement('ul');
                childList.className = 'tree-children';

                // 默认展开：根节点(depth=0)和根的直接子节点(depth=1)默认展开
                if (depth <= 1) {
                    li.classList.add('expanded');
                }

                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    AlbumBrowser.toggleNode(li);
                });

                sortChildren(node.children).forEach(child => {
                    childList.appendChild(buildNode(child, depth + 1));
                });

                li.appendChild(childList);
            }

            return li;
        };

        // 根节点也渲染为一个可点击的节点
        const rootList = document.createElement('ul');
        rootList.className = 'tree-list';

        // 创建根节点，depth=0 使其默认展开
        const rootNode = buildNode(data, 0);
        if (rootNode) {
            rootNode.classList.add('expanded');  // 根节点默认展开
            rootList.appendChild(rootNode);
        }

        container.appendChild(rootList);
    },

    /**
     * 选中节点
     */
    async selectNode(path, name) {
        console.log('选中节点:', path, name);
        
        this.currentPath = path;
        
        // 高亮选中节点
        document.querySelectorAll('.tree-item').forEach(item => {
            item.classList.remove('selected');
            const label = item.querySelector('.tree-item-label');
            if (label && label.dataset.path === path) {
                item.classList.add('selected');
            }
        });
        
        // 更新内容区标题
        const contentTitle = document.getElementById('content-title');
        if (contentTitle) contentTitle.textContent = name;
        
        // 加载照片
        await this.loadPhotos(path);
    },

    /**
     * 加载照片列表
     */
    async loadPhotos(path) {
        try {
            console.log('加载照片:', path);
            
            // 路径切换时重置过滤（v0.1）
            this.filterType = 'all';
            this._syncFilterButtons();

            // 检查缓存
            if (this.photosCache[path]) {
                this.allPhotos = this.photosCache[path];
                this.currentPage = 1;
                this.renderPhotosWithPagination();
                this._updateFilterGroupVisibility();
                return;
            }
            
            // 显示加载中
            const container = document.getElementById('photos-container');
            container.innerHTML = '<div class="loading">加载中...</div>';
            
            // 获取照片列表
            const response = await window.api.get('/album/photos', { path });
            
            // 响应格式: { path, count, photos: [...] }
            // 提取 photos 数组
            const photos = response.photos || [];
            console.log('获取到照片:', photos.length, '张');
            
            // 缓存
            this.photosCache[path] = photos;
            this.allPhotos = photos;
            this.currentPage = 1;
            
            // 渲染（带分页）
            this.renderPhotosWithPagination();
            this._updateFilterGroupVisibility();
        } catch (error) {
            console.error('加载照片失败:', error);
            document.getElementById('photos-container').innerHTML = 
                '<div class="error">加载照片失败</div>';
        }
    },

    /**
     * 构建照片卡片 DOM（统一入口，含勾选框）
     * @param {object} photo - 照片数据对象
     * @returns {HTMLElement} .photo-item 元素
     */
    _buildPhotoCard(photo) {
        const item = document.createElement('div');
        item.className = 'photo-item';
        item.dataset.path = photo.path || '';
        item.dataset.name = photo.name || '';
        item.dataset.url = photo.url || photo.thumbnail_url || '';
        item.dataset.size = photo.size || 0;

        // 勾选框
        const checkbox = document.createElement('div');
        checkbox.className = 'photo-checkbox';
        item.appendChild(checkbox);

        const img = document.createElement('img');
        img.src = photo.thumbnail_url || photo.url;
        img.alt = photo.name;
        img.className = 'photo-image';
        img.loading = 'lazy';
        // onerror 降级：图片加载失败时显示占位图标
        img.onerror = () => {
            img.onerror = null; // 防止循环触发
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'photo-error-placeholder';
            const isVideo = photo.type === 'video';
            placeholder.innerHTML = `<span>${isVideo ? '🎬' : '🖼'}</span><small>${isVideo ? '视频' : '图片加载失败'}</small>`;
            item.insertBefore(placeholder, img.nextSibling);
        };

        item.appendChild(img);

        // 视频类型徽标
        if (photo.type === 'video') {
            const badge = document.createElement('div');
            badge.className = 'photo-type-badge';
            badge.textContent = '🎬 视频';
            item.appendChild(badge);
        }

        // hover 浮层（文件名 + 大小）
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

        // 右键菜单触发
        item.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            AlbumBrowser._showContextMenu(e, photo, item);
        });

        return item;
    },

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

        // 媒体类型过滤（v0.1）
        const filtered = this.filterType === 'all'
            ? this.allPhotos
            : this.allPhotos.filter(p => p.type === this.filterType);

        if (filtered.length === 0) {
            container.innerHTML = `<div class="empty">当前过滤条件下无${this.filterType === 'photo' ? '照片' : '视频'}</div>`;
            if (btnQuickDelete) btnQuickDelete.style.display = 'none';
            return;
        }

        // 有照片时，在非多选模式下显示快速删除按钮
        if (btnQuickDelete && !this._photoSelection?.isSelectionMode) {
            btnQuickDelete.style.display = '';
        }
        
        // 计算分页信息
        const totalPhotos = filtered.length;
        const totalPages = Math.ceil(totalPhotos / this.pageSize);
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const currentPhotos = filtered.slice(startIndex, endIndex);
        
        container.innerHTML = '';
        
        // 渲染照片网格
        const grid = document.createElement('div');
        grid.className = 'photos-grid';
        
        currentPhotos.forEach(photo => {
            const item = this._buildPhotoCard(photo);
            grid.appendChild(item);
        });
        
        container.appendChild(grid);

        // 接入多选交互
        if (this._photoSelection) {
            this._photoSelection.attachToGrid(grid);
        }
        
        // 渲染分页控件
        this.renderPagination(totalPages);
    },
    
    /**
     * 渲染分页控件
     */
    renderPagination(totalPages) {
        if (totalPages <= 1) {
            return; // 只有一页时不显示分页
        }
        
        const container = document.getElementById('photos-container');
        
        const pagination = document.createElement('div');
        pagination.className = 'pagination';
        
        // 上一页按钮
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
        
        // 页码按钮
        const pageNumbers = [];
        
        // 计算要显示的页码范围
        let startPage = Math.max(1, this.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        // 确保至少显示5个页码
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            pageNumbers.push(i);
        }
        
        // 显示页码
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
        
        // 下一页按钮
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
        
        // 显示页码信息
        const pageInfo = document.createElement('span');
        pageInfo.className = 'page-info';
        pageInfo.textContent = `第 ${this.currentPage}/${totalPages} 页`;
        pagination.appendChild(pageInfo);
        
        container.appendChild(pagination);
    },
    
    /**
     * 渲染照片网格（兼容旧代码）
     */
    renderPhotos(photos) {
        // 保持向后兼容，将照片保存到allPhotos并调用新的渲染方法
        this.allPhotos = photos;
        this.currentPage = 1;
        this.renderPhotosWithPagination();
    },

    /**
     * 预览照片（委托给 App.previewPhoto，带列表翻页）
     */
    previewPhoto(photo) {
        if (window.app && typeof window.app.previewPhoto === 'function') {
            // 传递当前页照片列表，以支持 ← → 翻页
            const list = this.allPhotos || [photo];
            window.app.previewPhoto(photo, list);
        } else {
            console.warn('app.previewPhoto 不可用，降级预览');
        }
    },

    /**
     * 展开节点
     */
    expandNode(nodeElement) {
        nodeElement.classList.add('expanded');
    },

    /**
     * 收起节点
     */
    collapseNode(nodeElement) {
        nodeElement.classList.remove('expanded');
    },

    /**
     * 切换节点
     */
    toggleNode(nodeElement) {
        if (nodeElement.classList.contains('expanded')) {
            this.collapseNode(nodeElement);
        } else {
            this.expandNode(nodeElement);
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮由 main.js App.bindEvents() 统一管理，此处不重复绑定

        // 初始化多选交互
        this._initPhotoSelection();

        // 媒体类型过滤按钮组（v0.1）
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

        // 多选入口按钮
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

        // 取消选择按钮
        const btnCancel = document.getElementById('btn-cancel-selection');
        if (btnCancel) {
            btnCancel.addEventListener('click', () => {
                if (this._photoSelection) {
                    this._photoSelection.exitSelectionMode();
                }
            });
        }

        // 删除已选照片按钮
        const btnDelete = document.getElementById('btn-delete-selected');
        if (btnDelete) {
            btnDelete.addEventListener('click', () => {
                this._deleteSelectedPhotos();
            });
        }

        // 快速删除按钮（常驻，点击后进入多选模式；多选模式中被隐藏）
        const btnQuickDelete = document.getElementById('btn-quick-delete');
        if (btnQuickDelete) {
            btnQuickDelete.addEventListener('click', () => {
                if (this._photoSelection) {
                    // 如已在多选模式有选中项，直接删除；否则进入多选模式
                    if (this._photoSelection.isSelectionMode && this._photoSelection.getSelectedPaths().size > 0) {
                        this._deleteSelectedPhotos();
                    } else {
                        this._photoSelection.enterSelectionMode();
                    }
                }
            });
        }

    },

    /**
     * 初始化 PhotoSelection 实例
     */
    _initPhotoSelection() {
        if (this._photoSelection) {
            this._photoSelection.destroy();
        }

        this._photoSelection = new PhotoSelection({
            onPreview: (photo) => {
                AlbumBrowser.previewPhoto(photo);
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
    },

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
        // 多选模式时隐藏快速删除按钮（多选工具栏里已有删除）
        if (btnQuickDelete) {
            if (isSelectionMode) {
                btnQuickDelete.style.display = 'none';
            } else {
                // 退出多选模式时，如果有照片则显示快速删除
                const hasPhotos = !!document.querySelector('#photos-container .photo-item');
                btnQuickDelete.style.display = hasPhotos ? '' : 'none';
            }
        }
        // 同时给网格容器加多选模式 class，方便 CSS 显示勾选框
        const grid = document.querySelector('#photos-container .photos-grid');
        if (grid) {
            grid.classList.toggle('photos-grid--selection-mode', isSelectionMode);
        }
    },

    /**
     * 批量删除已选照片（使用自定义确认对话框）
     */
    async _deleteSelectedPhotos() {
        if (!this._photoSelection) return;
        const paths = [...this._photoSelection.getSelectedPaths()];
        if (paths.length === 0) return;

        const confirmed = await AlbumBrowser._showDeleteConfirm(
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
            const response = await window.api.post('/files/delete', { paths });
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
    },

    /**
     * 显示自定义删除确认对话框
     * @param {string} message
     * @returns {Promise<boolean>}
     */
    _showDeleteConfirm(message) {
        return new Promise((resolve) => {
            const dialog = document.getElementById('delete-confirm-dialog');
            if (!dialog) {
                // 降级到原生 confirm
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
    },

    /**
     * 显示照片右键菜单
     */
    _showContextMenu(event, photo, cardEl) {
        const menu = document.getElementById('photo-context-menu');
        if (!menu) return;

        // 定位
        menu.style.display = 'block';
        let x = event.clientX;
        let y = event.clientY;
        // 防止超出视口
        const mw = menu.offsetWidth  || 160;
        const mh = menu.offsetHeight || 120;
        if (x + mw > window.innerWidth)  x = window.innerWidth  - mw - 8;
        if (y + mh > window.innerHeight) y = window.innerHeight - mh - 8;
        menu.style.left = x + 'px';
        menu.style.top  = y + 'px';

        // 解绑旧事件（防止重复注册）
        const newMenu = menu.cloneNode(true);
        menu.parentNode.replaceChild(newMenu, menu);
        newMenu.style.display = 'block';
        newMenu.style.left = x + 'px';
        newMenu.style.top  = y + 'px';

        // 绑定菜单项
        const closeMenu = () => { newMenu.style.display = 'none'; };

        newMenu.querySelector('#ctx-preview').addEventListener('click', () => {
            closeMenu();
            AlbumBrowser.previewPhoto(photo);
        });
        newMenu.querySelector('#ctx-open').addEventListener('click', () => {
            closeMenu();
            if (window.app && typeof window.app.openPhoto === 'function') {
                window.app.openPhoto(photo);
            }
        });
        newMenu.querySelector('#ctx-delete').addEventListener('click', async () => {
            closeMenu();
            const confirmed = await AlbumBrowser._showDeleteConfirm(`确定要删除 "${photo.name}" 吗？`);
            if (!confirmed) return;
            try {
                const response = await window.api.post('/files/delete', { paths: [photo.path] });
                if (response.status === 'completed' || response.deleted_count !== undefined) {
                    if (window.app) window.app.showSuccess(`已删除 "${photo.name}"`);
                    if (AlbumBrowser.currentPath) {
                        delete AlbumBrowser.photosCache[AlbumBrowser.currentPath];
                        await AlbumBrowser.loadPhotos(AlbumBrowser.currentPath);
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

        // 点击其他区域关闭
        const closeOnOutside = (e) => {
            if (!newMenu.contains(e.target)) {
                closeMenu();
                document.removeEventListener('click', closeOnOutside, true);
            }
        };
        // 延迟绑定，避免当前 contextmenu 事件触发关闭
        setTimeout(() => document.addEventListener('click', closeOnOutside, true), 0);
    },

    /* ──────────────────────────────────────────────────────────
     * v0.1 新增：年份快速跳转
     * ────────────────────────────────────────────────────────── */

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

        // 保留占位选项，重建年份选项
        select.innerHTML = '<option value="">— 跳转到年份 —</option>';
        years.forEach(y => {
            const opt = document.createElement('option');
            opt.value = y.path;
            opt.textContent = `${y.name} 年（${y.count} 张）`;
            select.appendChild(opt);
        });
        jumper.style.display = 'block';

        // 绑定事件（幂等：先移除旧监听）
        select.onchange = () => {
            const path = select.value;
            if (!path) return;
            select.value = '';  // 重置显示
            // 找到年份节点并选中
            const node = (this.treeData?.children || []).find(n => n.path === path);
            if (node) {
                this.selectNode(node.path, node.name);
                // 滚动目录树使该节点可见
                const treeContainer = document.getElementById('tree-container');
                const nodeEl = treeContainer?.querySelector(`[data-path="${CSS.escape(path)}"]`);
                if (nodeEl) nodeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        };
    },

    /* ──────────────────────────────────────────────────────────
     * v0.1 新增：媒体过滤辅助
     * ────────────────────────────────────────────────────────── */

    /**
     * 同步过滤按钮的 active 状态
     */
    _syncFilterButtons() {
        const filterGroup = document.getElementById('media-filter-group');
        if (!filterGroup) return;
        filterGroup.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === this.filterType);
        });
    },

    /**
     * 根据 allPhotos 内容决定是否展示过滤按钮组
     * 仅当有视频文件时才显示（只有图片则没必要过滤）
     */
    _updateFilterGroupVisibility() {
        const filterGroup = document.getElementById('media-filter-group');
        if (!filterGroup) return;
        const hasVideo = this.allPhotos.some(p => p.type === 'video');
        filterGroup.style.display = hasVideo ? 'flex' : 'none';
    },
};

// 暴露到全局作用域
window.AlbumBrowser = AlbumBrowser;