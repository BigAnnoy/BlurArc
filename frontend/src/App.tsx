import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { MainContent } from './components/layout/MainContent';
import { TimelineView } from './components/timeline/TimelineView';
import { ImportDialog } from './components/dialogs/ImportDialog';
import { SettingsDialog } from './components/dialogs/SettingsDialog';
import { PhotoPreview } from './components/dialogs/PhotoPreview';
import { DeleteConfirmDialog } from './components/dialogs/DeleteConfirmDialog';
import { AlbumManageModal } from './components/dialogs/AlbumManageModal';
import { JoinAlbumModal } from './components/dialogs/JoinAlbumModal';
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
  // v0.7 新增
  currentView: 'timeline' | 'favorites' | 'albums' | 'album-detail' | 'folder';
  selectedAlbumId: number | null;
  favoriteCount: number;
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
    // v0.7 新增
    currentView: 'timeline',
    selectedAlbumId: null,
    favoriteCount: 0,
  });

  // Dialog states
  const [importOpen, setImportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewPhoto, setPreviewPhoto] = useState<Photo | null>(null);
  const [deletePaths, setDeletePaths] = useState<string[]>([]);
  // v0.7: Album management modal
  const [albumModal, setAlbumModal] = useState<{
    open: boolean;
    mode: 'create' | 'rename' | 'delete' | 'duplicate';
    album?: { id: number; name: string };
  }>({ open: false, mode: 'create' });
  // v0.7: Join album modal
  const [joinAlbumOpen, setJoinAlbumOpen] = useState(false);
  const [joinAlbumPhotoIds, setJoinAlbumPhotoIds] = useState<string[]>([]);
  // v0.7: Albums list for albums view
  const [albumsList, setAlbumsList] = useState<{ id: number; name: string; photo_count: number; cover_photo_id: number | null }[]>([]);
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
        
        const [statsRes, treeRes, favoritesRes] = await Promise.all([
          api.getStats().catch(() => null),
          api.getTree().catch(() => ({ tree: [], rootDir: null })),
          api.getFavorites().catch(() => ({ photos: [], total: 0 })),
        ]);

        setState((prev) => ({
          ...prev,
          initialized: true,
          stats: statsRes ? { total: statsRes.total_files, videos: statsRes.video_count, size: formatSize(statsRes.total_size_mb) } : null,
          years: treeRes.tree || [],
          rootDir: treeRes.rootDir || null,
          favoriteCount: favoritesRes.total,
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
        is_favorite: p.is_favorite || false,
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
    // 从路径提取目录名（不再对"年份"/"YYYY-MM"等格式做特殊处理，统一用真实目录名）
    const parts = path.split(/[\\/]/);
    const dirName = parts[parts.length - 1] || path;

    // v0.7: 切到文件夹视图（独立 view，避免时间线 section 被同时高亮）
    setState((prev) => ({ ...prev, currentView: 'folder', selectedAlbumId: null }));

    loadPhotos(path, dirName, 1);
  }, [loadPhotos]);

  const handlePhotoClick = useCallback((photo: Photo) => {
    if (state.selectionMode) {
      setState((prev) => {
        const next = new Set(prev.selectedIds);
        if (next.has(photo.id)) {
          next.delete(photo.id);
        } else {
          // v0.7 §2.7.1：单次最大选中 1000 张
          if (next.size >= 1000) {
            showToast('最多选中 1000 张', 'info');
            return prev;
          }
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

  // v0.7: 显示收藏
  const handleShowFavorites = useCallback(async () => {
    setState((prev) => ({ ...prev, currentView: 'favorites', selectedAlbumId: null, loading: true }));
    try {
      const res = await api.getFavorites();
      const photos = res.photos.map((p) => ({
        id: String(p.id),
        name: p.filename,
        path: p.path,
        size: p.size,
        date: p.date || '',
        type: p.type as 'photo' | 'video',
        is_favorite: p.is_favorite,
        favorited_at: p.favorited_at,
      }));
      setState((prev) => ({
        ...prev,
        photos,
        totalPhotos: res.total,
        selectedTitle: '我的收藏',
        selectedPath: null,
        loading: false,
      }));
    } catch (error) {
      console.error('Failed to load favorites:', error);
      showToast('加载收藏失败', 'error');
      setState((prev) => ({ ...prev, loading: false }));
    }
  }, [showToast]);

  // v0.7: 选择相册
  const handleSelectAlbum = useCallback(async (albumId: number) => {
    setState((prev) => ({ ...prev, currentView: 'album-detail', selectedAlbumId: albumId, loading: true }));
    try {
      const [albumRes, photosRes] = await Promise.all([
        api.getAlbum(albumId),
        api.getAlbumPhotos(albumId, 1, 100),
      ]);
      const photos = photosRes.photos.map((p) => ({
        id: String(p.id),
        name: p.filename,
        path: p.path,
        size: p.size,
        date: p.date || '',
        type: p.type as 'photo' | 'video',
        is_favorite: p.is_favorite || false,
      }));
      setState((prev) => ({
        ...prev,
        photos,
        totalPhotos: photosRes.total,
        selectedTitle: albumRes.name,
        selectedPath: null,
        loading: false,
      }));
    } catch (error) {
      console.error('Failed to load album:', error);
      showToast('加载相册失败', 'error');
      setState((prev) => ({ ...prev, loading: false }));
    }
  }, [showToast]);

  // v0.7: 时间线导航
  const handleShowTimeline = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentView: 'timeline',
      selectedAlbumId: null,
      selectedPath: null,
      selectedTitle: '时间线',
      photos: [],
      totalPhotos: 0,
      loading: false,
    }));
  }, []);

  // v0.7: 相册列表导航
  const handleShowAlbums = useCallback(async () => {
    setState((prev) => ({ ...prev, currentView: 'albums', selectedAlbumId: null, selectedTitle: '所有相册', loading: true }));
    try {
      const res = await api.getAlbums();
      setAlbumsList(res.albums);
    } catch (error) {
      console.error('Failed to load albums:', error);
    }
    setState((prev) => ({ ...prev, loading: false }));
  }, []);

  // 监听导航事件
  useEffect(() => {
    const timelineHandler = () => handleShowTimeline();
    const albumsHandler = () => handleShowAlbums();
    window.addEventListener('navigate:timeline', timelineHandler);
    window.addEventListener('navigate:albums', albumsHandler);
    return () => {
      window.removeEventListener('navigate:timeline', timelineHandler);
      window.removeEventListener('navigate:albums', albumsHandler);
    };
  }, [handleShowTimeline, handleShowAlbums]);

  // v0.7: 创建相册后刷新侧边栏
  const handleCreateAlbum = useCallback(() => {
    setAlbumModal({ open: true, mode: 'create' });
  }, []);

  // v0.7: 加入相册（PhotoCard 右键菜单）
  const handleJoinAlbum = useCallback((photoId: string) => {
    setJoinAlbumPhotoIds([photoId]);
    setJoinAlbumOpen(true);
  }, []);

  const handleJoinAlbums = useCallback((photoIds: string[]) => {
    if (photoIds.length === 0) return;
    setJoinAlbumPhotoIds(photoIds);
    setJoinAlbumOpen(true);
  }, []);

  // v0.7: 单张照片删除
  const handlePhotoDelete = useCallback((photoId: string) => {
    const photo = state.photos.find((p) => p.id === photoId);
    if (photo) {
      setDeletePaths([photo.path]);
    }
  }, [state.photos]);

  // v0.7: 收藏状态变化
  const handleFavoriteChange = useCallback(async (photoId: string, isFavorite: boolean) => {
    setState((prev) => ({
      ...prev,
      photos: prev.photos.map((p) => (p.id === photoId ? { ...p, is_favorite: isFavorite } : p)),
    }));
    // 重新拉取收藏总数，刷新 sidebar 计数
    try {
      const favRes = await api.getFavorites();
      setState((prev) => ({ ...prev, favoriteCount: favRes.total }));
    } catch (error) {
      console.error('Failed to refresh favorite count:', error);
    }
  }, []);

  // v0.7: 相册操作处理
  const handleAlbumAction = useCallback(async (action: 'rename' | 'delete' | 'duplicate', album: { id: number; name: string }) => {
    if (action === 'rename') {
      setAlbumModal({ open: true, mode: 'rename', album });
    } else if (action === 'delete') {
      setAlbumModal({ open: true, mode: 'delete', album });
    } else if (action === 'duplicate') {
      try {
        await api.duplicateAlbum(album.id);
        showToast('相册已复制', 'success');
        handleSelectAlbum(album.id);
      } catch (error) {
        console.error('Failed to duplicate album:', error);
        showToast('复制相册失败', 'error');
      }
    }
  }, [showToast, handleSelectAlbum]);

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
          currentView={state.currentView}
          selectedAlbumId={state.selectedAlbumId}
          onShowFavorites={handleShowFavorites}
          onSelectAlbum={handleSelectAlbum}
          onCreateAlbum={handleCreateAlbum}
          favoriteCount={state.favoriteCount}
          onAlbumAction={handleAlbumAction}
        />
        {state.currentView === 'albums' ? (
          <section className="flex-1 flex flex-col overflow-hidden bg-page min-h-0">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold text-text-primary">{t('sidebar.allAlbums')}</h2>
              <span className="text-sm text-text-secondary">{albumsList.length} {t('sidebar.albumSet')}</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {state.loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin w-8 h-8 border-4 border-border border-t-primary rounded-full" />
                </div>
              ) : albumsList.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-text-secondary">
                  <p className="text-base">{t('sidebar.allAlbums')}</p>
                  <p className="text-sm mt-1 opacity-70">{t('sidebar.newAlbum')}</p>
                </div>
              ) : (
                <div
                  className="grid gap-2 p-3"
                  style={{
                    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                    gridAutoRows: '220px',
                    alignContent: 'start',
                  }}
                >
                  {albumsList.map((album) => (
                    <button
                      key={album.id}
                      onClick={() => handleSelectAlbum(album.id)}
                      onContextMenu={(e) => {
                        e.preventDefault();
                        handleAlbumAction('rename', { id: album.id, name: album.name });
                      }}
                      className="album-card card-hover relative rounded-md overflow-hidden cursor-pointer text-left group"
                      style={{ minHeight: '220px' }}
                    >
                      {(album as any).cover_photo_path ? (
                        <div
                          className="w-full h-full bg-page"
                          style={{ backgroundImage: `url(${api.getThumbnail((album as any).cover_photo_path)})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
                        />
                      ) : (
                        <div className="tile-default">
                          <span className="emoji">📷</span>
                          <span className="label">PHOTOS</span>
                        </div>
                      )}
                      <div className="album-card-label absolute bottom-0 left-0 right-0 px-3 py-2.5 bg-gradient-to-t from-black/65 to-transparent text-white">
                        <div className="text-sm font-medium truncate">{album.name}</div>
                        <div className="text-[11px] font-mono opacity-85 mt-0.5">{album.photo_count} 张</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        ) : state.selectedPath ? (
          // 选中了某个文件夹/月份路径，使用 MainContent 按路径显示
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
            albumId={null}
            onJoinAlbum={handleJoinAlbum}
            onJoinAlbums={handleJoinAlbums}
            onPhotoDelete={handlePhotoDelete}
            onFavoriteChange={handleFavoriteChange}
          />
        ) : state.selectedAlbumId ? (
          // 选中了某个相册，使用 MainContent 显示相册内照片
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
            albumId={state.selectedAlbumId}
            onJoinAlbum={handleJoinAlbum}
            onJoinAlbums={handleJoinAlbums}
            onPhotoDelete={handlePhotoDelete}
            onFavoriteChange={handleFavoriteChange}
          />
        ) : state.currentView === 'favorites' ? (
          <MainContent
            title={state.selectedTitle || t('sidebar.myFavorites')}
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
            onLoadMore={undefined}
            albumId={null}
            onJoinAlbum={handleJoinAlbum}
            onJoinAlbums={handleJoinAlbums}
            onPhotoDelete={handlePhotoDelete}
            onFavoriteChange={handleFavoriteChange}
          />
        ) : (
          <TimelineView
            onPhotoClick={handlePhotoClick}
            selectionMode={state.selectionMode}
            selectedIds={state.selectedIds}
            onSelect={handleSelect}
            onSelectAll={handleSelectAll}
            onDeleteSelected={handleDelete}
            onJoinAlbums={handleJoinAlbums}
            onPhotosChange={(photos) => setState(prev => ({ ...prev, photos }))}
            onJoinAlbum={handleJoinAlbum}
            onDelete={handlePhotoDelete}
            onFavoriteChange={handleFavoriteChange}
          />
        )}
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
        onSelectAlbum={handleSelectAlbum}
        onPhotoUpdate={async (updated) => {
          setState((prev) => ({
            ...prev,
            photos: prev.photos.map((p) => (p.id === updated.id ? { ...p, ...updated } : p)),
          }));
          if (previewPhoto?.id === updated.id) {
            setPreviewPhoto({ ...previewPhoto, ...updated });
          }
          // 重新拉取收藏总数，刷新 sidebar 计数
          try {
            const favRes = await api.getFavorites();
            setState((prev) => ({ ...prev, favoriteCount: favRes.total }));
          } catch (error) {
            console.error('Failed to refresh favorite count:', error);
          }
        }}
      />
      <DeleteConfirmDialog
        isOpen={deletePaths.length > 0}
        onClose={() => setDeletePaths([])}
        paths={deletePaths}
        onDelete={handleDeleteComplete}
      />
      
      {/* v0.7: Album Management Modal */}
      <AlbumManageModal
        isOpen={albumModal.open}
        onClose={() => setAlbumModal({ open: false, mode: 'create' })}
        mode={albumModal.mode}
        album={albumModal.album}
        onSaved={() => {
          setAlbumModal({ open: false, mode: 'create' });
          // 广播相册变更，触发 Sidebar 刷新
          window.dispatchEvent(new CustomEvent('albums:changed'));
          // Refresh albums list
          api.getAlbums().catch(console.error);
        }}
      />
      
      {/* v0.7: Join Album Modal */}
      <JoinAlbumModal
        isOpen={joinAlbumOpen}
        onClose={() => { setJoinAlbumOpen(false); setJoinAlbumPhotoIds([]); }}
        photoIds={joinAlbumPhotoIds}
        onJoined={() => { setJoinAlbumOpen(false); setJoinAlbumPhotoIds([]); }}
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
