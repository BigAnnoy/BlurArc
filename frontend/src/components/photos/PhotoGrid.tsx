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
}

export function PhotoGrid({ photos, selectionMode, selectedIds, onPhotoClick, hasMore, onLoadMore }: PhotoGridProps) {
  const { t } = useI18n();
  const observerRef = useRef<HTMLDivElement>(null);
  
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

  return (
    <div className="flex-1 min-h-0 grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] auto-rows-[180px] gap-1 p-1 overflow-y-auto content-start">
      {photos.map((photo) => (
        <PhotoCard
          key={photo.id}
          photo={photo}
          selected={selectionMode && selectedIds?.has(photo.id)}
          selectionMode={selectionMode}
          onClick={() => onPhotoClick(photo)}
        />
      ))}
      {hasMore && (
        <div ref={observerRef} className="flex items-center justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-border border-t-primary rounded-full" />
        </div>
      )}
    </div>
  );
}
