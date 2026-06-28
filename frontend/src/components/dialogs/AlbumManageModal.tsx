import { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { api } from '../../services/api';
import { useI18n } from '../../contexts/I18nContext';

interface AlbumManageModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: 'create' | 'rename' | 'delete' | 'duplicate';
  album?: { id: number; name: string };
  onSaved: () => void;
}

export function AlbumManageModal({ isOpen, onClose, mode, album, onSaved }: AlbumManageModalProps) {
  const { t } = useI18n();
  const [name, setName] = useState(album?.name || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // modal 打开或 album 变化时重置 name
  useEffect(() => {
    if (isOpen) {
      setName(album?.name || '');
      setError('');
    }
  }, [isOpen, album?.id, album?.name]);

  const handleSave = async () => {
    if (!name.trim() && mode !== 'delete') {
      setError(t('albumModal.nameRequired'));
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      if (mode === 'create') {
        await api.createAlbum(name.trim());
      } else if (mode === 'rename' && album) {
        await api.updateAlbum(album.id, { name: name.trim() });
      } else if (mode === 'delete' && album) {
        await api.deleteAlbum(album.id);
      } else if (mode === 'duplicate' && album) {
        await api.duplicateAlbum(album.id);
      }
      
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.message || t('albumModal.actionFailed'));
    }
    
    setLoading(false);
  };

  const title = mode === 'create' ? t('albumModal.createTitle') : mode === 'rename' ? t('albumModal.renameTitle') : mode === 'delete' ? t('albumModal.deleteTitle') : t('albumModal.duplicateTitle');

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="p-6">
        {mode === 'delete' ? (
          <div>
            <p className="text-text-primary mb-4">
              {t('albumModal.deleteConfirm', { name: album?.name ?? '' })}
            </p>
            <p className="text-sm text-text-secondary">
              {t('albumModal.photosNotDeleted')}
            </p>
          </div>
        ) : mode === 'duplicate' ? (
          <p className="text-text-primary">
            {t('albumModal.duplicateConfirm', { name: album?.name ?? '' })}
          </p>
        ) : (
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              {t('sidebar.albumName')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave();
                if (e.key === 'Escape') onClose();
              }}
              className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:border-primary"
              placeholder={t('albumModal.namePlaceholder')}
              autoFocus
            />
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
            <p className="text-xs text-text-tertiary mt-2">
              {t('albumModal.hint')}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className={`px-4 py-2 text-sm rounded-md transition-colors ${
              mode === 'delete'
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-primary text-white hover:bg-primary-hover'
            } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {loading ? t('albumModal.processing') : mode === 'delete' ? t('albumModal.deleteAlbum') : t('common.confirm')}
          </button>
        </div>
      </div>
    </Modal>
  );
}
