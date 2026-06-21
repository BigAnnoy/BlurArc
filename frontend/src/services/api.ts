import type { ImportPhoto, ImportProgress } from '../components/dialogs/ImportDialog/types';
import type { DirNode, YearNode, MonthNode } from '../types';

const API_BASE = '/api';

// 复用 ImportPhoto 类型
export type { ImportPhoto };

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `API error: ${response.status}`);
  }
  return response.json();
}

// 当前导入任务 ID（用于追踪进度）
let currentImportId: string | null = null;

// PyWebView API 类型声明
declare global {
  interface Window {
    pywebview?: {
      api?: {
        select_folder: () => Promise<string>;
      };
    };
  }
}

export const api = {
  // Health check
  health: () => fetchJson<{ status: string }>(`${API_BASE}/health`),

  // Stats
  getStats: () => fetchJson<{ total_files: number; video_count: number; total_size_mb: number; last_import: string }>(`${API_BASE}/album/stats`),

  // Directory tree - 支持多层级目录
  getTree: async () => {
    const response = await fetchJson<DirNode & { type: string }>(`${API_BASE}/album/tree`);

    // 过滤 YYYY-MM 格式的目录（用于按年份浏览）
    const yearMonthDirs: DirNode[] = [];

    for (const item of response.children || []) {
      const match = item.name.match(/^(\d{4})-(\d{2})$/);
      if (match) {
        yearMonthDirs.push(item);
      }
    }

    // 将 YYYY-MM 目录按年份分组
    const yearMap = new Map<string, MonthNode[]>();
    for (const item of yearMonthDirs) {
      const match = item.name.match(/^(\d{4})-(\d{2})$/)!;
      const year = match[1];
      if (!yearMap.has(year)) {
        yearMap.set(year, []);
      }
      yearMap.get(year)!.push({
        name: item.name,
        path: item.path,
        count: item.count,
      });
    }

    // 转换为按年份降序排列的数组
    const yearGroups: YearNode[] = Array.from(yearMap.entries())
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([year, months]) => ({
        year,
        months: months.sort((a, b) => {
          const numA = parseInt(a.name.match(/^(\d{4})-(\d{2})$/)?.[2] || '0');
          const numB = parseInt(b.name.match(/^(\d{4})-(\d{2})$/)?.[2] || '0');
          return numA - numB;
        }),
      }));

    // 构造根目录节点（过滤掉 YYYY-MM 格式目录，避免与"按年份浏览"重复）
    const sortChildren = (children: DirNode[]): DirNode[] => {
      return children
        .filter((child) => !child.name.match(/^(\d{4})-(\d{2})$/))
        .map((child) => ({
          ...child,
          children: child.children ? sortChildren(child.children) : [],
        }))
        .sort((a, b) => a.name.localeCompare(b.name, 'zh'));
    };

    const rootDir: DirNode = {
      name: response.name,
      path: response.path,
      count: response.count,
      children: sortChildren(response.children || []),
    };

    return { tree: yearGroups, rootDir };
  },

  // Photos - 支持分页
  getPhotos: (path: string, page: number = 1, pageSize: number = 100) => fetchJson<{ 
    photos: { id: string; name: string; path: string; size: number; date: string; type: string; duration?: string }[];
    count: number;
    total_pages: number;
    page: number;
    page_size: number;
  }>(`${API_BASE}/album/photos?path=${encodeURIComponent(path)}&page=${page}&page_size=${pageSize}`),

  // Thumbnail
  getThumbnail: (path: string) => `${API_BASE}/album/thumbnail?path=${encodeURIComponent(path)}`,

  // File (for preview)
  getFile: (path: string) => `${API_BASE}/album/file?path=${encodeURIComponent(path)}`,

  // Import
  // 同步检查（简化版，兼容保留）
  checkImport: (sourcePath: string) => fetchJson<{ valid: boolean; count: number }>(`${API_BASE}/import/check`, {
    method: 'POST',
    body: JSON.stringify({ source_path: sourcePath }),
  }),

  // 异步检查（带进度）
  startImportCheck: (sourcePath: string) =>
    fetchJson<{ status: string; check_id: string }>(`${API_BASE}/import/check/start`, {
      method: 'POST',
      body: JSON.stringify({ source_path: sourcePath }),
    }),

  getImportCheckProgress: (checkId: string) =>
    fetchJson<{
      status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
      progress: number;
      stage: 'queued' | 'scanning' | 'grouping' | 'source_duplicates' | 'target_duplicates' | 'completed' | 'failed';
      detail: string;
      result?: {
        status: string;
        source_path: string;
        media_count: number;
        total_size_mb: number;
        date_folders: { name: string; count: number; size: number; files: ImportPhoto[] }[];
        target_duplicates: Record<string, ImportPhoto[]>;
        source_duplicates: Record<string, ImportPhoto[]>;
      };
    }>(`${API_BASE}/import/check/progress/${checkId}`),

  startImport: (sourcePath: string, targetPath: string, mode: 'copy' | 'move') =>
    fetchJson<{ import_id: string }>(`${API_BASE}/import/start`, {
      method: 'POST',
      body: JSON.stringify({
        source_path: sourcePath,
        target_path: targetPath,
        import_mode: mode,
      }),
    }).then((res) => {
      currentImportId = res.import_id;
      return res;
    }),

  getImportProgress: () => {
    if (!currentImportId) {
      return Promise.resolve({ step: 0, total: 0, current: '', status: 'idle' });
    }
    return api.getImportProgressById(currentImportId);
  },

  getImportProgressById: (importId: string) =>
    fetchJson<{
      import_id: string;
      status: string;
      progress: number;
      total_files: number;
      processed_files: number;
      failed_files: number;
      duplicated_files: number;
      current_file: string | null;
      error_message: string | null;
    }>(`${API_BASE}/import/progress/${importId}`).then((data) => ({
      step: data.processed_files,
      total: data.total_files,
      current: data.current_file ?? '',
      status: data.status as ImportProgress['status'],
      progress: data.progress,
      error: data.error_message ?? undefined,
      failed: data.failed_files,
      duplicated: data.duplicated_files,
    })),

  cancelImport: (importId: string) => {
    return fetchJson<{ cancelled: boolean }>(`${API_BASE}/import/cancel/${importId}`, { method: 'POST' });
  },

  pauseImport: (importId: string) => {
    return fetchJson<{ paused: boolean }>(`${API_BASE}/import/pause/${importId}`, { method: 'POST' });
  },

  resumeImport: (importId: string) => {
    return fetchJson<{ resumed: boolean }>(`${API_BASE}/import/resume/${importId}`, { method: 'POST' });
  },

  // Delete
  deletePhotos: (paths: string[], sourcePaths?: string[]) =>
    fetchJson<{ deleted: number }>(`${API_BASE}/files/delete`, {
      method: 'POST',
      body: JSON.stringify({ paths, source_paths: sourcePaths || [] }),
    }),

  // Settings - 并行获取所有设置
  getSettings: async () => {
    const [albumRes, themeRes, langRes] = await Promise.all([
      fetchJson<{ album_path: string }>(`${API_BASE}/settings/album-path`).catch(() => ({ album_path: '' })),
      fetchJson<{ theme: string }>(`${API_BASE}/settings/theme`).catch(() => ({ theme: 'system' })),
      fetchJson<{ language: string }>(`${API_BASE}/settings/language`).catch(() => ({ language: 'zh' })),
    ]);
    return {
      album_path: albumRes.album_path,
      theme: themeRes.theme,
      language: langRes.language,
    };
  },

  updateSettings: (settings: Partial<{ theme: string; language: string }>) => {
    const promises: Promise<void>[] = [];
    if (settings.theme) {
      promises.push(
        fetchJson<{ success: boolean }>(`${API_BASE}/settings/theme`, {
          method: 'PUT',
          body: JSON.stringify({ theme: settings.theme }),
        }).then(() => {})
      );
    }
    if (settings.language) {
      promises.push(
        fetchJson<{ success: boolean }>(`${API_BASE}/settings/language`, {
          method: 'PUT',
          body: JSON.stringify({ language: settings.language }),
        }).then(() => {})
      );
    }
    return Promise.all(promises).then(() => ({ success: true }));
  },

  // Change album path - 使用 PyWebView API 选择文件夹
  changeAlbumPath: async (): Promise<{ album_path: string; task_id: string }> => {
    // 检查 PyWebView API 是否可用
    if (window.pywebview?.api?.select_folder) {
      const newPath = await window.pywebview.api.select_folder();
      if (newPath) {
        // 调用后端设置路径
        const res = await fetchJson<{ album_path: string; task_id: string }>(`${API_BASE}/settings/album-path`, {
          method: 'PUT',
          body: JSON.stringify({ album_path: newPath }),
        });
        return { album_path: newPath, task_id: res.task_id };
      }
      throw new Error('未选择文件夹');
    }
    throw new Error('PyWebView API 不可用');
  },

  // Select source folder for import
  selectFolder: async (): Promise<string | null> => {
    if (window.pywebview?.api?.select_folder) {
      return await window.pywebview.api.select_folder();
    }
    return null;
  },

  // Cache
  clearCache: () => fetchJson<{ deleted_count: number; freed_mb: number }>(`${API_BASE}/cache/cleanup`, {
    method: 'POST',
    body: JSON.stringify({ max_size_mb: 0 }),
  }),

  // Rebuild index (database + thumbnails)
  rebuildIndex: () => fetchJson<{ status: string; task_id: string; cache_cleared: number }>(`${API_BASE}/settings/rebuild-index`, {
    method: 'POST',
  }),

  getRebuildProgress: (taskId: string) => fetchJson<{ status: string; progress: number; message: string }>(`${API_BASE}/settings/rebuild-progress/${taskId}`),

  // Phone upload
  startPhoneUpload: () =>
    fetchJson<{
      port: number;
      local_ip: string;
      upload_url: string;
      session_id: string;
      upload_dir: string;
    }>(`${API_BASE}/phone-upload/start`, { method: 'POST' }),

  stopPhoneUpload: () =>
    fetchJson<{ status: string }>(`${API_BASE}/phone-upload/stop`, { method: 'POST' }),

  getPhoneUploadStatus: () =>
    fetchJson<{
      total_files: number;
      completed_files: number;
      total_bytes_uploaded: number;
      files: { name: string; size: number; status: string; error?: string }[];
    }>(`${API_BASE}/phone-upload/status`),

  getPhoneUploadQr: () => `${API_BASE}/phone-upload/qr`,

  getIncompletePhoneSession: () =>
    fetchJson<{ session: { id: string; upload_dir: string; file_count: number; total_bytes: number; created_at: number } | null }>(`${API_BASE}/phone-upload/incomplete`),

  resumePhoneSession: (sessionId: string) =>
    fetchJson<{
      port: number;
      local_ip: string;
      upload_url: string;
      session_id: string;
      upload_dir: string;
    }>(`${API_BASE}/phone-upload/resume`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  discardPhoneSession: (sessionId: string) =>
    fetchJson<{ status: string }>(`${API_BASE}/phone-upload/discard`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  // File operations
  openFile: (path: string) => {
    window.open(`${API_BASE}/album/file?path=${encodeURIComponent(path)}`, '_blank');
    return Promise.resolve({ success: true });
  },

  // Mobile access service
  getMobileStatus: () =>
    fetchJson<{ enabled: boolean; running: boolean; port: number | null; local_ip: string | null; paired_count: number }>(`${API_BASE}/mobile/status`),

  enableMobileService: () =>
    fetchJson<{ status: string; port: number; local_ip: string }>(`${API_BASE}/mobile/enable`, { method: 'POST' }),

  disableMobileService: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/disable`, { method: 'POST' }),

  getMobileQr: () => `${API_BASE}/mobile/qr`,

  getMobilePendingRequest: () =>
    fetchJson<{ hasPending: boolean; pairing_code?: string; device_name?: string }>(`${API_BASE}/mobile/pending-request`),

  confirmMobilePairing: (pairingCode: string, action: 'accept' | 'reject') =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/confirm-pairing`, { method: 'POST', body: JSON.stringify({ pairing_code: pairingCode, action }) }),

  getMobileDevices: () =>
    fetchJson<{ devices: { device_name: string; paired_at: string; token: string }[] }>(`${API_BASE}/mobile/devices`),

  revokeMobileDevice: (token: string) =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/revoke`, { method: 'POST', body: JSON.stringify({ token }) }),

  revokeAllMobileDevices: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/revoke-all`, { method: 'POST' }),

  // 配对模式管理（新流程：mDNS 发现）
  startPairingMode: () =>
    fetchJson<{ status: string; hostname: string }>(`${API_BASE}/mobile/pairing/start`, { method: 'POST' }),

  stopPairingMode: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/pairing/stop`, { method: 'POST' }),

  getPairingPending: () =>
    fetchJson<{ status: string; device_name?: string; requested_at?: number }>(`${API_BASE}/mobile/pairing/pending`),

  confirmPairing: () =>
    fetchJson<{ status: string; pairing_code: string; expires_in: number }>(`${API_BASE}/mobile/pairing/confirm`, { method: 'POST' }),

  rejectPairing: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/pairing/reject`, { method: 'POST' }),

  cancelPairing: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/pairing/cancel`, { method: 'POST' }),

  // Flutter 上传通知
  getPendingFlutterUploads: () =>
    fetchJson<{ sessions: { device_name: string; upload_dir: string; file_count: number; updated_at: string }[] }>(`${API_BASE}/mobile/pending-flutter-uploads`),

  clearPendingFlutterUpload: (uploadDir: string) =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/pending-flutter-uploads/clear`, {
      method: 'POST',
      body: JSON.stringify({ upload_dir: uploadDir }),
    }),
};
