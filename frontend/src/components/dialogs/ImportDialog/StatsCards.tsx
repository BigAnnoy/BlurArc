import { useI18n } from '../../../contexts/I18nContext';

interface StatsCardsProps {
  mediaCount: number;
  totalSizeMB: number;
}

export function StatsCards({ mediaCount, totalSizeMB }: StatsCardsProps) {
  const { t } = useI18n();

  // 格式化文件大小
  const formatSize = (mb: number): string => {
    if (mb < 1024) {
      return `${mb.toFixed(1)} MB`;
    } else if (mb < 1024 * 1024) {
      return `${(mb / 1024).toFixed(2)} GB`;
    } else {
      return `${(mb / 1024 / 1024).toFixed(2)} TB`;
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center px-3 py-2 bg-card rounded-lg border border-border">
        <span className="text-sm text-text-secondary">{t('preview.totalFiles')}</span>
        <span className="font-mono text-base font-semibold text-primary">{mediaCount.toLocaleString()}</span>
      </div>
      <div className="flex justify-between items-center px-3 py-2 bg-card rounded-lg border border-border">
        <span className="text-sm text-text-secondary">{t('preview.totalSize')}</span>
        <span className="font-mono text-base font-semibold text-primary">{formatSize(totalSizeMB)}</span>
      </div>
    </div>
  );
}
