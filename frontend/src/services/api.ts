const API_BASE = '/api';

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

  // Directory tree - 转换后端返回的扁平结构为按年份分组
  getTree: async () => {
    const response = await fetchJson<{ children: { name: string; path: string; count: number; type: string }[] }>(`${API_BASE}/album/tree`);
    // 将扁平的 YYYY-MM 目录转换为按年份分组
    const yearMap = new Map<string, { name: string; path: string; count: number }[]>();
    for (const item of response.children || []) {
      // 从 "2014-05" 或 "D:\...\2014-05" 提取年月
      const match = item.name.match(/^(\d{4})-(\d{2})$/);
      if (match) {
        const year = match[1];
        const monthNum = parseInt(match[2]);
        const monthName = `${monthNum}月`;
        if (!yearMap.has(year)) {
          yearMap.set(year, []);
        }
        yearMap.get(year)!.push({
          name: monthName,
          path: item.path,
          count: item.count,
        });
      }
    }
    // 转换为数组并按年份降序排列
    const tree = Array.from(yearMap.entries())
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([year, months]) => ({
        year,
        // 按月份数字排序（1月 < 2月 < ... < 12月）
        months: months.sort((a, b) => {
          const numA = parseInt(a.name);
          const numB = parseInt(b.name);
          return numA - numB;
        }),
      }));
    return { tree };
  },

  // Photos
  getPhotos: (path: string) => fetchJson<{ photos: { id: string; name: string; path: string; size: number; date: string; type: string; duration?: string }[] }>(`${API_BASE}/album/photos?path=${encodeURIComponent(path)}`),

  // Thumbnail
  getThumbnail: (path: string) => `${API_BASE}/album/thumbnail?path=${encodeURIComponent(path)}`,

  // File (for preview)
  getFile: (path: string) => `${API_BASE}/album/file?path=${encodeURIComponent(path)}`,

  // Import
  checkImport: (sourcePath: string) => fetchJson<{ valid: boolean; count: number }>(`${API_BASE}/import/check`, {
    method: 'POST',
    body: JSON.stringify({ source_path: sourcePath }),
  }),

  startImport: (sourcePath: string, mode: 'copy' | 'move', options?: { skip_source_duplicates?: boolean; skip_target_duplicates?: boolean }) =>
    fetchJson<{ import_id: string }>(`${API_BASE}/import/start`, {
      method: 'POST',
      body: JSON.stringify({
        source_path: sourcePath,
        mode: mode,
        ...options,
      }),
    }).then((res) => {
      currentImportId = res.import_id;
      return res;
    }),

  getImportProgress: () => {
    if (!currentImportId) {
      return Promise.resolve({ step: 0, total: 0, current: '', status: 'idle' });
    }
    return fetchJson<{ step: number; total: number; current: string; status: string }>(`${API_BASE}/import/progress/${currentImportId}`);
  },

  cancelImport: () => {
    if (!currentImportId) {
      return Promise.resolve({ cancelled: true });
    }
    return fetchJson<{ cancelled: boolean }>(`${API_BASE}/import/cancel/${currentImportId}`, { method: 'POST' })
      .then((res) => {
        currentImportId = null;
        return res;
      });
  },

  // Delete
  deletePhotos: (paths: string[]) =>
    fetchJson<{ deleted: number }>(`${API_BASE}/files/delete`, {
      method: 'POST',
      body: JSON.stringify({ files: paths }),
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
  changeAlbumPath: async (): Promise<{ album_path: string }> => {
    // 检查 PyWebView API 是否可用
    if (window.pywebview?.api?.select_folder) {
      const newPath = await window.pywebview.api.select_folder();
      if (newPath) {
        // 调用后端设置路径
        await fetchJson<{ album_path: string; task_id: string }>(`${API_BASE}/settings/album-path`, {
          method: 'PUT',
          body: JSON.stringify({ album_path: newPath }),
        });
        return { album_path: newPath };
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

  // File operations
  openFile: (path: string) => {
    window.open(`${API_BASE}/album/file?path=${encodeURIComponent(path)}`, '_blank');
    return Promise.resolve({ success: true });
  },
};
