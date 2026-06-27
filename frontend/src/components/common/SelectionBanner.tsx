import { useI18n } from '../../contexts/I18nContext';

/**
 * v0.7 §2.7 公共选择模式 banner
 * TimelineView / MainContent 共用，选择模式下显示已选数量 + 批量操作按钮。
 * onJoinAlbums / onRemoveFromAlbum 可选，有则显示对应按钮。
 */
interface SelectionBannerProps {
  selectedCount: number;
  totalCount: number;
  selectedIds: Set<string>;
  onSelectAll: () => void;
  onDelete: () => void;
  onJoinAlbums?: (ids: string[]) => void;
  onRemoveFromAlbum?: () => void;
  onCancel: () => void;
}

export function SelectionBanner({
  selectedCount, totalCount, selectedIds,
  onSelectAll, onDelete, onJoinAlbums, onRemoveFromAlbum, onCancel,
}: SelectionBannerProps) {
  const { t } = useI18n();
  const allSelected = selectedCount === totalCount && totalCount > 0;
  const noneSelected = selectedCount === 0;

  return (
    <div className="flex items-center justify-between px-5 py-2 bg-primary-light border-b border-primary/30">
      <div className="flex items-center gap-3">
        <span className="text-[13px] font-medium text-primary">
          {t('main.selected', { count: selectedCount })}
        </span>
        {selectedCount > 0 && selectedCount < totalCount && (
          <span className="text-[11px] text-text-tertiary">
            {t('main.totalCount', { count: totalCount })}
          </span>
        )}
      </div>
      <div className="flex gap-1.5 items-center">
        {/* 全选 / 取消全选 */}
        <button
          onClick={onSelectAll}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-card border border-border rounded-lg text-[13px] text-text-primary cursor-pointer hover:border-primary hover:text-primary transition-all"
        >
          {allSelected ? t('common.cancelSelect') : t('common.selectAll')}
        </button>
        {/* 从相册移除（仅相册视图） */}
        {onRemoveFromAlbum && (
          <button
            onClick={onRemoveFromAlbum}
            disabled={noneSelected}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] transition-all ${
              !noneSelected
                ? 'bg-orange-500 text-white cursor-pointer hover:bg-orange-600'
                : 'bg-card text-text-tertiary cursor-not-allowed border border-border'
            }`}
          >
            {t('main.removeFromAlbum')}
          </button>
        )}
        {/* 加入相册 */}
        {onJoinAlbums && (
          <button
            onClick={() => onJoinAlbums(Array.from(selectedIds))}
            disabled={noneSelected}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] transition-all ${
              !noneSelected
                ? 'bg-primary text-white cursor-pointer hover:bg-primary-hover'
                : 'bg-card text-text-tertiary cursor-not-allowed border border-border'
            }`}
            title={t('main.joinAlbum')}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            {t('main.joinAlbum')}
          </button>
        )}
        {/* 删除 */}
        <button
          onClick={onDelete}
          disabled={noneSelected}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] transition-all ${
            !noneSelected
              ? 'bg-red-500 text-white cursor-pointer hover:bg-red-600'
              : 'bg-card text-text-tertiary cursor-not-allowed border border-border'
          }`}
        >
          {t('main.deleteSelected')}
        </button>
        {/* 取消选择模式 */}
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-card border border-border rounded-lg text-[13px] text-text-primary cursor-pointer hover:border-primary hover:text-primary transition-all"
        >
          {t('common.cancelSelectMode')}
        </button>
      </div>
    </div>
  );
}
