import { useState } from 'react';
import type { Photo } from '../../types';
import { PhotoGrid } from '../photos/PhotoGrid';
import { PhotoToolbar } from '../common/PhotoToolbar';
import { SelectionBanner } from '../common/SelectionBanner';
import { useI18n } from '../../contexts/I18nContext';

interface MainContentProps {
  title: string;
  count: number;
  photos: Photo[];
  loading?: boolean;
  selectionMode: boolean;
  selectedIds: Set<string>;
  onPhotoClick: (photo: Photo) => void;
  onSelect: () => void;
  onSelectAll: () => void;
  onDelete: () => void;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onFilterChange?: (filters: string[]) => void;
  onSortChange?: (sort: string) => void;
  onRemoveFromAlbum?: () => void;
  albumId?: number | null;
  // v0.7: 右键菜单
  onJoinAlbum?: (photoId: string) => void;
  onJoinAlbums?: (photoIds: string[]) => void;
  onPhotoDelete?: (photoId: string) => void;
  onFavoriteChange?: (photoId: string, isFavorite: boolean) => void;
  // v0.7: 排序状态（从 App 传入，用于触发重载）
  sort?: string;
}

export function MainContent({ title, count, photos, loading, selectionMode, selectedIds, onPhotoClick, onSelect, onSelectAll, onDelete, hasMore, onLoadMore, onFilterChange, onSortChange, onRemoveFromAlbum, albumId, onJoinAlbum, onJoinAlbums, onPhotoDelete, onFavoriteChange, sort: externalSort }: MainContentProps) {
  const selectedCount = selectedIds.size;
  const { t } = useI18n();
  const [filters, setFilters] = useState<string[]>([]);
  const [internalSort, setInternalSort] = useState('media_date_desc');
  const [group, setGroup] = useState<'all' | 'month' | 'year'>('all');
  
  // 使用外部传入的 sort（如果有），否则使用内部 sort
  const sort = externalSort ?? internalSort;
  // v0.7 §3.2.2/§4.2：布局切换 + 缩放（与 PhotoToolbar 公共组件配合）
  const [layoutMode, setLayoutMode] = useState<'grid' | 'masonry'>('grid');
  const [zoomLevel, setZoomLevel] = useState(1);
  const [draggedPhoto, setDraggedPhoto] = useState<string | null>(null);
  const [dragOverPhoto, setDragOverPhoto] = useState<string | null>(null);

  const filterOptions = [
    { key: 'photo', label: t('filter.photoOnly'), icon: '📷' },
    { key: 'video', label: t('filter.videoOnly'), icon: '🎥' },
    { key: 'favorite', label: t('filter.favoriteOnly'), icon: '⭐' },
    { key: 'not_in_album', label: t('filter.notInAlbum'), icon: '📁' }
  ];

  const sortOptions = [
    { key: 'media_date_desc', label: t('sort.dateDesc') },
    { key: 'media_date_asc', label: t('sort.dateAsc') },
    { key: 'manual', label: t('sort.manual') }
  ];

  const groupOptions = [
    { key: 'all', label: t('main.groupAll') },
    { key: 'month', label: t('main.groupMonth') },
    { key: 'year', label: t('main.groupYear') }
  ];

  const handleFilterChange = (newFilters: string[]) => {
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  const handleSortChange = (newSort: string) => {
    setInternalSort(newSort);
    onSortChange?.(newSort);
  };

  const handleDragStart = (photoId: string) => {
    if (sort === 'manual' && albumId) {
      setDraggedPhoto(photoId);
    }
  };

  const handleDragOver = (e: React.DragEvent, photoId: string) => {
    e.preventDefault();
    if (sort === 'manual' && albumId && draggedPhoto && draggedPhoto !== photoId) {
      setDragOverPhoto(photoId);
    }
  };

  const handleDrop = (e: React.DragEvent, targetPhotoId: string) => {
    e.preventDefault();
    if (sort === 'manual' && albumId && draggedPhoto && draggedPhoto !== targetPhotoId) {
      // 重新排序照片
      const draggedIndex = photos.findIndex(p => p.id === draggedPhoto);
      const targetIndex = photos.findIndex(p => p.id === targetPhotoId);
      
      if (draggedIndex !== -1 && targetIndex !== -1) {
        const newPhotos = [...photos];
        const [draggedItem] = newPhotos.splice(draggedIndex, 1);
        newPhotos.splice(targetIndex, 0, draggedItem);
        
        // 这里应该调用后端 API 保存排序，但暂时只更新本地状态
        // TODO: 调用 api.updateAlbumPhotoOrder(albumId, newPhotos.map(p => p.id))
      }
    }
    
    setDraggedPhoto(null);
    setDragOverPhoto(null);
  };

  return (
    <section className="flex-1 flex flex-col overflow-hidden bg-page min-h-0">
      {/* 公共工具栏（v0.7 §4.2：与 TimelineView 共用 PhotoToolbar） */}
      <PhotoToolbar
        title={title}
        count={count}
        loading={loading}
        layoutMode={layoutMode}
        onLayoutModeChange={setLayoutMode}
        zoomLevel={zoomLevel}
        onZoomChange={setZoomLevel}
        filters={filters}
        onFiltersChange={handleFilterChange}
        filterOptions={filterOptions}
        sort={sort}
        onSortChange={handleSortChange}
        sortOptions={sortOptions}
        selectionMode={selectionMode}
        onSelect={onSelect}
      />
      {/* 选择模式 banner（v0.7 §2.7：与 TimelineView 共用 SelectionBanner） */}
      {selectionMode && (
        <SelectionBanner
          selectedCount={selectedCount}
          totalCount={count}
          selectedIds={selectedIds}
          onSelectAll={onSelectAll}
          onDelete={onDelete}
          onJoinAlbums={onJoinAlbums}
          onRemoveFromAlbum={albumId && onRemoveFromAlbum ? onRemoveFromAlbum : undefined}
          onCancel={onSelect}
        />
      )}
      {/* 分组方式 tabs */}
      <div className="flex items-center gap-0.5 px-3 bg-card border-b border-border">
        <span className="text-[11px] text-text-tertiary tracking-[0.05em] mr-1">{t('main.groupBy')}</span>
        {groupOptions.map(option => (
          <button
            key={option.key}
            onClick={() => setGroup(option.key as 'all' | 'month' | 'year')}
            className={`px-3.5 py-2 text-[13px] cursor-pointer bg-transparent border-none border-b-2 transition-all ${
              group === option.key
                ? 'text-primary font-semibold border-b-primary'
                : 'text-text-secondary font-medium border-b-transparent hover:text-text-primary hover:border-b-border'
            }`}
          >
            {option.key === 'all' ? t('main.groupAll') : option.key === 'month' ? t('main.groupMonth') : t('main.groupYear')}
          </button>
        ))}
      </div>
      {loading && photos.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-3 border-border border-t-primary rounded-full" />
        </div>
      ) : (
        <PhotoGrid
          photos={photos}
          selectionMode={selectionMode}
          selectedIds={selectedIds}
          onPhotoClick={onPhotoClick}
          hasMore={hasMore}
          onLoadMore={onLoadMore}
          groupBy={group}
          sort={sort}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          draggedPhoto={draggedPhoto}
          dragOverPhoto={dragOverPhoto}
          albumId={albumId}
          onJoinAlbum={onJoinAlbum}
          onDelete={onPhotoDelete}
          onRemoveFromAlbum={onRemoveFromAlbum}
          onFavoriteChange={onFavoriteChange}
          layoutMode={layoutMode}
          zoomLevel={zoomLevel}
        />
      )}
    </section>
  );
}
