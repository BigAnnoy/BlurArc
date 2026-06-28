import type { ImportPhoto, ImportProgress } from '../components/dialogs/ImportDialog/types';
import type { DirNode } from '../types';

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

  // System locale - 用于首次启动自动选择语言
  getSystemLocale: () =>
    fetchJson<{ locale: string; language: 'zh' | 'en' }>(`${API_BASE}/system/locale`).catch(() => ({
      locale: '',
      language: 'zh' as const,
    })),

  // Stats
  getStats: () => fetchJson<{ total_files: number; video_count: number; total_size_mb: number; last_import: string }>(`${API_BASE}/album/stats`),

  // Directory tree - 不再做"年份"特殊处理，统一按实际目录结构递归展示
  getTree: async () => {
    const response = await fetchJson<DirNode & { type: string }>(`${API_BASE}/album/tree`);

    // 构造根目录节点（不再过滤 YYYY-MM 格式目录，按真实目录名展示）
    const sortChildren = (children: DirNode[]): DirNode[] => {
      return children
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

    // v0.7.1: 不再做"按年份浏览"特殊分组，years 保留为兼容旧版 API 的空数组
    return { tree: [], rootDir };
  },

  // Photos - 支持分页
  getPhotos: (path: string, page: number = 1, pageSize: number = 100, sort?: string) => fetchJson<{
    photos: { id: string; name: string; path: string; size: number; date: string; type: string; duration?: string; is_favorite?: boolean }[];
    count: number;
    total_pages: number;
    page: number;
    page_size: number;
  }>(`${API_BASE}/album/photos?path=${encodeURIComponent(path)}&page=${page}&page_size=${pageSize}${sort ? `&sort=${sort}` : ''}`),

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
      throw new Error('welcome.folderNotSelected');
    }
    throw new Error('app.pywebviewNotAvailable');
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

  // ============================================================================
  // 相册管理 API (v0.7)
  // ============================================================================

  getAlbums: () =>
    fetchJson<{ albums: { id: number; name: string; description: string; cover_photo_id: number | null; photo_count: number; created_at: string }[] }>(`${API_BASE}/albums`),

  createAlbum: (name: string, description?: string, coverPhotoId?: number) =>
    fetchJson<{ id: number; name: string; description: string; cover_photo_id: number | null; photo_count: number; created_at: string }>(`${API_BASE}/albums`, {
      method: 'POST',
      body: JSON.stringify({ name, description, cover_photo_id: coverPhotoId }),
    }),

  getAlbum: (albumId: number) =>
    fetchJson<{ id: number; name: string; description: string; cover_photo_id: number | null; photo_count: number; created_at: string }>(`${API_BASE}/albums/${albumId}`),

  updateAlbum: (albumId: number, data: { name?: string; description?: string; cover_photo_id?: number | null }) =>
    fetchJson<{ id: number; name: string; description: string; cover_photo_id: number | null; photo_count: number; created_at: string }>(`${API_BASE}/albums/${albumId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteAlbum: (albumId: number) =>
    fetchJson<{ status: string; id: number }>(`${API_BASE}/albums/${albumId}`, { method: 'DELETE' }),

  getAlbumPhotos: (albumId: number, page?: number, pageSize?: number, sort?: string) =>
    fetchJson<{ photos: { id: number; filename: string; path: string; size: number; date: string | null; type: string; is_favorite: boolean }[]; total: number; page: number; total_pages: number; page_size: number }>(
      `${API_BASE}/albums/${albumId}/photos${page && pageSize ? `?page=${page}&page_size=${pageSize}${sort ? `&sort=${sort}` : ''}` : (sort ? `?sort=${sort}` : '')}`
    ),

  getPhotoAlbums: (photoId: number) =>
    fetchJson<{ albums: { id: number; name: string; description: string | null; cover_photo_id: number | null; photo_count: number; created_at: string | null }[]; total: number }>(
      `${API_BASE}/photos/${photoId}/albums`
    ),

  addPhotoToAlbum: (albumId: number, photoId: number) =>
    fetchJson<{ status: string; album_id: number; photo_id: number }>(`${API_BASE}/albums/${albumId}/photos`, {
      method: 'POST',
      body: JSON.stringify({ photo_id: photoId }),
    }),

  removePhotoFromAlbum: (albumId: number, photoId: number) =>
    fetchJson<{ status: string; album_id: number; photo_id: number }>(`${API_BASE}/albums/${albumId}/photos`, {
      method: 'DELETE',
      body: JSON.stringify({ photo_id: photoId }),
    }),

  batchAddPhotosToAlbum: (albumId: number, photoIds: number[]) =>
    fetchJson<{ status: string; album_id: number; added: number; skipped: number }>(`${API_BASE}/albums/${albumId}/photos/batch`, {
      method: 'POST',
      body: JSON.stringify({ photo_ids: photoIds }),
    }),

  duplicateAlbum: (albumId: number) =>
    fetchJson<{ album: { id: number; name: string; photo_count: number; created_at: string } }>(`${API_BASE}/albums/${albumId}/duplicate`, {
      method: 'POST',
    }),

  mergeAlbums: (targetId: number, sourceId: number) =>
    fetchJson<{ target_album_id: number; source_album_id: number; added_count: number; skipped_count: number }>(
      `${API_BASE}/albums/${targetId}/merge`,
      { method: 'POST', body: JSON.stringify({ source_id: sourceId }) }
    ),

  batchRemovePhotosFromAlbum: (albumId: number, photoIds: number[]) =>
    fetchJson<{ status: string; album_id: number; removed: number; skipped: number }>(
      `${API_BASE}/albums/${albumId}/photos/batch-remove`,
      { method: 'POST', body: JSON.stringify({ photo_ids: photoIds }) }
    ),

  getPhotoIds: (params?: {
    favorite?: boolean;
    type?: string;
    path?: string;
    not_in_album?: boolean;
    album_id?: number;
    from?: string;
    to?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.favorite !== undefined) searchParams.set('favorite', String(params.favorite));
    if (params?.type) searchParams.set('type', params.type);
    if (params?.path) searchParams.set('path', params.path);
    if (params?.not_in_album !== undefined) searchParams.set('not_in_album', String(params.not_in_album));
    if (params?.album_id) searchParams.set('album_id', String(params.album_id));
    if (params?.from) searchParams.set('from', params.from);
    if (params?.to) searchParams.set('to', params.to);
    const query = searchParams.toString();
    return fetchJson<{ ids: number[]; total: number }>(
      `${API_BASE}/photos/ids${query ? `?${query}` : ''}`
    );
  },

  // ============================================================================
  // 收藏功能 API (v0.7)
  // ============================================================================

  addFavorite: (photoId: number) =>
    fetchJson<{ success: boolean; favorited_at: string }>(`${API_BASE}/photos/${photoId}/favorite`, { method: 'POST' }),

  removeFavorite: (photoId: number) =>
    fetchJson<{ success: boolean }>(`${API_BASE}/photos/${photoId}/favorite`, { method: 'DELETE' }),

  batchFavorite: (photoIds: number[], favorite: boolean) =>
    fetchJson<{ success: boolean; updated: number }>(`${API_BASE}/photos/batch-favorite`, {
      method: 'POST',
      body: JSON.stringify({ photo_ids: photoIds, favorite }),
    }),

  getFavorites: (sort?: string) =>
    fetchJson<{ photos: { id: number; filename: string; path: string; size: number; date: string | null; type: string; is_favorite: boolean; favorited_at: string | null }[]; total: number }>(`${API_BASE}/photos/favorites${sort ? `?sort=${sort}` : ''}`),

  // ============================================================================
  // 文件夹操作 API (v0.7)
  // ============================================================================

  openInExplorer: (path: string) =>
    fetchJson<{ status: string; path: string }>(`${API_BASE}/folders/open-in-explorer`, {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),

  scanDirectory: (path: string) =>
    fetchJson<{ status: string; path: string; new_files: number; added_to_db: number }>(
      `${API_BASE}/folders/scan-new`,
      {
        method: 'POST',
        body: JSON.stringify({ path }),
      }
    ),

  // ============================================================================
  // 时间线 API (v0.7)
  // ============================================================================

  // v0.7 概览图分批加载：limit/cursor 可选，不传时返回全部（兼容旧 API）
  // 后端响应字段为 snake_case（next_cursor / has_next），前端类型保持一致
  getTimelineYears: (limit?: number, cursor?: number) => {
    const params = new URLSearchParams();
    if (limit !== undefined) params.set('limit', String(limit));
    if (cursor !== undefined) params.set('cursor', String(cursor));
    const query = params.toString();
    return fetchJson<{
      years: { year: number; count: number; cover_photo_id: number | null; cover_photo_path: string | null; cover_photo_paths?: string[] }[];
      next_cursor: number | null;
      has_next: boolean;
    }>(`${API_BASE}/timeline/years${query ? `?${query}` : ''}`);
  },

  getTimelineMonths: (year?: number, limit?: number, cursor?: string) => {
    const params = new URLSearchParams();
    if (year !== undefined) params.set('year', String(year));
    if (limit !== undefined) params.set('limit', String(limit));
    if (cursor !== undefined) params.set('cursor', cursor);
    const query = params.toString();
    return fetchJson<{
      months: { year: number; month: number; count: number; cover_photo_id: number | null; cover_photo_path: string | null; cover_photo_paths?: string[] }[];
      next_cursor: string | null;
      has_next: boolean;
    }>(`${API_BASE}/timeline/months${query ? `?${query}` : ''}`);
  },

  getTimelinePhotos: (params?: { year?: number; month?: number; day?: string; page?: number; page_size?: number; sort?: string; filters?: string[] }) => {
    const searchParams = new URLSearchParams();
    if (params?.year) searchParams.set('year', String(params.year));
    if (params?.month) searchParams.set('month', String(params.month));
    if (params?.day) searchParams.set('day', params.day);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.sort) searchParams.set('sort', params.sort);
    if (params?.filters && params.filters.length > 0) searchParams.set('filters', params.filters.join(','));
    const query = searchParams.toString();
    return fetchJson<{
      photos: { id: number; filename: string; path: string; size: number; date: string | null; type: string; is_favorite: boolean }[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`${API_BASE}/timeline/photos${query ? `?${query}` : ''}`);
  },

  // ============================================================================
  // XMP 同步 API (v0.7)
  // ============================================================================

  updatePhotoTitle: (photoId: number, title: string) =>
    fetchJson<{ status: string; xmp_sync: boolean; message: string }>(`${API_BASE}/photos/${photoId}/title`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    }),

  updatePhotoDescription: (photoId: number, description: string) =>
    fetchJson<{ status: string; xmp_sync: boolean; message: string }>(`${API_BASE}/photos/${photoId}/description`, {
      method: 'PUT',
      body: JSON.stringify({ description }),
    }),
};
