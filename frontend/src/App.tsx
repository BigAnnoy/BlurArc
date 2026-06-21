import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { MainContent } from './components/layout/MainContent';
import { ImportDialog } from './components/dialogs/ImportDialog';
import { SettingsDialog } from './components/dialogs/SettingsDialog';
import { PhotoPreview } from './components/dialogs/PhotoPreview';
import { DeleteConfirmDialog } from './components/dialogs/DeleteConfirmDialog';
import { ToastProvider, useToast } from './components/common/Toast';
import { I18nProvider, useI18n } from './contexts/I18nContext';
import { WelcomeScreen } from './components/WelcomeScreen';
import { api } from './services/api';
import { formatSize } from './utils/format';
import type { Photo, YearNode, DirNode } from './types';

interface AppState {
  initialized: boolean;
  isFirstRun: boolean;
  stats: { total: number; videos: number; size: string } | null;
  years: YearNode[];
  rootDir: DirNode | null;
  selectedPath: string | null;
  selectedTitle: string;
  photos: Photo[];
  loading: boolean;
  selectionMode: boolean;
  selectedIds: Set<string>;
  // 分页状态
  totalPhotos: number;
  currentPage: number;
  hasMore: boolean;
}

function AppContent() {
  const { showToast } = useToast();
  const { t } = useI18n();
  const [state, setState] = useState<AppState>({
    initialized: false,
    isFirstRun: false,
    stats: null,
    years: [],
    rootDir: null,
    selectedPath: null,
    selectedTitle: '',
    photos: [],
    loading: true,
    selectionMode: false,
    selectedIds: new Set(),
    totalPhotos: 0,
    currentPage: 1,
    hasMore: false,
  });

  // Dialog states
  const [importOpen, setImportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewPhoto, setPreviewPhoto] = useState<Photo | null>(null);
  const [deletePaths, setDeletePaths] = useState<string[]>([]);
  // Flutter App 上传自动导入
  const [pendingFlutterSession, setPendingFlutterSession] = useState<{
    upload_dir: string;
    device_name: string;
    file_count: number;
  } | null>(null);

  // Initialize app
  useEffect(() => {
    const init = async () => {
      try {
        await api.health();
        
        // Check if this is first run
        const settings = await api.getSettings();
        if (!settings.album_path) {
          setState((prev) => ({ ...prev, isFirstRun: true, loading: false }));
          return;
        }
        
        const [statsRes, treeRes] = await Promise.all([
          api.getStats().catch(() => null),
          api.getTree().catch(() => ({ tree: [], rootDir: null })),
        ]);

        setState((prev) => ({
          ...prev,
          initialized: true,
          stats: statsRes ? { total: statsRes.total_files, videos: statsRes.video_count, size: formatSize(statsRes.total_size_mb) } : null,
          years: treeRes.tree || [],
          rootDir: treeRes.rootDir || null,
          loading: false,
        }));
      } catch (error) {
        console.error('Failed to initialize:', error);
        showToast(t('app.connectionFailed'), 'error');
        setState((prev) => ({ ...prev, loading: false }));
      }
    };

    init();
  }, [showToast]);

  // 轮询 Flutter App 上传完成通知
  useEffect(() => {
    let polling = true;
    const poll = async () => {
      try {
        const res = await api.getPendingFlutterUploads();
        if (res.sessions.length > 0 && polling) {
          const s = res.sessions[0];
          // 立即清除后端通知，防止重复触发
          api.clearPendingFlutterUpload(s.upload_dir).catch(() => {});
          setPendingFlutterSession({
            upload_dir: s.upload_dir,
            device_name: s.device_name,
            file_count: s.file_count,
          });
          setImportOpen(true);
        }
      } catch {
        // 静默
      }
    };
    poll();
    const interval = setInterval(poll, 3000);
    return () => { polling = false; clearInterval(interval); };
  }, []);

  // Load photos when path changes
  const loadPhotos = useCallback(async (path: string, title: string, page: number = 1, append: boolean = false) => {
    if (page === 1) {
      setState((prev) => ({ ...prev, selectedPath: path, selectedTitle: title, loading: true }));
    }
    try {
      const res = await api.getPhotos(path, page, 100);
      const newPhotos = res.photos.map((p) => ({
        id: p.path,
        name: p.name,
        path: p.path,
        size: p.size,
        date: p.date,
        type: p.type as 'photo' | 'video',
        duration: p.duration,
      }));
      
      setState((prev) => ({
        ...prev,
        photos: append ? [...prev.photos, ...newPhotos] : newPhotos,
        totalPhotos: res.count,
        currentPage: res.page,
        hasMore: res.page < res.total_pages,
        loading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : t('app.loadPhotosFailed');
      showToast(message, 'error');
      setState((prev) => ({ ...prev, photos: [], loading: false }));
    }
  }, [showToast]);

  const handleSelectPath = useCallback((path: string) => {
    // 从路径提取目录名
    const parts = path.split(/[\\/]/);
    const dirName = parts[parts.length - 1] || path;
    
    // 检查是否是 YYYY-MM 格式
    const match = dirName.match(/^(\d{4})-(\d{2})$/);
    if (match) {
      const year = match[1];
      const month = parseInt(match[2]);
      const title = `${year}年${month}月`;
      loadPhotos(path, title, 1);
    } else {
      loadPhotos(path, dirName, 1);
    }
  }, [loadPhotos]);

  const handlePhotoClick = useCallback((photo: Photo) => {
    if (state.selectionMode) {
      setState((prev) => {
        const next = new Set(prev.selectedIds);
        if (next.has(photo.id)) {
          next.delete(photo.id);
        } else {
          next.add(photo.id);
        }
        return { ...prev, selectedIds: next };
      });
    } else {
      setPreviewPhoto(photo);
    }
  }, [state.selectionMode]);

  const handleImport = useCallback(() => setImportOpen(true), []);
  const handleSettings = useCallback(() => setSettingsOpen(true), []);

  const handleSelect = useCallback(() => {
    setState((prev) => ({
      ...prev,
      selectionMode: !prev.selectionMode,
      selectedIds: new Set(),
    }));
  }, []);

  const handleSelectAll = useCallback(() => {
    setState((prev) => {
      const allSelected = prev.selectedIds.size === prev.photos.length;
      return {
        ...prev,
        selectedIds: allSelected ? new Set() : new Set(prev.photos.map((p) => p.id)),
      };
    });
  }, []);

  const handleDelete = useCallback(() => {
    const paths = state.photos
      .filter((p) => state.selectedIds.has(p.id))
      .map((p) => p.path);
    if (paths.length > 0) {
      setDeletePaths(paths);
    }
  }, [state.photos, state.selectedIds]);

  const handleDeleteComplete = useCallback(() => {
    setState((prev) => ({ ...prev, selectionMode: false, selectedIds: new Set() }));
    showToast(t('delete.success'), 'success');
    if (state.selectedPath) {
      loadPhotos(state.selectedPath, state.selectedTitle, 1);
    }
  }, [state.selectedPath, state.selectedTitle, loadPhotos, showToast, t]);

  // Reload app data after first run setup
  const handleWelcomeComplete = useCallback(async () => {
    try {
      const settings = await api.getSettings();
      if (settings.album_path) {
        const [statsRes, treeRes] = await Promise.all([
          api.getStats().catch(() => null),
          api.getTree().catch(() => ({ tree: [], rootDir: null })),
        ]);
        setState((prev) => ({
          ...prev,
          isFirstRun: false,
          initialized: true,
          stats: statsRes ? { total: statsRes.total_files, videos: statsRes.video_count, size: formatSize(statsRes.total_size_mb) } : null,
          years: treeRes.tree || [],
          rootDir: treeRes.rootDir || null,
        }));
      }
    } catch (error) {
      console.error('Failed to reload after welcome:', error);
    }
  }, []);

  // Refresh all app data (stats, tree, and current photos)
  const refreshAppData = useCallback(async () => {
    try {
      const [statsRes, treeRes] = await Promise.all([
        api.getStats().catch(() => null),
        api.getTree().catch(() => ({ tree: [], rootDir: null })),
      ]);
      setState((prev) => ({
        ...prev,
        stats: statsRes ? { total: statsRes.total_files, videos: statsRes.video_count, size: formatSize(statsRes.total_size_mb) } : null,
        years: treeRes.tree || [],
        rootDir: treeRes.rootDir || null,
      }));
      // Reload current photos if a path is selected
      if (state.selectedPath) {
        loadPhotos(state.selectedPath, state.selectedTitle, 1);
      }
    } catch (error) {
      console.error('Failed to refresh app data:', error);
    }
  }, [state.selectedPath, state.selectedTitle, loadPhotos]);

  if (!state.initialized && state.loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-page">
        <div className="animate-spin w-10 h-10 border-4 border-border border-t-primary rounded-full" />
      </div>
    );
  }

  // Show welcome screen on first run
  if (state.isFirstRun) {
    return <WelcomeScreen onComplete={handleWelcomeComplete} />;
  }

  return (
    <div className="flex flex-col w-full h-full">
      <Header onSettings={handleSettings} />
      <main className="flex flex-1 min-h-0 overflow-hidden">
        <Sidebar
          stats={state.stats}
          years={state.years}
          rootDir={state.rootDir}
          selectedPath={state.selectedPath}
          onSelectPath={handleSelectPath}
          onImport={handleImport}
        />
        <MainContent
          title={state.selectedTitle || t('main.selectToBrowse')}
          count={state.totalPhotos}
          photos={state.photos}
          loading={state.loading}
          selectionMode={state.selectionMode}
          selectedIds={state.selectedIds}
          onPhotoClick={handlePhotoClick}
          onSelect={handleSelect}
          onSelectAll={handleSelectAll}
          onDelete={handleDelete}
          hasMore={state.hasMore}
          onLoadMore={() => {
            if (state.selectedPath && state.hasMore) {
              loadPhotos(state.selectedPath, state.selectedTitle, state.currentPage + 1, true);
            }
          }}
        />
      </main>

      {/* Dialogs */}
      <ImportDialog
        isOpen={importOpen}
        onClose={() => {
          setImportOpen(false);
          setPendingFlutterSession(null);
        }}
        onComplete={() => {
          setPendingFlutterSession(null);
          refreshAppData();
        }}
        phoneSourcePath={pendingFlutterSession?.upload_dir}
      />
      <SettingsDialog isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} onDataRefresh={refreshAppData} />
      <PhotoPreview
        isOpen={!!previewPhoto}
        onClose={() => setPreviewPhoto(null)}
        photo={previewPhoto}
        photos={state.photos}
        onNavigate={setPreviewPhoto}
      />
      <DeleteConfirmDialog
        isOpen={deletePaths.length > 0}
        onClose={() => setDeletePaths([])}
        paths={deletePaths}
        onDelete={handleDeleteComplete}
      />
    </div>
  );
}

export function App() {
  return (
    <I18nProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </I18nProvider>
  );
}

export default App;
