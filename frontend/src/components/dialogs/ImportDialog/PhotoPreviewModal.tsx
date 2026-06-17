import { api } from '../../../services/api';
import { useI18n } from '../../../contexts/I18nContext';
import type { ImportPhoto } from './types';

interface PhotoPreviewModalProps {
  photo: ImportPhoto | null;
  onClose: () => void;
}

export function PhotoPreviewModal({ photo, onClose }: PhotoPreviewModalProps) {
  const { t } = useI18n();

  if (!photo) return null;

  const sizeMB = photo.size ? (photo.size / (1024 * 1024)).toFixed(2) : '0';

  const handleOpenFile = () => {
    api.openFile(photo.path);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={onClose}
    >
      <div
        className="bg-card rounded-lg shadow-xl max-w-3xl w-full mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h3 className="font-medium">{t('photoPreview.preview')}: {photo.name}</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-md hover:bg-page flex items-center justify-center transition-all"
          >
            ✕
          </button>
        </div>

        {/* 图片 */}
        <div className="flex items-center justify-center bg-page max-h-[60vh] overflow-hidden">
          <img
            src={photo.url || api.getFile(photo.path)}
            alt={photo.name}
            className="max-w-full max-h-[60vh] object-contain"
          />
        </div>

        {/* 信息 */}
        <div className="px-4 py-3 border-t border-border space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">{t('photoPreview.fileName')}:</span>
            <span>{photo.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">{t('photoPreview.fileSize')}:</span>
            <span>{sizeMB} MB</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">{t('photoPreview.filePath')}:</span>
            <span className="truncate max-w-[300px]" title={photo.path}>{photo.path}</span>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex justify-end gap-3 px-4 py-3 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all"
          >
            {t('photoPreview.close')}
          </button>
          <button
            onClick={handleOpenFile}
            className="px-4 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-all"
          >
            {t('photoPreview.openFile')}
          </button>
        </div>
      </div>
    </div>
  );
}
