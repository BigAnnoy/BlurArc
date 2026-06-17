import { useState, useEffect, useCallback } from 'react';
import { Modal } from '../common/Modal';
import { api } from '../../services/api';
import { useI18n } from '../../contexts/I18nContext';
import type { Photo } from '../../types';

interface PhotoPreviewProps {
  isOpen: boolean;
  onClose: () => void;
  photo: Photo | null;
  photos: Photo[];
  onNavigate: (photo: Photo) => void;
}

export function PhotoPreview({ isOpen, onClose, photo, photos, onNavigate }: PhotoPreviewProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const { t } = useI18n();

  useEffect(() => {
    if (photo && photos.length > 0) {
      const idx = photos.findIndex((p) => p.id === photo.id);
      setCurrentIndex(idx >= 0 ? idx : 0);
    }
  }, [photo, photos]);

  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      const prevPhoto = photos[currentIndex - 1];
      setCurrentIndex(currentIndex - 1);
      onNavigate(prevPhoto);
    }
  }, [currentIndex, photos, onNavigate]);

  const handleNext = useCallback(() => {
    if (currentIndex < photos.length - 1) {
      const nextPhoto = photos[currentIndex + 1];
      setCurrentIndex(currentIndex + 1);
      onNavigate(nextPhoto);
    }
  }, [currentIndex, photos, onNavigate]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') handlePrev();
      if (e.key === 'ArrowRight') handleNext();
    },
    [handlePrev, handleNext]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, handleKeyDown]);

  const handleOpenFile = async () => {
    if (photo) {
      try {
        await api.openFile(photo.path);
      } catch (error) {
        console.error('Failed to open file:', error);
      }
    }
  };

  if (!photo) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('preview.title')}
      size="xl"
      footer={
        <>
          <button onClick={onClose} className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all">
            {t('preview.close')}
          </button>
          <button onClick={handleOpenFile} className="px-4 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-all">
            {t('preview.openFile')}
          </button>
        </>
      }
    >
      <div className="relative">
        {/* Navigation buttons */}
        {currentIndex > 0 && (
          <button
            onClick={handlePrev}
            className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/50 text-white rounded-full flex items-center justify-center hover:bg-black/70 transition-all z-10"
          >
            ‹
          </button>
        )}
        {currentIndex < photos.length - 1 && (
          <button
            onClick={handleNext}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/50 text-white rounded-full flex items-center justify-center hover:bg-black/70 transition-all z-10"
          >
            ›
          </button>
        )}

        {/* Image/Video - 容器自适应内容尺寸 */}
        <div className="flex items-center justify-center bg-black/5 rounded-lg overflow-hidden" style={{ minHeight: '300px', maxHeight: '70vh' }}>
          {photo.type === 'video' ? (
            <video
              src={api.getFile(photo.path)}
              controls
              className="max-w-full max-h-[70vh] object-contain"
            />
          ) : (
            <img
              src={api.getFile(photo.path)}
              alt={photo.name}
              className="max-w-full max-h-[70vh] object-contain"
            />
          )}
        </div>

        {/* Info - 显示日期 */}
        <div className="mt-4 space-y-1 text-sm text-text-secondary">
          <p className="font-medium text-text-primary">{photo.name}</p>
          <p>{t('preview.size')}: {(photo.size / 1024 / 1024).toFixed(2)} MB</p>
          <p>{t('preview.date')}: {photo.date || t('preview.unknown')}</p>
          {photo.type === 'video' && photo.duration && (
            <p>{t('preview.duration')}: {photo.duration}</p>
          )}
        </div>

        {/* Index badge */}
        <div className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
          {currentIndex + 1} / {photos.length}
        </div>
      </div>
    </Modal>
  );
}
