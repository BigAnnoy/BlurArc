import { useState, useEffect } from 'react';
import type { YearNode, DirNode } from '../../types';
import { StatsCard } from '../sidebar/StatsCard';
import { DirectoryTree } from '../sidebar/DirectoryTree';
import { useI18n } from '../../contexts/I18nContext';
import { api } from '../../services/api';
import { ContextMenu } from '../common/ContextMenu';
import { buildAlbumMenu } from '../common/menuBuilders';
import { AlbumCoverDefault } from '../common/AlbumCoverDefault';
import { useToast } from '../common/Toast';

interface Album {
  id: number;
  name: string;
  description: string;
  cover_photo_id: number | null;
  photo_count: number;
  created_at: string;
}

interface SidebarProps {
  stats: { total: number; videos: number; size: string } | null;
  years: YearNode[];
  rootDir: DirNode | null;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  onImport: () => void;
  // v0.7 新增
  currentView?: 'timeline' | 'favorites' | 'albums' | 'album-detail' | 'folder';
  selectedAlbumId?: number | null;
  onShowFavorites?: () => void;
  onSelectAlbum?: (albumId: number) => void;
  onCreateAlbum?: () => void;
  favoriteCount?: number;
  onAlbumAction?: (action: 'rename' | 'delete' | 'duplicate', album: Album) => void;
  onRefreshCounters?: () => Promise<void>;
}

export function Sidebar({
  stats,
  years,
  rootDir,
  selectedPath,
  onSelectPath,
  onImport,
  currentView = 'timeline',
  selectedAlbumId = null,
  onShowFavorites,
  onSelectAlbum,
  onCreateAlbum,
  favoriteCount = 0,
  onAlbumAction,
  onRefreshCounters,
}: SidebarProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const [albums, setAlbums] = useState<Album[]>([]);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; album: Album } | null>(null);
  const [editingAlbumId, setEditingAlbumId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const [albumSort, setAlbumSort] = useState<'name' | 'oldest' | 'newest'>('name');
  const [showAlbumSort, setShowAlbumSort] = useState(false);

  useEffect(() => {
    api.getAlbums().then(res => setAlbums(res.albums)).catch(console.error);
    // 监听相册变更事件
    const handler = () => {
      api.getAlbums().then(res => setAlbums(res.albums)).catch(console.error);
    };
    window.addEventListener('albums:changed', handler);
    return () => window.removeEventListener('albums:changed', handler);
  }, []);

  const sortedAlbums = [...albums].sort((a, b) => {
    if (albumSort === 'name') return a.name.localeCompare(b.name);
    if (albumSort === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  // v0.7.1: 统一通过 onCreateAlbum 回调触发 App.tsx 的 AlbumManageModal，
  // 避免双重 modal（原先 Sidebar 自己的 modal + App.tsx 的 modal）
  const handleCreateAlbumClick = () => {
    onCreateAlbum?.();
  };

  return (
    <aside className="w-[250px] h-full bg-card border-r border-border flex flex-col overflow-hidden flex-shrink-0">
      <div className="flex-1 overflow-y-auto p-4 min-h-0">
        {stats && <StatsCard total={stats.total} videos={stats.videos} size={stats.size} />}

        {/* Section 1: 收藏 */}
        <div className="flex items-center justify-between text-[12px] font-bold uppercase tracking-[0.08em] text-text-secondary mt-5 mb-2 py-1 first:mt-0">
          <span>{t('sidebar.favorites')}</span>
        </div>
        <button
          onClick={onShowFavorites}
          className={`w-full flex items-center gap-1.5 px-2.5 py-1.5 -ml-2.5 mb-0.5 text-[13px] rounded-[6px] transition-all cursor-pointer ${
            currentView === 'favorites'
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:bg-page hover:text-text-primary'
          }`}
        >
          <span className="w-3.5 h-3.5 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="currentColor" stroke="none" className="w-3 h-3">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
          </span>
          <span className="flex-1 text-left">{t('sidebar.myFavorites')}</span>
          <span className="text-[11px] font-mono opacity-70">{favoriteCount}</span>
        </button>

        {/* Section 2: 时间线 */}
        <div className="flex items-center justify-between text-[12px] font-bold uppercase tracking-[0.08em] text-text-secondary mt-5 mb-2 py-1">
          <span>{t('sidebar.timeline')}</span>
        </div>
        <button
          onClick={() => window.dispatchEvent(new CustomEvent('navigate:timeline'))}
          className={`w-full flex items-center gap-1.5 px-2.5 py-1.5 -ml-2.5 mb-0.5 text-[13px] rounded-[6px] transition-all cursor-pointer ${
            currentView === 'timeline'
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:bg-page hover:text-text-primary'
          }`}
        >
          <span className="w-3.5 h-3.5 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </span>
          <span className="flex-1 text-left">{t('sidebar.browseAll')}</span>
          <span className="text-[11px] font-mono opacity-70">{stats?.total || 0}</span>
        </button>

        {/* Section 3: 相册集 */}
        <div className="flex items-center justify-between text-[12px] font-bold uppercase tracking-[0.08em] text-text-secondary mt-5 mb-2 py-1">
          <span>{t('sidebar.albumSet')}</span>
          <div className="flex items-center gap-0.5">
            <div className="relative">
              <button
                onClick={() => setShowAlbumSort(!showAlbumSort)}
                className="w-[18px] h-[18px] rounded-[6px] border-none bg-transparent text-text-tertiary cursor-pointer flex items-center justify-center text-[16px] hover:bg-page hover:text-primary transition-colors"
                title={t('sidebar.sort')}
              >
                ↕
              </button>
              {showAlbumSort && (
                <div className="absolute right-0 top-full mt-1 w-32 bg-card border border-border rounded-lg shadow-lg z-50">
                  {(['name', 'oldest', 'newest'] as const).map(key => (
                    <button
                      key={key}
                      onClick={() => { setAlbumSort(key); setShowAlbumSort(false); }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-page transition-colors ${
                        albumSort === key ? 'text-primary font-medium' : 'text-text-primary'
                      }`}
                    >
                      {key === 'name' ? t('sidebar.sortByName') : key === 'oldest' ? t('sidebar.sortByOldest') : t('sidebar.sortByNewest')}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        {/* 所有相册入口 */}
        <button
          onClick={() => window.dispatchEvent(new CustomEvent('navigate:albums'))}
          className={`w-full flex items-center gap-1.5 px-2.5 py-1.5 -ml-2.5 mb-0.5 text-[13px] rounded-[6px] transition-all cursor-pointer ${
            currentView === 'albums'
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:bg-page hover:text-text-primary'
          }`}
        >
          <span className="w-3.5 h-3.5 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3">
              <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
          </span>
          <span className="flex-1 text-left">{t('sidebar.allAlbums')}</span>
          <span className="text-[11px] font-mono opacity-70">{albums.length}</span>
        </button>

        {/* 相册列表 */}
        <div className="space-y-0.5">
          {sortedAlbums.map(album => (
            editingAlbumId === album.id ? (
              <div key={album.id} className="flex items-center gap-2 px-2.5 py-1.5">
                <input
                  type="text"
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onKeyDown={async (e) => {
                    if (e.key === 'Enter' && editingName.trim()) {
                      try {
                        await api.updateAlbum(album.id, { name: editingName.trim() });
                        const res = await api.getAlbums();
                        setAlbums(res.albums);
                        window.dispatchEvent(new CustomEvent('albums:changed'));
                        showToast(t('sidebar.renameSuccess'), 'success');
                      } catch (error) {
                        console.error('重命名失败:', error);
                        showToast(t('sidebar.renameFailed'), 'error');
                      }
                      setEditingAlbumId(null);
                    } else if (e.key === 'Escape') {
                      setEditingAlbumId(null);
                    }
                  }}
                  onBlur={async () => {
                    // 失焦时如名称未变则取消编辑，名称变了则保存
                    if (editingName.trim() && editingName.trim() !== album.name) {
                      try {
                        await api.updateAlbum(album.id, { name: editingName.trim() });
                        const res = await api.getAlbums();
                        setAlbums(res.albums);
                        window.dispatchEvent(new CustomEvent('albums:changed'));
                      } catch (error) {
                        console.error('重命名失败:', error);
                      }
                    }
                    setEditingAlbumId(null);
                  }}
                  className="flex-1 px-2 py-1 text-sm border border-primary rounded focus:outline-none"
                  autoFocus
                />
              </div>
            ) : (
              <button
                key={album.id}
                onClick={() => onSelectAlbum?.(album.id)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  setContextMenu({ x: e.clientX, y: e.clientY, album });
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.dataTransfer.dropEffect = 'copy';
                }}
                onDrop={async (e) => {
                  e.preventDefault();
                  const photoId = e.dataTransfer.getData('photo/id');
                  const sourceAlbumId = e.dataTransfer.getData('album/id');
                  if (photoId) {
                    try {
                      await api.addPhotoToAlbum(album.id, Number(photoId));
                      showToast(t('sidebar.addedToAlbum', { name: album.name }), 'success');
                      await onRefreshCounters?.();
                    } catch (error) {
                      showToast(t('sidebar.addFailed'), 'error');
                    }
                  } else if (sourceAlbumId && Number(sourceAlbumId) !== album.id) {
                    try {
                      await api.mergeAlbums(Number(sourceAlbumId), album.id);
                      showToast(t('sidebar.mergedToAlbum', { name: album.name }), 'success');
                      await onRefreshCounters?.();
                    } catch (error) {
                      showToast(t('sidebar.mergeFailed'), 'error');
                    }
                  }
                }}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('album/id', String(album.id));
                  e.dataTransfer.effectAllowed = 'move';
                }}
                className={`w-full flex items-center gap-2 px-2.5 py-[5px] -ml-2.5 mb-0.5 text-[13px] rounded-[6px] transition-all cursor-pointer ${
                  currentView === 'album-detail' && selectedAlbumId === album.id
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:bg-page hover:text-text-primary'
                }`}
              >
                {/* 相册封面 / 默认占位（v0.7 §5.8：cyan 渐变 + 📷） */}
                <div
                  className="w-[26px] h-[26px] rounded-[5px] flex-shrink-0 overflow-hidden relative"
                  style={
                    (album as any).cover_photo_path
                      ? { backgroundImage: `url(${api.getThumbnail((album as any).cover_photo_path)})`, backgroundSize: 'cover', backgroundPosition: 'center' }
                      : undefined
                  }
                >
                  {!(album as any).cover_photo_path && (
                    <AlbumCoverDefault size="thumb" />
                  )}
                </div>
                <span className="flex-1 text-left truncate min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">{album.name}</span>
                <span className="text-[11px] font-mono opacity-70">{album.photo_count}</span>
              </button>
            )
          ))}
        </div>

        {/* 新建相册按钮（点击触发 App.tsx 的 AlbumManageModal，v0.7.1 修复双重弹窗） */}
        <button
          onClick={handleCreateAlbumClick}
          className="new-album-row w-full text-left transition-all duration-150"
        >
          <span className="plus">+</span>
          <span>{t('sidebar.newAlbum')}</span>
        </button>

        {/* Section 4: 文件夹 */}
        <div className="flex items-center justify-between text-[12px] font-bold uppercase tracking-[0.08em] text-text-secondary mt-5 mb-2 py-1">
          <span>{t('sidebar.folders')}</span>
        </div>
        <DirectoryTree years={years} rootDir={rootDir} selectedPath={selectedPath} onSelect={onSelectPath} onRefreshCounters={onRefreshCounters} />
      </div>

      {/* 导入按钮 */}
      <div className="p-4 border-t border-border flex-shrink-0">
        <button
          onClick={onImport}
          className="w-full py-2.5 bg-primary text-white border-none rounded-lg font-medium text-sm cursor-pointer hover:bg-primary-hover transition-all duration-150"
        >
          {t('sidebar.importPhotos')}
        </button>
      </div>

      {/* 相册右键菜单 */}
      {contextMenu && (
        <ContextMenu
          isOpen={true}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          groups={buildAlbumMenu({
            onOpen: () => onSelectAlbum?.(contextMenu.album.id),
            onRename: () => onAlbumAction?.('rename', contextMenu.album),
            onDuplicate: () => onAlbumAction?.('duplicate', contextMenu.album),
            onDelete: () => onAlbumAction?.('delete', contextMenu.album),
            t,
          })}
        />
      )}
    </aside>
  );
}
