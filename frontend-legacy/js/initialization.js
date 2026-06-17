/**
 * 初始化屏幕管理
 * 处理首次运行时的相册位置选择
 */

class InitializationScreen {
    constructor() {
        console.log('[InitializationScreen.constructor] 创建 InitializationScreen 实例...');
        
        this.screen = document.getElementById('initialization-screen');
        console.log('[InitializationScreen.constructor] 初始化屏幕:', this.screen ? '✅ 找到' : '❌ 找不到');
        
        this.btnSelect = document.getElementById('btn-select-album');
        console.log('[InitializationScreen.constructor] 【选择相册位置】按钮:', this.btnSelect ? '✅ 找到' : '❌ 找不到');
        
        this.btnConfirm = document.getElementById('btn-confirm-album');
        console.log('[InitializationScreen.constructor] 【确认】按钮:', this.btnConfirm ? '✅ 找到' : '❌ 找不到');
        
        this.pathDisplay = document.getElementById('init-path-display');
        this.pathText = document.getElementById('init-path-text');
        this.selectedPath = null;
        
        console.log('[InitializationScreen.constructor] ✅ 构造函数完成');
    }

    /**
     * 初始化事件监听
     */
    init() {
        console.log('[InitializationScreen.init] 开始初始化事件监听...');
        
        // 重新获取按钮元素，确保获取到最新的 DOM 元素
        this.btnSelect = document.getElementById('btn-select-album');
        this.btnConfirm = document.getElementById('btn-confirm-album');
        
        console.log('[InitializationScreen.init] 重新获取按钮元素:');
        console.log('  - btn-select-album:', this.btnSelect);
        console.log('  - btn-confirm-album:', this.btnConfirm);
        
        if (this.btnSelect) {
            console.log('[InitializationScreen.init] ✅ 找到【选择相册位置】按钮，绑定 click 事件');
            // 先移除可能存在的事件监听器，避免重复绑定
            this.btnSelect.removeEventListener('click', this.selectAlbumPath.bind(this));
            // 绑定新的事件监听器
            this.btnSelect.addEventListener('click', async () => {
                console.log('[InitializationScreen] 🎯 【选择相册位置】按钮被点击！');
                try {
                    await this.selectAlbumPath();
                } catch (err) {
                    console.error('[InitializationScreen] ❌ selectAlbumPath 异常:', err);
                    console.error('[InitializationScreen] 错误堆栈:', err.stack);
                    alert('操作失败: ' + err.message);
                }
            });
            console.log('[InitializationScreen.init] ✅ 【选择相册位置】按钮事件绑定完成');
        } else {
            console.error('[InitializationScreen.init] ❌ 找不到【选择相册位置】按钮 (id=btn-select-album)');
            // 检查 DOM 中有什么元素
            console.log('[InitializationScreen.init] 检查 btn-select-album:', document.getElementById('btn-select-album'));
        }
        
        if (this.btnConfirm) {
            console.log('[InitializationScreen.init] ✅ 找到【确认】按钮，绑定 click 事件');
            // 先移除可能存在的事件监听器，避免重复绑定
            this.btnConfirm.removeEventListener('click', this.confirmAlbumPath.bind(this));
            // 绑定新的事件监听器
            this.btnConfirm.addEventListener('click', () => {
                console.log('[InitializationScreen] 🎯 【确认】按钮被点击！');
                this.confirmAlbumPath();
            });
            console.log('[InitializationScreen.init] ✅ 【确认】按钮事件绑定完成');
        } else {
            console.error('[InitializationScreen.init] ❌ 找不到【确认】按钮 (id=btn-confirm-album)');
        }
        
        console.log('[InitializationScreen.init] ✅ 事件监听初始化完成');
    }

    /**
     * 显示初始化屏幕
     */
    show() {
        if (this.screen) {
            this.screen.classList.add('shown');
        }
    }

    /**
     * 隐藏初始化屏幕
     */
    hide() {
        if (this.screen) {
            this.screen.classList.remove('shown');
        }
    }

    /**
     * 选择相册路径
     */
    async selectAlbumPath() {
        const originalText = this.btnSelect.textContent;
        try {
            // 显示加载状态
            this.btnSelect.disabled = true;
            this.btnSelect.textContent = '⏳ 打开文件夹选择器...';
            
            console.log('[selectAlbumPath] 1. 开始选择相册路径...');
            
            // 1. 先等待 PyWebView API 准备就绪（重要！）
            if (window.pywebviewReady) {
                console.log('[selectAlbumPath] 2. 等待 PyWebView API 准备就绪...');
                try {
                    await window.pywebviewReady.wait(5000);
                    console.log('[selectAlbumPath] 3. ✅ PyWebView API 已准备就绪');
                } catch (err) {
                    console.warn('[selectAlbumPath] ⚠️ PyWebView API 准备超时:', err.message);
                    // 继续尝试，可能已经可用
                }
            } else {
                console.warn('[selectAlbumPath] ⚠️ 未检测到 pywebviewReady 对象');
            }
            
            // 2. 检查 PyWebView API 是否可用
            if (window.pywebview && window.pywebview.api) {
                console.log('[selectAlbumPath] 4. 🎯 PyWebView API 可用，开始调用 select_folder()...');
                console.log('[selectAlbumPath] 5. window.pywebview.api 类型:', typeof window.pywebview.api);
                console.log('[selectAlbumPath] 6. select_folder 方法存在:', typeof window.pywebview.api.select_folder);
                
                // 移除超时逻辑，直接等待文件夹选择完成
                const selectPromise = window.pywebview.api.select_folder();
                
                console.log('[selectAlbumPath] 7. 等待文件夹选择...');
                const path = await selectPromise;
                
                console.log('[selectAlbumPath] 8. 文件夹选择完成，返回值:', path);
                
                if (path && typeof path === 'string' && path.trim()) {
                    // 验证路径是否有效
                    if (await this.validatePath(path)) {
                        this.selectedPath = path;
                        this.pathText.textContent = path;
                        this.pathDisplay.style.display = 'block';
                        this.btnConfirm.style.display = 'block';
                        console.log('[selectAlbumPath] ✅ 成功选择相册路径:', path);
                    }
                } else if (!path) {
                    console.log('[selectAlbumPath] ℹ️ 用户取消了文件夹选择 (path is null/empty)');
                } else {
                    console.warn('[selectAlbumPath] ⚠️ 返回值类型异常:', typeof path, path);
                    alert('⚠️ 文件夹选择返回值异常，请尝试手动输入路径');
                }
            } else {
                // 降级方案：提示用户手动输入
                console.warn('[selectAlbumPath] ⚠️ PyWebView API 不可用，使用降级方案');
                console.warn('[selectAlbumPath]   window.pywebview:', window.pywebview);
                if (window.pywebview) {
                    console.warn('[selectAlbumPath]   window.pywebview.api:', window.pywebview.api);
                }
                
                const path = prompt('PyWebView API 不可用\n\n请输入相册位置的完整路径:\n(例如：D:\\Pictures 或 /home/user/Pictures)');
                if (path && path.trim()) {
                    // 验证路径是否有效
                    if (await this.validatePath(path)) {
                        this.selectedPath = path;
                        this.pathText.textContent = path;
                        this.pathDisplay.style.display = 'block';
                        this.btnConfirm.style.display = 'block';
                        console.log('[selectAlbumPath] ℹ️ 用户手动输入相册路径:', path);
                    }
                } else {
                    console.log('[selectAlbumPath] ℹ️ 用户取消手动输入');
                }
            }
        } catch (error) {
            console.error('[selectAlbumPath] ❌ 选择文件夹异常:', error);
            console.error('[selectAlbumPath] 错误堆栈:', error.stack);
            alert('❌ 选择文件夹失败: ' + error.message + '\n\n请尝试手动输入完整路径。');
        } finally {
            // 恢复按钮状态
            this.btnSelect.disabled = false;
            if (originalText) {
                this.btnSelect.textContent = originalText;
            }
        }
    }

    /**
     * 验证路径是否有效
     */
    async validatePath(path) {
        console.log('[validatePath] 验证路径:', path);
        try {
            // 调用 API 验证路径
            const response = await fetch('/api/import/check', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ source_path: path })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'valid') {
                    console.log('[validatePath] ✅ 路径验证成功:', path);
                    return true;
                } else {
                    console.warn('[validatePath] ❌ 路径验证失败:', result);
                    alert('⚠️ 路径验证失败: ' + (result.error || '路径无效'));
                    return false;
                }
            } else {
                console.error('[validatePath] ❌ API 响应错误:', response.status);
                alert('⚠️ 路径验证失败: API 响应错误');
                return false;
            }
        } catch (error) {
            console.error('[validatePath] ❌ 验证路径异常:', error);
            alert('⚠️ 路径验证失败: ' + error.message);
            return false;
        }
    }

    /**
     * 确认相册路径
     */
    async confirmAlbumPath() {
        if (!this.selectedPath) {
            alert('请先选择相册位置');
            return;
        }

        try {
            // 调用 API 保存相册路径（使用绝对 URL 确保在 PyWebView 环境中可靠）
            const response = await fetch('http://127.0.0.1:5000/api/settings/album-path', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ album_path: this.selectedPath })
            });

            if (response.ok) {
                console.log('Album path saved successfully');
                // 直接刷新页面重新加载
                location.reload();
            } else {
                const error = await response.json();
                throw new Error(error.error || '保存相册路径失败');
            }
        } catch (error) {
            console.error('Error saving album path:', error);
            alert('保存相册路径失败: ' + error.message);
        }
    }
}

// 创建全局实例
if (!window.InitializationScreen) {
    window.InitializationScreen = InitializationScreen;
}

// 创建全局初始化屏幕实例
if (!window.initScreen) {
    // 等待 DOM 准备就绪后再创建实例
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.initScreen = new InitializationScreen();
            console.log('[initialization.js] ✅ DOM 就绪后创建全局 initScreen 实例');
        });
    } else {
        window.initScreen = new InitializationScreen();
        console.log('[initialization.js] ✅ 创建全局 initScreen 实例');
    }
}
