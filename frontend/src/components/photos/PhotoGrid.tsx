import type { Photo } from '../../types';
import { PhotoCard } from './PhotoCard';
import { useI18n } from '../../contexts/I18nContext';
import { useEffect, useRef } from 'react';

interface PhotoGridProps {
  photos: Photo[];
  selectionMode?: boolean;
  selectedIds?: Set<string>;
  onPhotoClick: (photo: Photo) => void;
  hasMore?: boolean;
  onLoadMore?: () => void;
  groupBy?: 'all' | 'month' | 'year';
  displayMode?: 'square' | 'original';
  sort?: string;
  onDragStart?: (photoId: string) => void;
  onDragOver?: (e: React.DragEvent, photoId: string) => void;
  onDrop?: (e: React.DragEvent, photoId: string) => void;
  draggedPhoto?: string | null;
  dragOverPhoto?: string | null;
  // v0.7: 右键菜单支持
  albumId?: number | null;
  onJoinAlbum?: (photoId: string) => void;
  onDelete?: (photoId: string) => void;
  onRemoveFromAlbum?: () => void;
  onFavoriteChange?: (photoId: string, isFavorite: boolean) => void;
  // v0.7 §4.2：缩放级别（0=小 120px, 1=中 180px 默认, 2=大 240px）
  zoomLevel?: number;
}

export function PhotoGrid({ photos, selectionMode, selectedIds, onPhotoClick, hasMore, onLoadMore, groupBy = 'all', displayMode = 'square', sort, onDragStart, onDragOver, onDrop, draggedPhoto, dragOverPhoto, albumId, onJoinAlbum, onDelete, onRemoveFromAlbum, onFavoriteChange, zoomLevel = 1 }: PhotoGridProps) {
  const { t } = useI18n();
  const observerRef = useRef<HTMLDivElement>(null);
  // v0.7 §4.2：根据缩放级别计算单元格尺寸
  const cellSize = zoomLevel === 0 ? 120 : zoomLevel === 2 ? 240 : 180;
  const gridStyle = { gridTemplateColumns: `repeat(auto-fill, minmax(${cellSize}px, 1fr))`, gridAutoRows: `${cellSize}px` };
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMore && onLoadMore) {
          onLoadMore();
        }
      },
      { rootMargin: '200px' }
    );
    
    if (observerRef.current) {
      observer.observe(observerRef.current);
    }
    
    return () => observer.disconnect();
  }, [hasMore, onLoadMore]);
  
  if (photos.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
        <div className="text-5xl mb-4 opacity-50">🖼️</div>
        <div className="text-lg font-medium mb-2">{t('main.selectToBrowse')}</div>
        <div className="text-text-secondary max-w-[320px] leading-relaxed">
          {t('main.clickToBrowse')}
        </div>
      </div>
    );
  }

  // 按日期分组照片
  const groupPhotosByDate = (photos: Photo[], groupBy: 'month' | 'year') => {
    const groups: { [key: string]: Photo[] } = {};
    
    photos.forEach(photo => {
      const date = new Date(photo.date);
      let key: string;
      
      if (groupBy === 'year') {
        key = date.getFullYear().toString();
      } else {
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      }
      
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(photo);
    });
    
    // 按日期降序排序
    return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]));
  };

  const renderPhotoGrid = (photosToRender: Photo[]) => (
    <div className="flex-1 min-h-0 grid gap-1 p-1 overflow-y-auto content-start" style={gridStyle}>
      {photosToRender.map((photo) => (
        <PhotoCard
          key={photo.id}
          photo={photo}
          selected={selectionMode && selectedIds?.has(photo.id)}
          selectionMode={selectionMode}
          onClick={() => onPhotoClick(photo)}
          displayMode={displayMode}
          draggable={sort === 'manual'}
          onDragStart={onDragStart ? () => onDragStart(photo.id) : undefined}
          onDragOver={onDragOver ? (e) => onDragOver(e, photo.id) : undefined}
          onDrop={onDrop ? (e) => onDrop(e, photo.id) : undefined}
          isDragged={draggedPhoto === photo.id}
          isDragOver={dragOverPhoto === photo.id}
          albumId={albumId}
          onJoinAlbum={onJoinAlbum}
          onDelete={onDelete}
          onRemoveFromAlbum={onRemoveFromAlbum}
          onFavoriteChange={onFavoriteChange}
        />
      ))}
      {hasMore && (
        <div ref={observerRef} className="flex items-center justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-border border-t-primary rounded-full" />
        </div>
      )}
    </div>
  );

  if (groupBy === 'all') {
    return renderPhotoGrid(photos);
  }

  const groupedPhotos = groupPhotosByDate(photos, groupBy);

  return (
    <div className="flex-1 overflow-y-auto">
      {groupedPhotos.map(([dateKey, datePhotos]) => (
        <div key={dateKey} className="mb-6">
          <div className="sticky top-0 z-10 bg-page px-4 py-2 border-b border-border">
            <h3 className="text-sm font-semibold text-text-primary">
              {groupBy === 'year' ? dateKey : dateKey}
            </h3>
          </div>
          <div className="grid gap-1 p-1" style={gridStyle}>
            {datePhotos.map((photo) => (
              <PhotoCard
                key={photo.id}
                photo={photo}
                selected={selectionMode && selectedIds?.has(photo.id)}
                selectionMode={selectionMode}
                onClick={() => onPhotoClick(photo)}
                displayMode={displayMode}
                draggable={sort === 'manual'}
                onDragStart={onDragStart ? () => onDragStart(photo.id) : undefined}
                onDragOver={onDragOver ? (e) => onDragOver(e, photo.id) : undefined}
                onDrop={onDrop ? (e) => onDrop(e, photo.id) : undefined}
                isDragged={draggedPhoto === photo.id}
                isDragOver={dragOverPhoto === photo.id}
                albumId={albumId}
                onJoinAlbum={onJoinAlbum}
                onDelete={onDelete}
                onRemoveFromAlbum={onRemoveFromAlbum}
                onFavoriteChange={onFavoriteChange}
              />
            ))}
          </div>
        </div>
      ))}
      {hasMore && (
        <div ref={observerRef} className="flex items-center justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-border border-t-primary rounded-full" />
        </div>
      )}
    </div>
  );
}
