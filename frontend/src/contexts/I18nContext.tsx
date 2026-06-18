import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { api } from '../services/api';

type Language = 'zh' | 'en';

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

// Translation dictionaries
const translations: Record<Language, Record<string, string>> = {
  zh: {
    // Common
    'common.close': '关闭',
    'common.confirm': '确认',
    'common.cancel': '取消',
    'common.save': '保存',
    'common.loading': '加载中...',
    'common.delete': '删除',
    'common.select': '选择',
    'common.selectAll': '全选',
    'common.cancelSelect': '取消全选',
    'common.cancelSelectMode': '取消',

    // Header
    'header.toggleTheme': '切换主题',
    'header.settings': '设置',

    // Sidebar
    'sidebar.browseByYear': '按年份浏览',
    'sidebar.folders': '文件夹',
    'sidebar.importPhotos': '导入照片',
    'sidebar.totalFiles': '总文件个数',
    'sidebar.totalSize': '总文件大小',

    // Main Content
    'main.selectToBrowse': '选择目录开始浏览',
    'main.clickToBrowse': '点击左侧目录树中的年份或月份文件夹，即可查看其中的照片和视频',
    'main.loading': '加载中...',
    'main.selected': '已选 {count} 张',
    'main.photoCount': '{count}张',
    'main.deleteSelected': '删除',
    'main.selectMode': '选择',

    // Photo Preview
    'preview.title': '照片预览',
    'preview.close': '关闭',
    'preview.openFile': '打开文件',
    'preview.size': '大小',
    'preview.date': '日期',
    'preview.duration': '时长',
    'preview.unknown': '未知',

    // Delete Dialog
    'delete.title': '确认删除',
    'delete.confirmMessage': '确定要删除选中的照片吗？',
    'delete.willDelete': '将删除 {count} 张照片',
    'delete.cannotUndo': '此操作不可撤销',
    'delete.deleting': '删除中...',
    'delete.confirmButton': '确认删除',
    'delete.failed': '删除失败',
    'delete.success': '删除成功',

    // Settings Dialog
    'settings.title': '设置',
    'settings.albumPath': '相册路径',
    'settings.albumPathDesc': '当前相册的存储位置',
    'settings.change': '更改...',
    'settings.theme': '主题设置',
    'settings.themeSystem': '跟随系统设置',
    'settings.themeLight': '亮色',
    'settings.themeDark': '暗色',
    'settings.language': '界面语言',
    'settings.languageZh': '中文',
    'settings.languageEn': 'English',
    'settings.clearCache': '清空缩略图缓存',
    'settings.clearing': '清空中...',
    'settings.cacheCleared': '已清空缓存，释放 {size} MB',
    'settings.rebuildIndex': '重建索引（数据库 + 缩略图）',
    'settings.rebuilding': '重建中...',
    'settings.rebuildProgress': '{progress}%',
    'settings.rebuildStarted': '已清空 {count} 个缩略图，开始重建索引',
    'settings.rebuildComplete': '索引重建完成',
    'settings.rebuildFailed': '重建失败: {message}',
    'settings.themeChanged': '主题已更改',
    'settings.languageChanged': '语言已更改',
    'settings.albumPathChanged': '相册路径已更改',
    'settings.loadFailed': '加载设置失败',
    'settings.themeChangeFailed': '更改主题失败',
    'settings.languageChangeFailed': '更改语言失败',
    'settings.albumPathChangeFailed': '更改相册路径失败',
    'settings.clearCacheFailed': '清空缓存失败',
    'settings.rebuildFailedGeneric': '重建索引失败',
    'settings.queryProgressFailed': '查询进度失败',

    // Import Dialog
    'import.title': '导入照片',
    'import.checking': '检查源文件夹',
    'import.preview': '预览导入',
    'import.progress': '导入进度',
    'import.sourcePath': '源文件夹路径',
    'import.sourcePathPlaceholder': '输入源文件夹路径或点击浏览',
    'import.confirm': '确认',
    'import.cancelCheck': '取消检查',
    'import.checkFailed': '检查失败',
    'import.startCheckFailed': '启动检查失败',
    'import.enterPathFirst': '请输入源文件夹路径',
    'import.checkingStatus': '正在启动检查...',
    'import.cancelled': '已取消',

    // Import Mode Dialog
    'importMode.title': '选择导入方式',
    'importMode.copy': '复制',
    'importMode.copyDesc': '将照片复制到相册，源文件保留不变',
    'importMode.move': '移动',
    'importMode.moveDesc': '将照片移动到相册，导入成功后源文件将被删除',
    'importMode.cancel': '取消',

    // Step 2 Preview
    'preview.loadFailed': '加载预览数据失败',
    'preview.noMedia': '没有可导入的媒体文件',
    'preview.noMediaDesc': '选择的文件夹中没有找到图片、视频或音频文件。',
    'preview.backToSelect': '返回重新选择',
    'preview.sourcePath': '源路径：',
    'preview.totalFiles': '总文件个数',
    'preview.totalSize': '总文件大小',
    'preview.timeline': '时间线',
    'preview.inAlbum': '已在相册',
    'preview.sourceDuplicates': '文件夹内重复',
    'preview.back': '返回',
    'preview.startImport': '开始导入',

    // Timeline Tab
    'timeline.description': '按拍摄日期浏览待导入的照片，确认内容无误后点击「开始导入」。',
    'timeline.toImport': '待导入：',
    'timeline.files': '{count} 个文件',
    'timeline.cancel': '取消',
    'timeline.selectAll': '全选',
    'timeline.cancelSelect': '取消全选',
    'timeline.deleteSelected': '删除所选',
    'timeline.select': '选择',
    'timeline.dateFilter': '日期筛选',
    'timeline.noFiles': '没有文件',
    'timeline.photoPreview': '照片预览',
    'timeline.selectDate': '请选择左侧的日期查看照片',
    'timeline.deleteConfirm': '确定要删除选中的 {count} 个文件吗？此操作不可撤销。',

    // Target Duplicates Tab
    'target.description': '以下照片与相册中的文件内容完全相同。导入后将以 _dup 后缀保存，你可以事后手动删除，或现在从源文件夹删除以跳过导入。',
    'target.inAlbum': '已在相册：',
    'target.groups': '{count} 组',
    'target.selectDuplicates': '选择重复照片',
    'target.selectedSourceFiles': '已选 {count} 个源文件',
    'target.deleteSelection': '删除选择',
    'target.selectedSummary': '已选中 {count} 个源文件（不在相册中的重复文件）',
    'target.clearSelection': '清除选择',
    'target.duplicateFiles': '重复文件',
    'target.noDuplicates': '没有发现相册中已有的文件',
    'target.duplicatePreview': '重复照片预览',
    'target.selectGroup': '请选择左侧的重复文件组查看照片',
    'target.album': '相册',
    'target.duplicateWithAlbum': '与相册中文件重复',
    'target.deleteConfirm': '确定要删除选中的 {count} 个文件吗？此操作不可撤销。',

    // Source Duplicates Tab
    'source.description': '以下是你选择的文件夹中自身存在的重复文件（同一张照片有多个副本）。建议在导入前删除多余的副本，只保留一份。',
    'source.inFolder': '文件夹内重复：',
    'source.groups': '{count} 组',
    'source.selectDuplicates': '选择重复照片',
    'source.deleteSelection': '删除选择',
    'source.duplicateGroups': '重复文件组',
    'source.noDuplicates': '没有发现源重复文件',
    'source.duplicatePreview': '重复照片预览',
    'source.selectGroup': '请选择左侧的重复文件组查看照片',
    'source.duplicateFiles': '{count} 个重复文件',
    'source.deleteConfirm': '确定要删除选中的 {count} 个文件吗？此操作不可撤销。',

    // Step 3 Importing
    'importing.complete': '导入完成',
    'importing.failed': '导入失败',
    'importing.paused': '已暂停',
    'importing.scanning': '正在扫描...',
    'importing.importing': '正在导入',
    'importing.files': '{current} / {total} 个文件',
    'importing.importFailed': '导入失败',
    'importing.resume': '继续导入',
    'importing.pause': '暂停',
    'importing.cancel': '取消导入',
    'importing.close': '关闭',
    'importing.cancelConfirm': '确定要取消导入吗？已导入的文件将保留，但未完成的部分将停止。',
    'importing.cancelled': '导入已取消',
    'importing.cancelFailed': '取消导入失败',
    'importing.startFailed': '启动导入失败',
    'importing.deletedFiles': '已删除 {count} 个文件',
    'importing.resultImported': '已导入',
    'importing.resultDuplicated': '重复',
    'importing.resultFailed': '失败',
    'importing.resultTotal': '总数',
    'importing.starting': '启动中...',

    // Photo Preview Modal
    'photoPreview.preview': '预览',
    'photoPreview.fileName': '文件名',
    'photoPreview.fileSize': '文件大小',
    'photoPreview.filePath': '文件路径',
    'photoPreview.close': '关闭',
    'photoPreview.openFile': '打开文件',

    // Check Stage Text
    'checkStage.queued': '任务已排队',
    'checkStage.scanning': '正在扫描源目录...',
    'checkStage.grouping': '正在按日期整理预览...',
    'checkStage.source_duplicates': '正在检测源重复...',
    'checkStage.target_duplicates': '正在检测目标重复...',
    'checkStage.completed': '检查完成',
    'checkStage.failed': '检查失败',

    // App initialization
    'app.connectionFailed': '连接服务器失败，请重启应用',
    'app.loadPhotosFailed': '加载照片失败',

    // Phone Import
    'phoneImport.title': '从手机导入',
    'phoneImport.subtitle': '扫码无线传输',
    'phoneImport.ensureWifi': '确保手机和电脑在同一 WiFi 网络',
    'phoneImport.scanQr': '手机扫码或浏览器访问以下地址',
    'phoneImport.starting': '正在启动上传服务...',
    'phoneImport.receiving': '等待手机上传...',
    'phoneImport.filesUploaded': '已上传 {count} 个文件，共 {size}',
    'phoneImport.stopReceiving': '停止接收',
    'phoneImport.startImport': '开始导入',
    'phoneImport.noFiles': '请先上传至少一个文件',
    'phoneImport.serverError': '上传服务启动失败，请检查防火墙设置',
    'phoneImport.entry': '从手机导入',
    'phoneImport.localImport': '本地导入',
    'phoneImport.localImportDesc': '从本地磁盘/U盘/移动硬盘选择文件夹',
    'phoneImport.selectMode': '请选择导入方式',
    'common.retry': '重试',
    'phoneImport.resumeTitle': '发现上次未完成的导入',
    'phoneImport.resumeDetail': '{date} — {count} 个文件 ({size})',
    'phoneImport.resumeContinue': '继续上传',
    'phoneImport.resumeDiscard': '放弃，重新开始',

    // Welcome Screen
    'welcome.title': '欢迎使用 Blur Arc',
    'welcome.subtitle': '让我们开始设置您的相册',
    'welcome.description': '请选择一个空文件夹作为相册存储位置。应用会按年份和月份自动整理导入的照片和视频。',
    'welcome.selectAlbum': '选择相册文件夹',
    'welcome.selecting': '正在设置...',
    'welcome.hint': '建议选择空文件夹，您可以随时在设置中更改相册路径',
    'welcome.selectFailed': '选择相册路径失败',
    'welcome.folderNotSelected': '未选择文件夹',
    'welcome.selectingFolder': '正在选择文件夹...',
    'welcome.buildingIndex': '正在建立索引和缩略图...',
    'welcome.processing': '处理中',
    'welcome.rebuildFailed': '建立索引失败',
    'welcome.rebuildTimeout': '建立索引超时',

    // Mobile Access
    'mobileAccess.title': '移动设备访问',
    'mobileAccess.service': '移动接入服务',
    'mobileAccess.running': '运行中',
    'mobileAccess.stopped': '已停止',
    'mobileAccess.connectionInfo': '连接信息',
    'mobileAccess.newDevice': '新设备配对',
    'mobileAccess.scanQrHint': '使用 Blur Arc App 扫描此二维码',
    'mobileAccess.pairRequest': '请求连接相册',
    'mobileAccess.pairedDevices': '已配对设备',
    'mobileAccess.revoke': '撤销',
    'mobileAccess.revokeAll': '撤销全部',
    'mobileAccess.entry': '移动设备',

    // Pairing Mode (新流程)
    'pairing.title': '配对模式',
    'pairing.description': '开启后广播服务，允许新设备配对',
    'pairing.start': '点击开启',
    'pairing.stop': '停止广播',
    'pairing.broadcasting': '正在广播...',
    'pairing.deviceFound': '等待设备连接...',
    'pairing.confirmPairing': '确认配对',
    'pairing.rejectPairing': '拒绝',
    'pairing.pairingCode': '配对码',
    'pairing.enterCodeOnPhone': '请在手机上输入此配对码',
    'pairing.codeExpiresIn': '有效期: {seconds} 秒',
    'pairing.cancelPairing': '取消配对',
    'pairing.requestFrom': '{device} 请求配对',
  },
  en: {
    // Common
    'common.close': 'Close',
    'common.confirm': 'Confirm',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.loading': 'Loading...',
    'common.delete': 'Delete',
    'common.select': 'Select',
    'common.selectAll': 'Select All',
    'common.cancelSelect': 'Deselect All',
    'common.cancelSelectMode': 'Cancel',

    // Header
    'header.toggleTheme': 'Toggle Theme',
    'header.settings': 'Settings',

    // Sidebar
    'sidebar.browseByYear': 'Browse by Year',
    'sidebar.folders': 'Folders',
    'sidebar.importPhotos': 'Import Photos',
    'sidebar.totalFiles': 'Total Files',
    'sidebar.totalSize': 'Total Size',

    // Main Content
    'main.selectToBrowse': 'Select a folder to browse',
    'main.clickToBrowse': 'Click on year or month folders in the left tree to view photos and videos',
    'main.loading': 'Loading...',
    'main.selected': '{count} selected',
    'main.photoCount': '{count}',
    'main.deleteSelected': 'Delete',
    'main.selectMode': 'Select',

    // Photo Preview
    'preview.title': 'Photo Preview',
    'preview.close': 'Close',
    'preview.openFile': 'Open File',
    'preview.size': 'Size',
    'preview.date': 'Date',
    'preview.duration': 'Duration',
    'preview.unknown': 'Unknown',

    // Delete Dialog
    'delete.title': 'Confirm Delete',
    'delete.confirmMessage': 'Are you sure you want to delete the selected photos?',
    'delete.willDelete': 'Will delete {count} photos',
    'delete.cannotUndo': 'This action cannot be undone',
    'delete.deleting': 'Deleting...',
    'delete.confirmButton': 'Confirm Delete',
    'delete.failed': 'Delete failed',
    'delete.success': 'Deleted successfully',

    // Settings Dialog
    'settings.title': 'Settings',
    'settings.albumPath': 'Album Path',
    'settings.albumPathDesc': 'Storage location of the current album',
    'settings.change': 'Change...',
    'settings.theme': 'Theme',
    'settings.themeSystem': 'Follow System',
    'settings.themeLight': 'Light',
    'settings.themeDark': 'Dark',
    'settings.language': 'Language',
    'settings.languageZh': '中文',
    'settings.languageEn': 'English',
    'settings.clearCache': 'Clear Thumbnail Cache',
    'settings.clearing': 'Clearing...',
    'settings.cacheCleared': 'Cache cleared, freed {size} MB',
    'settings.rebuildIndex': 'Rebuild Index (Database + Thumbnails)',
    'settings.rebuilding': 'Rebuilding...',
    'settings.rebuildProgress': '{progress}%',
    'settings.rebuildStarted': 'Cleared {count} thumbnails, rebuilding index',
    'settings.rebuildComplete': 'Index rebuild complete',
    'settings.rebuildFailed': 'Rebuild failed: {message}',
    'settings.themeChanged': 'Theme changed',
    'settings.languageChanged': 'Language changed',
    'settings.albumPathChanged': 'Album path changed',
    'settings.loadFailed': 'Failed to load settings',
    'settings.themeChangeFailed': 'Failed to change theme',
    'settings.languageChangeFailed': 'Failed to change language',
    'settings.albumPathChangeFailed': 'Failed to change album path',
    'settings.clearCacheFailed': 'Failed to clear cache',
    'settings.rebuildFailedGeneric': 'Failed to rebuild index',
    'settings.queryProgressFailed': 'Failed to query progress',

    // Import Dialog
    'import.title': 'Import Photos',
    'import.checking': 'Checking Source Folder',
    'import.preview': 'Preview Import',
    'import.progress': 'Import Progress',
    'import.sourcePath': 'Source Folder Path',
    'import.sourcePathPlaceholder': 'Enter source folder path or click to browse',
    'import.confirm': 'Confirm',
    'import.cancelCheck': 'Cancel Check',
    'import.checkFailed': 'Check failed',
    'import.startCheckFailed': 'Failed to start check',
    'import.enterPathFirst': 'Please enter source folder path',
    'import.checkingStatus': 'Starting check...',
    'import.cancelled': 'Cancelled',

    // Import Mode Dialog
    'importMode.title': 'Choose Import Mode',
    'importMode.copy': 'Copy',
    'importMode.copyDesc': 'Copy photos to album, source files remain unchanged',
    'importMode.move': 'Move',
    'importMode.moveDesc': 'Move photos to album, source files will be deleted after import',
    'importMode.cancel': 'Cancel',

    // Step 2 Preview
    'preview.loadFailed': 'Failed to load preview data',
    'preview.noMedia': 'No media files to import',
    'preview.noMediaDesc': 'No images, videos, or audio files found in the selected folder.',
    'preview.backToSelect': 'Back to Select',
    'preview.sourcePath': 'Source Path:',
    'preview.totalFiles': 'Total Files',
    'preview.totalSize': 'Total Size',
    'preview.timeline': 'Timeline',
    'preview.inAlbum': 'In Album',
    'preview.sourceDuplicates': 'Source Duplicates',
    'preview.back': 'Back',
    'preview.startImport': 'Start Import',

    // Timeline Tab
    'timeline.description': 'Browse photos to import by date. Click "Start Import" after confirming.',
    'timeline.toImport': 'To Import:',
    'timeline.files': '{count} files',
    'timeline.cancel': 'Cancel',
    'timeline.selectAll': 'Select All',
    'timeline.cancelSelect': 'Deselect All',
    'timeline.deleteSelected': 'Delete Selected',
    'timeline.select': 'Select',
    'timeline.dateFilter': 'Date Filter',
    'timeline.noFiles': 'No files',
    'timeline.photoPreview': 'Photo Preview',
    'timeline.selectDate': 'Select a date on the left to view photos',
    'timeline.deleteConfirm': 'Delete {count} selected file(s)? This cannot be undone.',

    // Target Duplicates Tab
    'target.description': 'These photos are identical to files already in your album. They will be saved with _dup suffix. You can delete them later or remove from source folder now to skip import.',
    'target.inAlbum': 'In Album:',
    'target.groups': '{count} groups',
    'target.selectDuplicates': 'Select Duplicates',
    'target.selectedSourceFiles': '{count} source files selected',
    'target.deleteSelection': 'Delete Selection',
    'target.selectedSummary': 'Selected {count} source files (duplicates not in album)',
    'target.clearSelection': 'Clear Selection',
    'target.duplicateFiles': 'Duplicate Files',
    'target.noDuplicates': 'No duplicates found in album',
    'target.duplicatePreview': 'Duplicate Preview',
    'target.selectGroup': 'Select a duplicate group on the left to view photos',
    'target.album': 'Album',
    'target.duplicateWithAlbum': 'Duplicate with album file',
    'target.deleteConfirm': 'Delete {count} selected file(s)? This cannot be undone.',

    // Source Duplicates Tab
    'source.description': 'These are duplicate files within your selected folder (multiple copies of the same photo). Consider deleting extras before import, keeping only one copy.',
    'source.inFolder': 'In Folder:',
    'source.groups': '{count} groups',
    'source.selectDuplicates': 'Select Duplicates',
    'source.deleteSelection': 'Delete Selection',
    'source.duplicateGroups': 'Duplicate Groups',
    'source.noDuplicates': 'No source duplicates found',
    'source.duplicatePreview': 'Duplicate Preview',
    'source.selectGroup': 'Select a duplicate group on the left to view photos',
    'source.duplicateFiles': '{count} duplicate files',
    'source.deleteConfirm': 'Delete {count} selected file(s)? This cannot be undone.',

    // Step 3 Importing
    'importing.complete': 'Import Complete',
    'importing.failed': 'Import Failed',
    'importing.paused': 'Paused',
    'importing.scanning': 'Scanning...',
    'importing.importing': 'Importing',
    'importing.files': '{current} / {total} files',
    'importing.importFailed': 'Import Failed',
    'importing.resume': 'Resume',
    'importing.pause': 'Pause',
    'importing.cancel': 'Cancel Import',
    'importing.close': 'Close',
    'importing.cancelConfirm': 'Cancel import? Already imported files will be kept, but incomplete parts will stop.',
    'importing.cancelled': 'Import cancelled',
    'importing.cancelFailed': 'Failed to cancel import',
    'importing.startFailed': 'Failed to start import',
    'importing.deletedFiles': 'Deleted {count} files',
    'importing.resultImported': 'Imported',
    'importing.resultDuplicated': 'Duplicated',
    'importing.resultFailed': 'Failed',
    'importing.resultTotal': 'Total',
    'importing.starting': 'Starting...',

    // Photo Preview Modal
    'photoPreview.preview': 'Preview',
    'photoPreview.fileName': 'File Name',
    'photoPreview.fileSize': 'File Size',
    'photoPreview.filePath': 'File Path',
    'photoPreview.close': 'Close',
    'photoPreview.openFile': 'Open File',

    // Check Stage Text
    'checkStage.queued': 'Task queued',
    'checkStage.scanning': 'Scanning source directory...',
    'checkStage.grouping': 'Organizing by date...',
    'checkStage.source_duplicates': 'Detecting source duplicates...',
    'checkStage.target_duplicates': 'Detecting target duplicates...',
    'checkStage.completed': 'Check complete',
    'checkStage.failed': 'Check failed',

    // App initialization
    'app.connectionFailed': 'Failed to connect to server, please restart the app',
    'app.loadPhotosFailed': 'Failed to load photos',

    // Phone Import
    'phoneImport.title': 'Import from Phone',
    'phoneImport.subtitle': 'Scan to transfer wirelessly',
    'phoneImport.ensureWifi': 'Make sure phone and PC are on the same WiFi',
    'phoneImport.scanQr': 'Scan QR code or visit the address below',
    'phoneImport.starting': 'Starting upload service...',
    'phoneImport.receiving': 'Waiting for uploads...',
    'phoneImport.filesUploaded': '{count} files uploaded, {size} total',
    'phoneImport.stopReceiving': 'Stop Receiving',
    'phoneImport.startImport': 'Start Import',
    'phoneImport.noFiles': 'Please upload at least one file first',
    'phoneImport.serverError': 'Failed to start upload service, check firewall',
    'phoneImport.entry': 'Import from Phone',
    'phoneImport.localImport': 'Local Import',
    'phoneImport.localImportDesc': 'Select a folder from local disk / USB drive',
    'phoneImport.selectMode': 'Choose import method',
    'common.retry': 'Retry',
    'phoneImport.resumeTitle': 'Incomplete import found',
    'phoneImport.resumeDetail': '{date} — {count} files ({size})',
    'phoneImport.resumeContinue': 'Continue Upload',
    'phoneImport.resumeDiscard': 'Discard & Start Over',

    // Welcome Screen
    'welcome.title': 'Welcome to Blur Arc',
    'welcome.subtitle': "Let's set up your album",
    'welcome.description': 'Please select an empty folder as the album storage location. The app will automatically organize imported photos and videos by year and month.',
    'welcome.selectAlbum': 'Select Album Folder',
    'welcome.selecting': 'Setting up...',
    'welcome.hint': 'It is recommended to select an empty folder. You can change the album path anytime in Settings',
    'welcome.selectFailed': 'Failed to select album path',
    'welcome.folderNotSelected': 'No folder selected',
    'welcome.selectingFolder': 'Selecting folder...',
    'welcome.buildingIndex': 'Building index and thumbnails...',
    'welcome.processing': 'Processing',
    'welcome.rebuildFailed': 'Failed to build index',
    'welcome.rebuildTimeout': 'Building index timed out',

    // Mobile Access
    'mobileAccess.title': 'Mobile Access',
    'mobileAccess.service': 'Mobile Access Service',
    'mobileAccess.running': 'Running',
    'mobileAccess.stopped': 'Stopped',
    'mobileAccess.connectionInfo': 'Connection Info',
    'mobileAccess.newDevice': 'New Device Pairing',
    'mobileAccess.scanQrHint': 'Scan with Blur Arc App',
    'mobileAccess.pairRequest': 'Request to connect',
    'mobileAccess.pairedDevices': 'Paired Devices',
    'mobileAccess.revoke': 'Revoke',
    'mobileAccess.revokeAll': 'Revoke All',
    'mobileAccess.entry': 'Mobile',

    // Pairing Mode (新流程)
    'pairing.title': 'Pairing Mode',
    'pairing.description': 'Broadcast service after enabling, allow new devices to pair',
    'pairing.start': 'Tap to Start',
    'pairing.stop': 'Stop Broadcasting',
    'pairing.broadcasting': 'Broadcasting...',
    'pairing.deviceFound': 'Waiting for device...',
    'pairing.confirmPairing': 'Confirm Pairing',
    'pairing.rejectPairing': 'Reject',
    'pairing.pairingCode': 'Pairing Code',
    'pairing.enterCodeOnPhone': 'Enter this code on your phone',
    'pairing.codeExpiresIn': 'Expires in {seconds}s',
    'pairing.cancelPairing': 'Cancel Pairing',
    'pairing.requestFrom': '{device} requests pairing',
  },
};

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('zh');

  // Load language from backend on mount
  useEffect(() => {
    const loadLanguage = async () => {
      try {
        const settings = await api.getSettings();
        if (settings.language === 'zh' || settings.language === 'en') {
          setLanguageState(settings.language);
        }
      } catch (error) {
        console.error('Failed to load language:', error);
      }
    };
    loadLanguage();
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    // Save to backend
    api.updateSettings({ language: lang }).catch((error) => {
      console.error('Failed to save language:', error);
    });
  };

  const t = (key: string, params?: Record<string, string | number>) => {
    let text = translations[language][key] || key;
    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        text = text.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramValue));
      });
    }
    return text;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
}
