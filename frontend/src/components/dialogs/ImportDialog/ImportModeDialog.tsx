import { useI18n } from '../../../contexts/I18nContext';
import type { ImportMode } from './types';

interface ImportModeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (mode: ImportMode) => void;
}

export function ImportModeDialog({ isOpen, onClose, onSelect }: ImportModeDialogProps) {
  const { t } = useI18n();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-card rounded-lg shadow-lg max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="p-6">
          <h3 className="text-lg font-medium mb-4">{t('importMode.title')}</h3>
          
          <div className="space-y-3">
            <button
              onClick={() => onSelect('copy')}
              className="w-full p-4 rounded-lg border border-border hover:border-primary hover:bg-primary-light transition-all text-left"
            >
              <div className="flex items-start gap-3">
                <div className="text-2xl">📋</div>
                <div className="flex-1">
                  <div className="font-medium mb-1">{t('importMode.copy')}</div>
                  <div className="text-sm text-text-secondary">
                    {t('importMode.copyDesc')}
                  </div>
                </div>
              </div>
            </button>
            
            <button
              onClick={() => onSelect('move')}
              className="w-full p-4 rounded-lg border border-border hover:border-primary hover:bg-primary-light transition-all text-left"
            >
              <div className="flex items-start gap-3">
                <div className="text-2xl">✂️</div>
                <div className="flex-1">
                  <div className="font-medium mb-1">{t('importMode.move')}</div>
                  <div className="text-sm text-text-secondary">
                    {t('importMode.moveDesc')}
                  </div>
                </div>
              </div>
            </button>
          </div>
          
          <button
            onClick={onClose}
            className="w-full mt-4 px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all"
          >
            {t('importMode.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
