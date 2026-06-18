import type { Photo } from '../../types';
import { PhotoGrid } from '../photos/PhotoGrid';
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
}

export function MainContent({ title, count, photos, loading, selectionMode, selectedIds, onPhotoClick, onSelect, onSelectAll, onDelete, hasMore, onLoadMore }: MainContentProps) {
  const selectedCount = selectedIds.size;
  const { t } = useI18n();

  return (
    <section className="flex-1 flex flex-col overflow-hidden bg-page min-h-0">
      <div className="flex items-center justify-between px-5 py-3 bg-card border-b border-border">
        <span className="text-sm font-medium">
          <span className="text-primary font-semibold">{title}</span>
          {count > 0 && <span className="text-text-secondary"> · {t('main.photoCount', { count })}</span>}
          {selectionMode && selectedCount > 0 && <span className="text-primary ml-2">({t('main.selected', { count: selectedCount })})</span>}
          {loading && <span className="text-text-tertiary ml-2">{t('main.loading')}</span>}
        </span>
        <div className="flex gap-2">
          {selectionMode ? (
            <>
              <button
                onClick={onSelect}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-card border border-border rounded-md text-[13px] text-text-primary cursor-pointer hover:border-primary hover:text-primary transition-all"
              >
                {t('common.cancelSelectMode')}
              </button>
              <button
                onClick={onSelectAll}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-card border border-border rounded-md text-[13px] text-text-primary cursor-pointer hover:border-primary hover:text-primary transition-all"
              >
                {selectedCount === count ? t('common.cancelSelect') : t('common.selectAll')}
              </button>
              <button
                onClick={onDelete}
                disabled={selectedCount === 0}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[13px] transition-all ${selectedCount > 0 ? 'bg-red-500 text-white cursor-pointer hover:bg-red-600' : 'bg-card text-text-tertiary cursor-not-allowed border border-border'}`}
              >
                🗑 {t('main.deleteSelected')}
              </button>
            </>
          ) : (
            <button
              onClick={onSelect}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-card border border-border rounded-md text-[13px] text-text-primary cursor-pointer hover:border-primary hover:text-primary transition-all"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
              </svg>
              {t('main.selectMode')}
            </button>
          )}
        </div>
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
        />
      )}
    </section>
  );
}
