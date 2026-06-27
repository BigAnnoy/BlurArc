import { useI18n } from '../../contexts/I18nContext';

interface StatsCardProps {
  total: number;
  videos: number;
  size: string;
}

export function StatsCard({ total, size }: StatsCardProps) {
  const { t } = useI18n();

  return (
    <div className="bg-primary-light rounded-lg p-4 mb-5 border border-border">
      <div className="flex justify-between items-center">
        <span className="text-xs text-text-secondary">{t('sidebar.totalFiles')}</span>
        <span className="font-mono text-base font-semibold text-primary/90">{total.toLocaleString()}</span>
      </div>
      <div className="flex justify-between items-center mt-2">
        <span className="text-xs text-text-secondary">{t('sidebar.totalSize')}</span>
        <span className="font-mono text-base font-semibold text-primary/90">{size}</span>
      </div>
    </div>
  );
}
