import type { Photo } from '../../types';
import { PhotoCard } from './PhotoCard';
import { useI18n } from '../../contexts/I18nContext';

interface PhotoGridProps {
  photos: Photo[];
  selectionMode?: boolean;
  selectedIds?: Set<string>;
  onPhotoClick: (photo: Photo) => void;
}

export function PhotoGrid({ photos, selectionMode, selectedIds, onPhotoClick }: PhotoGridProps) {
  const { t } = useI18n();
  
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
    </div>
  );
}
