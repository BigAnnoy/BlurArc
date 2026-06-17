/**
 * API 调用封装模块
 * 提供统一的 API 调用接口，处理错误和日志
 */

const API = {
    BASE_URL: 'http://127.0.0.1:5000/api',
    
    /**
     * 发送 HTTP 请求
     */
    async request(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        const method = options.method || 'GET';
        console.log(`[API.request] 📤 发送请求: ${method} ${endpoint}`, { url });
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            console.log(`[API.request] ⏳ 等待响应...`);
            const response = await fetch(url, config);
            console.log(`[API.request] 📥 收到响应: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                const errorMsg = error.error || `HTTP ${response.status}`;
                console.error(`[API.request] ❌ 请求失败: ${errorMsg}`);
                throw new Error(errorMsg);
            }
            
            const data = await response.json();
            console.log(`[API.request] ✅ 响应成功`, data);
            return data;
        } catch (error) {
            console.error(`[API.request] ❌ 请求异常 [${method} ${endpoint}]:`, error.message);
            console.error(`[API.request] 错误详情:`, error);
            throw error;
        }
    },

    /**
     * GET 请求
     * @param {string} endpoint - API 端点
     * @param {object} params - 查询参数 (会被转换为 query string)
     * @param {object} options - HTTP 选项 (headers 等)
     */
    get(endpoint, params = {}, options = {}) {
        // 构建 query string
        const queryString = Object.entries(params)
            .filter(([_, value]) => value !== null && value !== undefined)
            .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
            .join('&');
        
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, {
            ...options,
            method: 'GET',
        });
    },

    /**
     * POST 请求
     */
    post(endpoint, data, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * PUT 请求
     */
    put(endpoint, data, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    /**
     * DELETE 请求
     */
    delete(endpoint, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'DELETE',
        });
    },

    // ========================================================================
    // 相册 API
    // ========================================================================

    /**
     * 获取相册统计信息
     */
    getAlbumStats() {
        console.log('[API.getAlbumStats] 获取相册统计...');
        return this.get('/album/stats').then(data => {
            console.log('[API.getAlbumStats] ✅ 统计数据:', data);
            return data;
        }).catch(error => {
            console.error('[API.getAlbumStats] ❌ 获取统计失败:', error);
            throw error;
        });
    },

    /**
     * 获取完整目录树
     */
    getAlbumTree() {
        console.log('[API.getAlbumTree] 获取目录树...');
        return this.get('/album/tree').then(data => {
            console.log('[API.getAlbumTree] ✅ 目录树数据:', data);
            return data;
        }).catch(error => {
            console.error('[API.getAlbumTree] ❌ 获取目录树失败:', error);
            throw error;
        });
    },

    /**
     * 获取指定路径下的照片列表
     */
    getPhotos(path) {
        console.log('[API.getPhotos] 获取照片列表，路径:', path);
        return this.get('/album/photos', { path }).then(data => {
            console.log('[API.getPhotos] ✅ 照片数据:', data);
            return data;
        }).catch(error => {
            console.error('[API.getPhotos] ❌ 获取照片失败:', error);
            throw error;
        });
    },

    // ========================================================================
    // 设置 API
    // ========================================================================

    /**
     * 获取当前相册路径
     */
    getAlbumPath() {
        console.log('[API.getAlbumPath] 获取相册路径...');
        return this.get('/settings/album-path').then(data => {
            console.log('[API.getAlbumPath] ✅ 相册路径:', data);
            return data;
        }).catch(error => {
            console.error('[API.getAlbumPath] ❌ 获取相册路径失败:', error);
            throw error;
        });
    },

    /**
     * 修改相册路径
     */
    setAlbumPath(path) {
        console.log('[API.setAlbumPath] 设置相册路径:', path);
        return this.put('/settings/album-path', {
            album_path: path,
        }).then(data => {
            console.log('[API.setAlbumPath] ✅ 相册路径设置成功:', data);
            return data;
        }).catch(error => {
            console.error('[API.setAlbumPath] ❌ 设置相册路径失败:', error);
            throw error;
        });
    },

    // ========================================================================
    // 导入 API
    // ========================================================================

    /**
     * 检查导入路径
     */
    async checkImportPath(sourcePath, progressCallback, shouldStopPolling) {
        console.log('[API.checkImportPath] 检查导入路径:', sourcePath);

        const started = await this.post('/import/check/start', {
            source_path: sourcePath,
        });
        const checkId = started.check_id;

        if (!checkId) {
            throw new Error('检查任务启动失败，未返回 check_id');
        }

        const pollIntervalMs = 300;
        while (true) {
            if (typeof shouldStopPolling === 'function' && shouldStopPolling()) {
                throw new Error('CHECK_CANCELLED');
            }

            const progressData = await this.get(`/import/check/progress/${checkId}`);
            const progressRatio = Math.max(0, Math.min(1, (progressData.progress || 0) / 100));

            if (typeof progressCallback === 'function') {
                progressCallback(progressRatio, progressData);
            }

            if (progressData.status === 'completed') {
                console.log('[API.checkImportPath] ✅ 路径检查结果:', progressData.result);
                return progressData.result;
            }

            if (progressData.status === 'failed') {
                throw new Error(progressData.error || '路径检查失败');
            }

            await APIUtils.delay(pollIntervalMs);
        }
    },

    /**
     * 开始导入
     */
    startImport(sourcePath, targetPath, importMode = 'copy', skipSourceDuplicates = false, skipTargetDuplicates = false) {
        console.log('[API.startImport] 开始导入，源:', sourcePath, '目标:', targetPath, '模式:', importMode, '跳过源重复:', skipSourceDuplicates, '跳过目标重复:', skipTargetDuplicates);
        return this.post('/import/start', {
            source_path: sourcePath,
            target_path: targetPath,
            import_mode: importMode,
            skip_source_duplicates: skipSourceDuplicates,
            skip_target_duplicates: skipTargetDuplicates,
        }).then(data => {
            console.log('[API.startImport] ✅ 导入已启动:', data);
            return data;
        }).catch(error => {
            console.error('[API.startImport] ❌ 导入启动失败:', error);
            throw error;
        });
    },

    /**
     * 获取导入进度
     */
    getImportProgress(importId) {
        console.log('[API.getImportProgress] 获取进度，导入 ID:', importId);
        return this.get(`/import/progress/${importId}`).then(data => {
            console.log('[API.getImportProgress] ✅ 进度数据:', data);
            return data;
        }).catch(error => {
            console.error('[API.getImportProgress] ❌ 获取进度失败:', error);
            throw error;
        });
    },

    /**
     * 取消导入
     */
    cancelImport(importId) {
        console.log('[API.cancelImport] 取消导入，导入 ID:', importId);
        return this.post(`/import/cancel/${importId}`, {}).then(data => {
            console.log('[API.cancelImport] ✅ 导入已取消:', data);
            return data;
        }).catch(error => {
            console.error('[API.cancelImport] ❌ 取消导入失败:', error);
            throw error;
        });
    },

    /**
     * 暂停导入
     */
    pauseImport(importId) {
        console.log('[API.pauseImport] 暂停导入，导入 ID:', importId);
        return this.post(`/import/pause/${importId}`, {}).then(data => {
            console.log('[API.pauseImport] ✅ 导入已暂停:', data);
            return data;
        }).catch(error => {
            console.error('[API.pauseImport] ❌ 暂停导入失败:', error);
            throw error;
        });
    },

    /**
     * 继续导入
     */
    resumeImport(importId) {
        console.log('[API.resumeImport] 继续导入，导入 ID:', importId);
        return this.post(`/import/resume/${importId}`, {}).then(data => {
            console.log('[API.resumeImport] ✅ 导入已继续:', data);
            return data;
        }).catch(error => {
            console.error('[API.resumeImport] ❌ 继续导入失败:', error);
            throw error;
        });
    },



    // ========================================================================
    // 测试 API
    // ========================================================================

    /**
     * 健康检查
     */
    health() {
        console.log('[API.health] 执行健康检查...');
        return this.get('/health').then(data => {
            console.log('[API.health] ✅ 后端服务正常:', data);
            return data;
        }).catch(error => {
            console.error('[API.health] ❌ 健康检查失败（可能后端未启动）:', error);
            throw error;
        });
    },

    /**
     * 测试 API
     */
    test() {
        console.log('[API.test] 执行测试 API...');
        return this.get('/test').then(data => {
            console.log('[API.test] ✅ 测试 API 响应:', data);
            return data;
        }).catch(error => {
            console.error('[API.test] ❌ 测试 API 失败:', error);
            throw error;
        });
    },
};

/**
 * API 工具函数
 */
const APIUtils = {
    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    },

    /**
     * 格式化日期时间
     */
    formatDateTime(dateString) {
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN');
        } catch (e) {
            return dateString;
        }
    },

    /**
     * 格式化日期
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('zh-CN');
        } catch (e) {
            return dateString;
        }
    },

    /**
     * 延迟函数
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    /**
     * 防抖函数
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * 节流函数
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
};

/**
 * 全局错误处理
 */
window.addEventListener('unhandledrejection', event => {
    console.error('未捕获的异常:', event.reason);
    // 可以在这里添加统一的错误处理逻辑
});

// 导出和暴露到全局作用域
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API, APIUtils };
}

// 暴露到全局作用域，以兼容各种调用方式
window.API = API;
window.api = API;  // 小写版本，便于使用
window.APIUtils = APIUtils;
