import { useState } from 'react';
import { Modal } from '../common/Modal';
import { useToast } from '../common/Toast';
import { api } from '../../services/api';
import { useI18n } from '../../contexts/I18nContext';

interface DeleteConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  paths: string[];
  onDelete: () => void;
}

export function DeleteConfirmDialog({ isOpen, onClose, paths, onDelete }: DeleteConfirmDialogProps) {
  const { showToast } = useToast();
  const [deleting, setDeleting] = useState(false);
  const { t } = useI18n();

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.deletePhotos(paths);
      onDelete();
      onClose();
    } catch (error) {
      const message = error instanceof Error ? error.message : t('delete.failed');
      showToast(message, 'error');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('delete.title')}
      size="sm"
      footer={
        <>
          <button
            onClick={onClose}
            disabled={deleting}
            className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary disabled:opacity-50 transition-all"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-4 py-2 bg-red-500 text-white rounded-md text-sm hover:bg-red-600 disabled:opacity-50 transition-all"
          >
            {deleting ? t('delete.deleting') : t('delete.confirmButton')}
          </button>
        </>
      }
    >
      <div className="text-center py-4 px-5">
        <div className="text-4xl mb-4">🗑️</div>
        <p className="text-lg font-medium mb-2">{t('delete.confirmMessage')}</p>
        <p className="text-sm text-text-secondary">
          {t('delete.willDelete', { count: paths.length })}
        </p>
        <p className="text-xs text-text-tertiary mt-2">{t('delete.cannotUndo')}</p>
      </div>
    </Modal>
  );
}
