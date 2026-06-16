import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { MainContent } from './components/layout/MainContent';
import { ImportDialog } from './components/dialogs/ImportDialog';
import { SettingsDialog } from './components/dialogs/SettingsDialog';
import { PhotoPreview } from './components/dialogs/PhotoPreview';
import { DeleteConfirmDialog } from './components/dialogs/DeleteConfirmDialog';
import { ToastProvider, useToast } from './components/common/Toast';
import { api } from './services/api';
import type { Photo, YearNode } from './types';

interface AppState {
  initialized: boolean;
  stats: { total: number; videos: number; size: string } | null;
  years: YearNode[];
  selectedPath: string | null;
  selectedTitle: string;
  photos: Photo[];
  loading: boolean;
  selectionMode: boolean;
  selectedIds: Set<string>;
}

function AppContent() {
  const { showToast } = useToast();
  const [state, setState] = useState<AppState>({
    initialized: false,
    stats: null,
    years: [],
    selectedPath: null,
    selectedTitle: '',
    photos: [],
    loading: true,
    selectionMode: false,
    selectedIds: new Set(),
  });

  // Dialog states
  const [importOpen, setImportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewPhoto, setPreviewPhoto] = useState<Photo | null>(null);
  const [deletePaths, setDeletePaths] = useState<string[]>([]);

  // Initialize app
  useEffect(() => {
    const init = async () => {
      try {
        await api.health();
        const [statsRes, treeRes] = await Promise.all([
          api.getStats().catch(() => null),
          api.getTree().catch(() => ({ tree: [] })),
        ]);

        setState((prev) => ({
          ...prev,
          initialized: true,
          stats: statsRes ? { total: statsRes.total_files, videos: statsRes.video_count, size: `${(statsRes.total_size_mb / 1024).toFixed(1)} GB` } : null,
          years: treeRes.tree || [],
          loading: false,
        }));
      } catch (error) {
        console.error('Failed to initialize:', error);
        showToast('连接服务器失败，请重启应用', 'error');
        setState((prev) => ({ ...prev, loading: false }));
      }
    };

    init();
  }, [showToast]);

  // Load photos when path changes
  const loadPhotos = useCallback(async (path: string, title: string) => {
    setState((prev) => ({ ...prev, selectedPath: path, selectedTitle: title, loading: true }));
    try {
      const res = await api.getPhotos(path);
      setState((prev) => ({
        ...prev,
        photos: res.photos.map((p) => ({
          id: p.path, // 使用 path 作为唯一标识
          name: p.name,
          path: p.path,
          size: p.size,
          date: p.date,
          type: p.type as 'photo' | 'video',
          duration: p.duration,
        })),
        loading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : '加载照片失败';
      showToast(message, 'error');
      setState((prev) => ({ ...prev, photos: [], loading: false }));
    }
  }, [showToast]);

  const handleSelectPath = useCallback((path: string) => {
    const parts = path.split('/');
    const title = parts.length >= 2 ? `${parts[0]}年${parseInt(parts[1])}月` : path;
    loadPhotos(path, title);
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
    showToast('删除成功', 'success');
    if (state.selectedPath) {
      loadPhotos(state.selectedPath, state.selectedTitle);
    }
  }, [state.selectedPath, state.selectedTitle, loadPhotos, showToast]);

  const refreshStats = useCallback(async () => {
    try {
      const res = await api.getStats();
      setState((prev) => ({
        ...prev,
        stats: { total: res.total_files, videos: res.video_count, size: `${(res.total_size_mb / 1024).toFixed(1)} GB` },
      }));
    } catch (error) {
      console.error('Failed to refresh stats:', error);
    }
  }, []);

  if (!state.initialized && state.loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-page">
        <div className="animate-spin w-10 h-10 border-4 border-border border-t-primary rounded-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full h-full">
      <Header onSettings={handleSettings} />
      <main className="flex flex-1 min-h-0 overflow-hidden">
        <Sidebar
          stats={state.stats}
          years={state.years}
          selectedPath={state.selectedPath}
          onSelectPath={handleSelectPath}
          onImport={handleImport}
        />
        <MainContent
          title={state.selectedTitle || '选择目录开始浏览'}
          count={state.photos.length}
          photos={state.photos}
          loading={state.loading}
          selectionMode={state.selectionMode}
          selectedIds={state.selectedIds}
          onPhotoClick={handlePhotoClick}
          onSelect={handleSelect}
          onSelectAll={handleSelectAll}
          onDelete={handleDelete}
        />
      </main>

      {/* Dialogs */}
      <ImportDialog
        isOpen={importOpen}
        onClose={() => setImportOpen(false)}
        onComplete={() => {
          refreshStats();
          if (state.selectedPath) loadPhotos(state.selectedPath, state.selectedTitle);
        }}
      />
      <SettingsDialog isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
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
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}

export default App;
