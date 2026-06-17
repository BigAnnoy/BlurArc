/**
 * i18n 国际化模块
 * 支持中文（zh）和英文（en）
 * 用法：
 *   I18n.t('key')             - 获取翻译文本
 *   I18n.setLanguage('en')    - 切换语言并刷新页面文本
 *   I18n.getLanguage()        - 获取当前语言代码
 */

const I18n = (() => {
    // ─── 语言包 ──────────────────────────────────────────────────────
    const LOCALES = {
        zh: {
            // 通用
            'app.name': 'Blur Arc',
            'common.close': '关闭',
            'common.confirm': '确认',
            'common.cancel': '取消',
            'common.loading': '加载中...',
            'common.change': '更改...',
            'common.save': '保存',

            // 标题栏
            'header.settings': '设置',
            'header.help': '帮助',

            // 侧边栏 / 统计
            'sidebar.title': '相册',
            'stats.photos': '张照片',
            'stats.videos': '个视频',
            'stats.total': '共',

            // 相册浏览器
            'browser.welcome': '👈 选择左侧的目录查看照片',
            'browser.no_media': '此目录下没有媒体文件',
            'browser.loading': '正在加载...',
            'browser.filter.all': '全部',
            'browser.filter.photos': '照片',
            'browser.filter.videos': '视频',
            'browser.year_jump': '跳转年份',

            // 导入
            'import.btn': '导入照片',
            'import.title': '导入照片',
            'import.step1': '步骤 1: 选择源目录',
            'import.step2': '步骤 2: 预览文件',
            'import.step3': '步骤 3: 导入进度',
            'import.mode.copy': '复制',
            'import.mode.move': '移动',
            'import.mode.copy_desc': '将照片复制到相册，源文件保留不变',
            'import.mode.move_desc': '将照片移动到相册，导入成功后源文件将被删除',
            'import.mode.title': '选择导入方式',
            'import.mode.desc': '请选择照片的导入方式：',
            'import.source.label': '源目录路径',
            'import.source.placeholder': '请选择或输入源目录路径',
            'import.source.help': '支持的格式：JPG、PNG、MP4、MOV 等 20+ 种媒体格式',
            'import.btn.confirm': '确认',
            'import.btn.start': '开始导入',
            'import.btn.cancel_import': '取消导入',
            'import.btn.pause': '暂停',
            'import.tab.date_folders': '按日期查看',
            'import.tab.target_duplicates': '目标重复',
            'import.tab.source_duplicates': '源重复',

            // 预览
            'preview.title': '照片预览',
            'preview.prev': '上一张',
            'preview.next': '下一张',
            'preview.close': '关闭',
            'preview.open_file': '打开文件',
            'preview.exif.title': '拍摄参数',
            'preview.loading': '加载中...',
            'preview.unsupported': '当前浏览器无法播放此格式',
            'preview.unsupported_hint': '请使用下方"打开文件"按钮，用系统播放器打开',
            'preview.zoom_reset': '双击重置',

            // EXIF
            'exif.camera': '相机',
            'exif.lens': '镜头',
            'exif.focal': '焦距',
            'exif.aperture': '光圈',
            'exif.shutter': '快门',
            'exif.iso': 'ISO',
            'exif.datetime': '拍摄时间',
            'exif.gps': 'GPS',

            // 设置
            'settings.title': '设置',
            'settings.album_path': '相册路径',
            'settings.album_path_desc': '当前相册的存储位置',
            'settings.theme': '主题设置',
            'settings.theme.system': '跟随系统设置',
            'settings.theme.light': '亮色',
            'settings.theme.dark': '暗色',
            'settings.language': '界面语言',
            'settings.language.zh': '中文',
            'settings.language.en': 'English',
            'settings.clear_cache': '清空缓存',
            'settings.ffmpeg': 'FFmpeg',
            'settings.ffmpeg.checking': '检查中...',
            'settings.ffmpeg.ok': '✓ 已安装',
            'settings.ffmpeg.missing': '✗ 未安装',
            'settings.ffmpeg.error': '✗ 检查失败',

            // 初始化屏幕
            'init.welcome': '欢迎使用 Blur Arc',
            'init.desc': '首次使用需要选择相册存储位置',
            'init.select_btn': '📁 选择相册位置',
            'init.selected': '已选择:',
            'init.confirm_btn': '✓ 确认',

            // 文件删除
            'delete.confirm': '确定要删除选中的 {n} 个文件吗？此操作不可撤销。',
            'delete.success': '已删除 {n} 个文件',
            'delete.error': '删除失败',
        },

        en: {
            // General
            'app.name': 'Blur Arc',
            'common.close': 'Close',
            'common.confirm': 'Confirm',
            'common.cancel': 'Cancel',
            'common.loading': 'Loading...',
            'common.change': 'Change...',
            'common.save': 'Save',

            // Header
            'header.settings': 'Settings',
            'header.help': 'Help',

            // Sidebar / Stats
            'sidebar.title': 'Album',
            'stats.photos': 'photos',
            'stats.videos': 'videos',
            'stats.total': 'Total',

            // Browser
            'browser.welcome': '👈 Select a folder on the left to view photos',
            'browser.no_media': 'No media files in this folder',
            'browser.loading': 'Loading...',
            'browser.filter.all': 'All',
            'browser.filter.photos': 'Photos',
            'browser.filter.videos': 'Videos',
            'browser.year_jump': 'Jump to year',

            // Import
            'import.btn': 'Import Photos',
            'import.title': 'Import Photos',
            'import.step1': 'Step 1: Select Source Folder',
            'import.step2': 'Step 2: Preview Files',
            'import.step3': 'Step 3: Import Progress',
            'import.mode.copy': 'Copy',
            'import.mode.move': 'Move',
            'import.mode.copy_desc': 'Copy photos to album, source files remain unchanged',
            'import.mode.move_desc': 'Move photos to album, source files will be deleted after import',
            'import.mode.title': 'Choose Import Mode',
            'import.mode.desc': 'Please choose how to import your photos:',
            'import.source.label': 'Source Folder Path',
            'import.source.placeholder': 'Select or enter source folder path',
            'import.source.help': 'Supported formats: JPG, PNG, MP4, MOV and 20+ more',
            'import.btn.confirm': 'Confirm',
            'import.btn.start': 'Start Import',
            'import.btn.cancel_import': 'Cancel Import',
            'import.btn.pause': 'Pause',
            'import.tab.date_folders': 'View by Date',
            'import.tab.target_duplicates': 'Target Duplicates',
            'import.tab.source_duplicates': 'Source Duplicates',

            // Preview
            'preview.title': 'Photo Preview',
            'preview.prev': 'Previous',
            'preview.next': 'Next',
            'preview.close': 'Close',
            'preview.open_file': 'Open File',
            'preview.exif.title': 'EXIF Info',
            'preview.loading': 'Loading...',
            'preview.unsupported': 'This format is not supported by the current browser',
            'preview.unsupported_hint': 'Use the "Open File" button below to play with your system player',
            'preview.zoom_reset': 'Double-click to reset',

            // EXIF
            'exif.camera': 'Camera',
            'exif.lens': 'Lens',
            'exif.focal': 'Focal Length',
            'exif.aperture': 'Aperture',
            'exif.shutter': 'Shutter',
            'exif.iso': 'ISO',
            'exif.datetime': 'Date Taken',
            'exif.gps': 'GPS',

            // Settings
            'settings.title': 'Settings',
            'settings.album_path': 'Album Path',
            'settings.album_path_desc': 'Storage location of the current album',
            'settings.theme': 'Theme',
            'settings.theme.system': 'Follow System',
            'settings.theme.light': 'Light',
            'settings.theme.dark': 'Dark',
            'settings.language': 'Language',
            'settings.language.zh': '中文',
            'settings.language.en': 'English',
            'settings.clear_cache': 'Clear Cache',
            'settings.ffmpeg': 'FFmpeg',
            'settings.ffmpeg.checking': 'Checking...',
            'settings.ffmpeg.ok': '✓ Installed',
            'settings.ffmpeg.missing': '✗ Not installed',
            'settings.ffmpeg.error': '✗ Check failed',

            // Init screen
            'init.welcome': 'Welcome to Blur Arc',
            'init.desc': 'Please select a folder to store your album',
            'init.select_btn': '📁 Select Album Folder',
            'init.selected': 'Selected:',
            'init.confirm_btn': '✓ Confirm',

            // Delete
            'delete.confirm': 'Delete {n} selected file(s)? This cannot be undone.',
            'delete.success': 'Deleted {n} file(s)',
            'delete.error': 'Delete failed',
        }
    };

    // ─── 内部状态 ────────────────────────────────────────────────────
    const STORAGE_KEY = 'blurarc_language';
    // BUG-017：某些 WebView 沙箱环境下 localStorage 访问会抛 SecurityError
    // 用 try-catch 包裹，失败时降级到默认语言 'zh'，确保模块不崩溃
    let _lang;
    try {
        _lang = localStorage.getItem(STORAGE_KEY) || 'zh';
    } catch (e) {
        console.warn('[i18n] localStorage 不可用，使用默认语言 zh:', e);
        _lang = 'zh';
    }

    // ─── 公共 API ────────────────────────────────────────────────────

    /** 获取当前语言代码 */
    function getLanguage() {
        return _lang;
    }

    /**
     * 设置语言，刷新页面所有 data-i18n 元素，并持久化到 localStorage 和后端
     * @param {string} lang - 'zh' 或 'en'
     * @param {boolean} [saveToServer=true] - 是否同步到后端
     */
    async function setLanguage(lang, saveToServer = true) {
        if (lang !== 'zh' && lang !== 'en') return;
        _lang = lang;
        // BUG-017：localStorage 写入同样可能抛 SecurityError
        try {
            localStorage.setItem(STORAGE_KEY, lang);
        } catch (e) {
            console.warn('[i18n] 无法写入 localStorage:', e);
        }
        _applyAll();

        if (saveToServer) {
            try {
                await fetch('/api/settings/language', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language: lang })
                });
            } catch (e) {
                console.warn('[i18n] Failed to save language preference to server:', e);
            }
        }
    }

    /**
     * 翻译 key，支持 {n} 等简单占位符替换
     * @param {string} key
     * @param {Object} [vars] - 占位符变量，如 { n: 5 }
     * @returns {string}
     */
    function t(key, vars) {
        const dict = LOCALES[_lang] || LOCALES['zh'];
        let text = dict[key] !== undefined ? dict[key] : (LOCALES['zh'][key] || key);
        if (vars) {
            Object.entries(vars).forEach(([k, v]) => {
                text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
            });
        }
        return text;
    }

    /**
     * 应用翻译到所有带 data-i18n 属性的 DOM 元素
     * data-i18n="key"           → 设置 textContent
     * data-i18n-placeholder="key" → 设置 placeholder
     * data-i18n-title="key"    → 设置 title / aria-label
     */
    function _applyAll() {
        // textContent
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = t(key);
        });
        // placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
        });
        // aria-label / title
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const val = t(el.getAttribute('data-i18n-title'));
            el.title = val;
            el.setAttribute('aria-label', val);
        });
        // <html lang>
        document.documentElement.lang = _lang === 'zh' ? 'zh-CN' : 'en';
    }

    /**
     * 首次启动时：若 localStorage 无记录，查询后端已保存偏好；
     * 若后端也没有，则检测系统语言并自动设置。
     * 调用时机：DOMContentLoaded 之后，其他模块初始化之前。
     */
    async function initLanguage() {
        // BUG-017：读取 localStorage 同样要防 SecurityError
        let stored;
        try {
            stored = localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            stored = null;
        }

        if (!stored) {
            // 1. 先看后端有没有保存过偏好
            try {
                const res = await fetch('/api/settings/language');
                const data = await res.json();
                if (data.language) {
                    await setLanguage(data.language, false); // 后端已有，不必再写回
                    return;
                }
            } catch (e) { /* ignore */ }

            // 2. 检测系统语言
            try {
                const res = await fetch('/api/system/locale');
                const data = await res.json();
                const detected = data.language || 'zh';
                await setLanguage(detected, true);
                return;
            } catch (e) { /* ignore */ }
        }

        // 3. 用 localStorage 里的值（或默认 zh）刷新一次 DOM
        _applyAll();
    }

    // ─── 导出 ────────────────────────────────────────────────────────
    return { t, getLanguage, setLanguage, initLanguage };
})();

window.I18n = I18n;
