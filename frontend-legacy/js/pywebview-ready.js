/**
 * PyWebView API 准备就绪监听器
 * 
 * 提供 window.pywebviewReady 对象用于检测 PyWebView API 何时可用
 * 解决问题：PyWebView 的 API 注入需要时间，应用需要等待 API 准备就绪
 */

(function() {
    'use strict';
    
    console.log('[pywebview-ready.js] 初始化 PyWebView 准备就绪检测器...');
    
    /**
     * PyWebView 准备状态对象
     */
    window.pywebviewReady = {
        // 状态标志
        isReady: false,
        isInitialized: false,
        
        // 回调队列
        callbacks: [],
        
        /**
         * 等待 PyWebView API 准备就绪
         * @param {number} timeout - 超时时间（毫秒），默认 5000
         * @returns {Promise} - 返回 Promise，成功时 resolve，超时或错误时 reject
         * @example
         *   try {
         *       await window.pywebviewReady.wait(5000);
         *       console.log('API 已准备');
         *   } catch (err) {
         *       console.error('API 准备失败:', err);
         *   }
         */
        wait: function(timeout = 5000) {
            const self = this;
            
            return new Promise((resolve, reject) => {
                // 如果已经准备就绪，立即返回
                if (self.isReady) {
                    console.log('[pywebview-ready] API 已准备（缓存状态）');
                    return resolve();
                }
                
                // 设置超时
                const timeoutId = setTimeout(() => {
                    // 从回调队列中移除此项
                    const index = self.callbacks.indexOf(onReady);
                    if (index !== -1) {
                        self.callbacks.splice(index, 1);
                    }
                    reject(new Error('PyWebView API 准备超时（' + timeout + 'ms）'));
                }, timeout);
                
                // 定义回调函数
                const onReady = () => {
                    clearTimeout(timeoutId);
                    resolve();
                };
                
                // 加入回调队列
                self.callbacks.push(onReady);
            });
        },
        
        /**
         * 标记 API 已准备（由 PyWebView 自动调用或由检测器调用）
         */
        markReady: function() {
            if (this.isReady) {
                return;  // 已经标记过，避免重复
            }
            
            this.isReady = true;
            console.log('[pywebview-ready] ✅ PyWebView API 已准备就绪');
            
            // 执行所有待处理的回调
            const callbacks = this.callbacks.slice();
            this.callbacks = [];
            
            callbacks.forEach(callback => {
                try {
                    callback();
                } catch (err) {
                    console.error('[pywebview-ready] 回调执行失败:', err);
                }
            });
        }
    };
    
    /**
     * 方案 1: 监听 PyWebView 官方事件
     * PyWebView 会在 API 注入时触发 'pywebviewready' 事件
     */
    window.addEventListener('pywebviewready', () => {
        console.log('[pywebview-ready] 捕获 pywebviewready 事件');
        window.pywebviewReady.markReady();
    });
    
    /**
     * 方案 2: 定期检查 window.pywebview 是否存在
     * 这是备选方案，用于兼容不同版本的 PyWebView
     */
    let detectionRetries = 0;
    const maxRetries = 100;  // 最多等待 10 秒（100 * 100ms）
    
    const checkApiReady = () => {
        // 检查 PyWebView API 是否可用
        if (window.pywebview && window.pywebview.api) {
            console.log('[pywebview-ready] 检测到 PyWebView API 已注入');
            window.pywebviewReady.markReady();
            return;
        }
        
        // 继续检测
        if (detectionRetries < maxRetries) {
            detectionRetries++;
            setTimeout(checkApiReady, 100);
        } else {
            console.warn('[pywebview-ready] PyWebView API 准备超时（10秒）');
            // 不自动标记为准备就绪，由调用者处理超时
        }
    };
    
    // 启动检测（延迟 100ms 以确保 PyWebView 有时间注入 API）
    setTimeout(checkApiReady, 100);
    
    /**
     * 方案 3: 监听 DOMContentLoaded 事件后再检查一次
     * 这是最后的保险方案
     */
    document.addEventListener('DOMContentLoaded', () => {
        // 如果仍未准备，再次检查
        if (!window.pywebviewReady.isReady && window.pywebview && window.pywebview.api) {
            console.log('[pywebview-ready] DOMContentLoaded 时检测到 API 已可用');
            window.pywebviewReady.markReady();
        }
    });
    
    console.log('[pywebview-ready.js] 初始化完成');
})();
