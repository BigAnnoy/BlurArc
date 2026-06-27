import { useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { FilterMenu } from './FilterMenu';
import { SortMenu } from './SortMenu';

/**
 * v0.7 §4.2 公共照片工具栏
 * TimelineView / MainContent 共用，统一布局切换/缩放/筛选/排序/选择行为。
 * 选择模式下隐藏工具按钮，仅显示标题 + 取消按钮（各视图自行渲染选择 banner）。
 */
interface PhotoToolbarProps {
  title: string;
  count: number;
  loading?: boolean;
  // §3.2.2 布局切换
  layoutMode: 'grid' | 'masonry';
  onLayoutModeChange: (mode: 'grid' | 'masonry') => void;
  // §4.2 缩放（0=小 120px, 1=中 180px, 2=大 240px）
  zoomLevel: number;
  onZoomChange: (level: number) => void;
  // §4.3 筛选
  filters: string[];
  onFiltersChange: (filters: string[]) => void;
  filterOptions: { key: string; label: string; icon: string }[];
  // §4.2.1 排序
  sort: string;
  onSortChange: (sort: string) => void;
  sortOptions: { key: string; label: string }[];
  // 选择模式
  selectionMode: boolean;
  onSelect: () => void;
  // 概览模式禁用（缩放/显示选项/选择仅 All Photos 生效）
  actionsDisabled?: boolean;
}

export function PhotoToolbar({
  title, count, loading,
  layoutMode, onLayoutModeChange,
  zoomLevel, onZoomChange,
  filters, onFiltersChange, filterOptions,
  sort, onSortChange, sortOptions,
  selectionMode, onSelect,
  actionsDisabled = false,
}: PhotoToolbarProps) {
  const { t } = useI18n();
  const [showFilter, setShowFilter] = useState(false);
  const [showSort, setShowSort] = useState(false);

  return (
    <div className="flex items-center justify-between px-5 py-2.5 bg-card border-b border-border min-h-[48px]">
      <div className="flex items-baseline gap-2 flex-1 min-w-0 h-[34px]">
        <span className="text-primary font-semibold text-[18px] leading-[34px]">{title}</span>
        {count > 0 && <span className="text-text-secondary font-mono text-[12px] leading-[34px]">{t('main.photoCount', { count })}</span>}
        {loading && <span className="text-text-tertiary ml-2">{t('main.loading')}</span>}
      </div>
      <div className="flex gap-1.5 items-center flex-shrink-0">
        {!selectionMode && (
          <>
            {/* §3.2.2 布局切换：网格 / 瀑布流 */}
            <button
              onClick={() => onLayoutModeChange(layoutMode === 'grid' ? 'masonry' : 'grid')}
              disabled={actionsDisabled}
              className={`w-[34px] h-[34px] rounded-[6px] border-none bg-transparent cursor-pointer flex items-center justify-center transition-all hover:bg-page hover:text-primary ${
                actionsDisabled ? 'text-text-tertiary cursor-not-allowed opacity-50' : 'text-text-secondary'
              } ${layoutMode === 'masonry' ? 'text-primary bg-primary-light' : ''}`}
              title={layoutMode === 'grid' ? t('main.layoutSwitch') + '（网格）' : t('main.layoutSwitch') + '（瀑布流）'}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
                <rect x="9" y="9" width="6" height="6" rx="1" fill="currentColor" stroke="none"/>
              </svg>
            </button>
            {/* §4.2 缩放 - */}
            <button
              onClick={() => onZoomChange(Math.max(0, zoomLevel - 1))}
              disabled={actionsDisabled || zoomLevel === 0}
              className={`w-[34px] h-[34px] rounded-[6px] border-none bg-transparent cursor-pointer flex items-center justify-center transition-all hover:bg-page hover:text-primary ${
                (actionsDisabled || zoomLevel === 0) ? 'text-text-tertiary cursor-not-allowed opacity-50' : 'text-text-secondary'
              }`}
              title={t('main.zoomOut')}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            {/* §4.2 缩放 + */}
            <button
              onClick={() => onZoomChange(Math.min(2, zoomLevel + 1))}
              disabled={actionsDisabled || zoomLevel === 2}
              className={`w-[34px] h-[34px] rounded-[6px] border-none bg-transparent cursor-pointer flex items-center justify-center transition-all hover:bg-page hover:text-primary ${
                (actionsDisabled || zoomLevel === 2) ? 'text-text-tertiary cursor-not-allowed opacity-50' : 'text-text-secondary'
              }`}
              title={t('main.zoomIn')}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            {/* §4.3 筛选（modal 弹窗，无需 relative 定位） */}
            <button
              onClick={() => { setShowFilter(!showFilter); setShowSort(false); }}
              className="w-[34px] h-[34px] rounded-[6px] border-none bg-transparent text-text-secondary cursor-pointer flex items-center justify-center transition-all hover:bg-page hover:text-primary"
              title={t('main.filter')}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
              </svg>
            </button>
            <FilterMenu
              isOpen={showFilter}
              options={filterOptions}
              selected={filters}
              onChange={onFiltersChange}
              onClose={() => setShowFilter(false)}
            />
            {/* §4.2.1 排序（modal 弹窗，无需 relative 定位） */}
            <button
              onClick={() => { setShowSort(!showSort); setShowFilter(false); }}
              className="w-[34px] h-[34px] rounded-[6px] border-none bg-transparent text-text-secondary cursor-pointer flex items-center justify-center transition-all hover:bg-page hover:text-primary"
              title={t('main.sort')}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="9" y2="18"/>
              </svg>
            </button>
            <SortMenu
              isOpen={showSort}
              onClose={() => setShowSort(false)}
              options={sortOptions}
              selected={sort}
              onChange={onSortChange}
            />
          </>
        )}
        {/* 选择按钮（非选择模式显示"选择"，选择模式显示"取消"） */}
        <button
          onClick={onSelect}
          disabled={actionsDisabled && !selectionMode}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 bg-card border border-border rounded-[8px] text-[13px] cursor-pointer transition-all ${
            actionsDisabled && !selectionMode
              ? 'text-text-tertiary cursor-not-allowed opacity-50'
              : 'text-text-primary hover:border-primary hover:text-primary'
          }`}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <polyline points="9 11 12 14 22 4"/>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
          </svg>
          {selectionMode ? t('common.cancelSelectMode') : t('main.selectMode')}
        </button>
      </div>
    </div>
  );
}
