/**
 * 照片多选交互工具模块
 * 提供统一的「单击=预览，长按/勾选框=多选模式」交互逻辑
 * 适用于相册主页和导入对话框的所有照片网格
 */

class PhotoSelection {
    /**
     * @param {object} options
     * @param {function} options.onPreview      - 单击照片触发预览，接收 photoItem 元素
     * @param {function} options.onSelectionChange - 选中数量变化时回调，接收 Set<string>
     * @param {function} options.onEnterMode    - 进入多选模式时回调
     * @param {function} options.onExitMode     - 退出多选模式时回调
     * @param {function} [options.canSelect]    - 可选：判断某个 photoItem 能否被选中，返回 bool
     */
    constructor(options = {}) {
        this.onPreview = options.onPreview || (() => {});
        this.onSelectionChange = options.onSelectionChange || (() => {});
        this.onEnterMode = options.onEnterMode || (() => {});
        this.onExitMode = options.onExitMode || (() => {});
        this.canSelect = options.canSelect || (() => true);

        this.isSelectionMode = false;
        this.selectedPaths = new Set();

        // 长按计时器
        this._longPressTimer = null;
        this._longPressDelay = 400; // ms

        // 绑定键盘事件（用于 Esc 退出）
        this._escHandler = (e) => {
            if (e.key === 'Escape' && this.isSelectionMode) {
                this.exitSelectionMode();
            }
        };
        document.addEventListener('keydown', this._escHandler);
    }

    /**
     * 销毁：解绑全局事件
     */
    destroy() {
        document.removeEventListener('keydown', this._escHandler);
    }

    /**
     * 进入多选模式
     */
    enterSelectionMode() {
        if (this.isSelectionMode) return;
        this.isSelectionMode = true;
        this.onEnterMode();
    }

    /**
     * 退出多选模式，清空选中
     */
    exitSelectionMode() {
        if (!this.isSelectionMode) return;
        this.isSelectionMode = false;
        this.selectedPaths.clear();

        // 清除所有 selected 样式
        document.querySelectorAll('.photo-item.selection-active').forEach(item => {
            item.classList.remove('selected');
            item.classList.remove('selection-active');
        });

        this.onExitMode();
        this.onSelectionChange(this.selectedPaths);
    }

    /**
     * 切换某个照片项的选中状态
     * @param {HTMLElement} photoItem
     * @param {string} path
     */
    toggleSelect(photoItem, path) {
        if (!this.canSelect(photoItem)) return;

        if (photoItem.classList.contains('selected')) {
            photoItem.classList.remove('selected');
            this.selectedPaths.delete(path);
        } else {
            photoItem.classList.add('selected');
            this.selectedPaths.add(path);
        }
        this.onSelectionChange(this.selectedPaths);
    }

    /**
     * 获取当前选中路径集合（浅拷贝）
     * @returns {Set<string>}
     */
    getSelectedPaths() {
        return new Set(this.selectedPaths);
    }

    /**
     * 清空选中，但不退出多选模式
     */
    clearSelection() {
        this.selectedPaths.clear();
        document.querySelectorAll('.photo-item.selection-active.selected').forEach(item => {
            item.classList.remove('selected');
        });
        this.onSelectionChange(this.selectedPaths);
    }

    /**
     * 为一个照片网格容器绑定多选交互逻辑
     * 调用此方法后，网格内现有的 .photo-item 元素将获得交互能力
     *
     * 注意：此方法采用「事件委托」挂载到 container 上，
     * 所以对于动态渲染的网格，可以在渲染完成后调用此方法绑定到外层容器。
     *
     * @param {HTMLElement} container - photos-grid 或包含 .photo-item 的容器
     * @param {object} [gridOptions]
     * @param {function} [gridOptions.getPath]   - 从 photoItem 获取路径，默认 item.dataset.path
     * @param {function} [gridOptions.getPhoto]  - 从 photoItem 获取 photo 对象（用于预览），默认从 dataset 还原
     */
    attachToGrid(container, gridOptions = {}) {
        if (!container) return;

        const getPath = gridOptions.getPath || ((item) => item.dataset.path || '');
        const getPhoto = gridOptions.getPhoto || ((item) => ({
            name: item.dataset.name || item.querySelector('.photo-name')?.textContent || '',
            path: item.dataset.path || '',
            thumbnail_url: item.querySelector('img.photo-image')?.src || '',
            url: item.dataset.url || item.querySelector('img.photo-image')?.src || '',
            size: Number(item.dataset.size) || 0
        }));

        // 标记所有当前 photo-item，便于退出多选时清理
        container.querySelectorAll('.photo-item').forEach(item => {
            item.classList.add('selection-active');
        });

        // ---- 事件委托绑定到 container ----
        // 避免重复绑定
        if (container._photoSelectionBound) {
            container.removeEventListener('mousedown', container._photoSelectionBound.mousedown);
            container.removeEventListener('mouseup', container._photoSelectionBound.mouseup);
            container.removeEventListener('mouseleave', container._photoSelectionBound.mouseleave);
            container.removeEventListener('click', container._photoSelectionBound.click);
            container.removeEventListener('touchstart', container._photoSelectionBound.touchstart);
            container.removeEventListener('touchend', container._photoSelectionBound.touchend);
            container.removeEventListener('touchmove', container._photoSelectionBound.touchmove);
        }

        const handlers = {
            mousedown: (e) => {
                const item = e.target.closest('.photo-item');
                if (!item) return;
                // 如果点击的是勾选框，不触发长按
                if (e.target.closest('.photo-checkbox')) return;

                this._longPressTimer = setTimeout(() => {
                    this._longPressTimer = null;
                    if (!this.isSelectionMode) {
                        this.enterSelectionMode();
                    }
                    this.toggleSelect(item, getPath(item));
                }, this._longPressDelay);
            },
            mouseup: () => {
                if (this._longPressTimer) {
                    clearTimeout(this._longPressTimer);
                    this._longPressTimer = null;
                }
            },
            mouseleave: () => {
                if (this._longPressTimer) {
                    clearTimeout(this._longPressTimer);
                    this._longPressTimer = null;
                }
            },
            click: (e) => {
                const item = e.target.closest('.photo-item');
                if (!item) return;

                // 点击勾选框
                if (e.target.closest('.photo-checkbox')) {
                    e.stopPropagation();
                    if (!this.isSelectionMode) {
                        this.enterSelectionMode();
                    }
                    this.toggleSelect(item, getPath(item));
                    return;
                }

                // 多选模式：单击切换选中
                if (this.isSelectionMode) {
                    this.toggleSelect(item, getPath(item));
                    return;
                }

                // 普通模式：单击预览
                this.onPreview(getPhoto(item), item);
            },
            touchstart: (e) => {
                const item = e.target.closest('.photo-item');
                if (!item) return;
                if (e.target.closest('.photo-checkbox')) return;

                this._longPressTimer = setTimeout(() => {
                    this._longPressTimer = null;
                    if (!this.isSelectionMode) {
                        this.enterSelectionMode();
                    }
                    this.toggleSelect(item, getPath(item));
                }, this._longPressDelay);
            },
            touchend: () => {
                if (this._longPressTimer) {
                    clearTimeout(this._longPressTimer);
                    this._longPressTimer = null;
                }
            },
            touchmove: () => {
                if (this._longPressTimer) {
                    clearTimeout(this._longPressTimer);
                    this._longPressTimer = null;
                }
            }
        };

        container.addEventListener('mousedown', handlers.mousedown);
        container.addEventListener('mouseup', handlers.mouseup);
        container.addEventListener('mouseleave', handlers.mouseleave);
        container.addEventListener('click', handlers.click);
        container.addEventListener('touchstart', handlers.touchstart, { passive: true });
        container.addEventListener('touchend', handlers.touchend);
        container.addEventListener('touchmove', handlers.touchmove, { passive: true });

        container._photoSelectionBound = handlers;
    }
}

// 暴露到全局
window.PhotoSelection = PhotoSelection;
