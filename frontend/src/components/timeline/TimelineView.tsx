import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../services/api';
import { PhotoGrid } from '../photos/PhotoGrid';
import { PhotoToolbar } from '../common/PhotoToolbar';
import { SelectionBanner } from '../common/SelectionBanner';
import { AlbumCoverDefault } from '../common/AlbumCoverDefault';
import { useI18n } from '../../contexts/I18nContext';
import type { Photo } from '../../types';

// D1: 去掉 'days'，仅保留 all / months / years
type TimelineViewType = 'all' | 'months' | 'years';

interface TimelineState {
  view: TimelineViewType;
  year?: number;
  month?: number;
}

interface TimelineViewProps {
  onPhotoClick: (photo: Photo) => void;
  selectionMode: boolean;
  selectedIds: Set<string>;
  onSelect?: () => void;
  onSelectAll?: () => void;
  onDeleteSelected?: () => void;
  onJoinAlbum?: (photoId: string) => void;
  onJoinAlbums?: (photoIds: string[]) => void;
  onDelete?: (photoId: string) => void;
  onRemoveFromAlbum?: () => void;
  onFavoriteChange?: (photoId: string, isFavorite: boolean) => void;
  onPhotosChange?: (photos: Photo[]) => void;
}

// D6: 概览图分批加载每批数量
const PAGE_SIZE = 30;

export function TimelineView({ onPhotoClick, selectionMode, selectedIds, onSelect, onSelectAll, onDeleteSelected, onJoinAlbum, onJoinAlbums, onDelete, onRemoveFromAlbum, onFavoriteChange, onPhotosChange }: TimelineViewProps) {
  const { t } = useI18n();
  const [state, setState] = useState<TimelineState>({ view: 'all' });
  const [years, setYears] = useState<any[]>([]);
  const [months, setMonths] = useState<any[]>([]);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<string[]>([]);
  const [sort, setSort] = useState('media_date_desc');
  // v0.7 §3.2.2：布局切换（网格 / 瀑布流），仅 All Photos 视图生效
  const [layoutMode, setLayoutMode] = useState<'grid' | 'masonry'>('grid');
  // v0.7 §4.2：缩放级别（0=小, 1=中默认, 2=大），仅 All Photos 视图生效
  const [zoomLevel, setZoomLevel] = useState(1);

  // D6: 概览图分批加载状态（years）
  const [yearsCursor, setYearsCursor] = useState<number | null>(null);
  const [yearsHasMore, setYearsHasMore] = useState(false);
  const [yearsLoadingMore, setYearsLoadingMore] = useState(false);
  // D6: 概览图分批加载状态（months）
  const [monthsCursor, setMonthsCursor] = useState<string | null>(null);
  const [monthsHasMore, setMonthsHasMore] = useState(false);
  const [monthsLoadingMore, setMonthsLoadingMore] = useState(false);
  // 无限滚动状态（all photos）
  const [photosPage, setPhotosPage] = useState(1);
  const [photosHasMore, setPhotosHasMore] = useState(false);
  const [photosLoadingMore, setPhotosLoadingMore] = useState(false);

  // D6: sentinel 节点引用（参考 PhotoGrid 的 IntersectionObserver 实现）
  const yearsSentinelRef = useRef<HTMLDivElement>(null);
  const monthsSentinelRef = useRef<HTMLDivElement>(null);
  const photosSentinelRef = useRef<HTMLDivElement>(null);

  // D2: 判断是否为概览模式（年/月，§4.8 选择按钮在概览视图禁用），去掉 'days'
  const isOverviewMode = state.view === 'years' || state.view === 'months';

  const filterOptions = [
    { key: 'photo', label: t('filter.photoOnly'), icon: '📷' },
    { key: 'video', label: t('filter.videoOnly'), icon: '🎥' },
    { key: 'favorite', label: t('filter.favoriteOnly'), icon: '⭐' },
    { key: 'not_in_album', label: t('filter.notInAlbum'), icon: '📁' }
  ];

  const sortOptions = [
    { key: 'media_date_desc', label: t('sort.dateDesc') },
    { key: 'media_date_asc', label: t('sort.dateAsc') }
  ];

  // 按日期分组照片
  const groupPhotosByDay = (photos: Photo[], sort: string) => {
    const groups: { [key: string]: Photo[] } = {};
    photos.forEach(photo => {
      // v0.7.1: 后端 date 是 ISO 格式 "2026-06-23T17:56:58"，用 'T' 切取日期部分
      const date = (photo.date || '').split('T')[0] || (photo.date || '').split(' ')[0];
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(photo);
    });
    const groupOrder = sort === 'media_date_asc'
      ? (a: [string, Photo[]], b: [string, Photo[]]) => a[0].localeCompare(b[0])   // 升序：旧→新
      : (a: [string, Photo[]], b: [string, Photo[]]) => b[0].localeCompare(a[0]);  // 降序：新→旧
    return Object.entries(groups).sort(groupOrder);
  };

  // 加载首页数据（D6: years/months 取首批，all 取全部）
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (state.view === 'years') {
          const res = await api.getTimelineYears(PAGE_SIZE);
          setYears(res.years);
          setYearsCursor(res.next_cursor);
          setYearsHasMore(res.has_next);
        } else if (state.view === 'months') {
          const res = await api.getTimelineMonths(state.year, PAGE_SIZE);
          setMonths(res.months);
          setMonthsCursor(res.next_cursor);
          setMonthsHasMore(res.has_next);
        } else {
          // all photos（§4.2.1/§4.3：排序与筛选仅 All Photos 视图生效）
          const res = await api.getTimelinePhotos({
            year: state.year,
            month: state.month,
            page: 1,
            sort,
            filters,
          });
          const mapped = res.photos.map(p => ({
            id: String(p.id),
            name: p.filename,
            path: p.path,
            size: p.size,
            date: p.date || '',
            type: p.type as 'photo' | 'video',
            is_favorite: p.is_favorite || false,
          }));
          setPhotos(mapped);
          setPhotosPage(1);
          setPhotosHasMore(res.page < res.total_pages);
          // v0.7.1: 同步给 App 用于 PhotoPreview 上下张导航
          onPhotosChange?.(mapped);
        }
      } catch (error) {
        console.error(t('timeline.loadFailed'), error);
      }
      setLoading(false);
    };
    load();
  }, [state, sort, filters]);

  // D6: 加载更多 years（追加，不重置）
  const loadMoreYears = useCallback(async () => {
    if (!yearsHasMore || yearsLoadingMore || yearsCursor === null) return;
    setYearsLoadingMore(true);
    try {
      const res = await api.getTimelineYears(PAGE_SIZE, yearsCursor);
      setYears(prev => [...prev, ...res.years]);
      setYearsCursor(res.next_cursor);
      setYearsHasMore(res.has_next);
    } catch (error) {
      console.error(t('timeline.loadFailed'), error);
    }
    setYearsLoadingMore(false);
  }, [yearsHasMore, yearsLoadingMore, yearsCursor, t]);

  // D6: 加载更多 months（追加，不重置）
  const loadMoreMonths = useCallback(async () => {
    if (!monthsHasMore || monthsLoadingMore || monthsCursor === null) return;
    setMonthsLoadingMore(true);
    try {
      const res = await api.getTimelineMonths(state.year, PAGE_SIZE, monthsCursor);
      setMonths(prev => [...prev, ...res.months]);
      setMonthsCursor(res.next_cursor);
      setMonthsHasMore(res.has_next);
    } catch (error) {
      console.error(t('timeline.loadFailed'), error);
    }
    setMonthsLoadingMore(false);
  }, [monthsHasMore, monthsLoadingMore, monthsCursor, state.year, t]);

  // D6: years 滚动到底部触发加载
  useEffect(() => {
    if (state.view !== 'years') return;
    const node = yearsSentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) loadMoreYears();
      },
      { rootMargin: '200px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [state.view, loadMoreYears]);

  // D6: months 滚动到底部触发加载
  useEffect(() => {
    if (state.view !== 'months') return;
    const node = monthsSentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) loadMoreMonths();
      },
      { rootMargin: '200px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [state.view, loadMoreMonths]);

  // 无限滚动：加载更多照片（追加，不重置）
  const loadMorePhotos = useCallback(async () => {
    if (!photosHasMore || photosLoadingMore) return;
    setPhotosLoadingMore(true);
    try {
      const nextPage = photosPage + 1;
      const res = await api.getTimelinePhotos({
        year: state.year,
        month: state.month,
        page: nextPage,
        sort,
        filters,
      });
      const mapped = res.photos.map(p => ({
        id: String(p.id),
        name: p.filename,
        path: p.path,
        size: p.size,
        date: p.date || '',
        type: p.type as 'photo' | 'video',
        is_favorite: p.is_favorite || false,
      }));
      setPhotos(prev => [...prev, ...mapped]);
      setPhotosPage(nextPage);
      setPhotosHasMore(nextPage < res.total_pages);
      // v0.7.1: 同步给 App 用于 PhotoPreview 上下张导航
      onPhotosChange?.([...photos, ...mapped]);
    } catch (error) {
      console.error(t('timeline.loadFailed'), error);
    }
    setPhotosLoadingMore(false);
  }, [photosHasMore, photosLoadingMore, photosPage, state.year, state.month, sort, filters, t, photos, onPhotosChange]);

  // 无限滚动：all photos 滚动到底部触发加载
  useEffect(() => {
    if (state.view !== 'all') return;
    const node = photosSentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) loadMorePhotos();
      },
      { rootMargin: '200px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [state.view, loadMorePhotos]);

  // D5: 标题规则
  const title = state.view === 'all'
    ? (state.year && state.month
        ? t('timeline.yearMonthLabel', { year: state.year, month: state.month })
        : state.year
          ? t('timeline.yearLabel', { year: state.year })
          : t('sidebar.timeline'))
    : state.view === 'years'
      ? t('timeline.yearsTitle')
      : t('timeline.monthsTitle');

  // D5: 返回按钮仅 All Photos 带 filter 时显示
  const showBack = state.view === 'all' && (state.year !== undefined || state.month !== undefined);
  const handleBack = () => {
    // D21: 选择模式下切到概览图自动退出选择模式
    if (selectionMode) onSelect?.();
    if (state.month) {
      // D16: 带 year+month → 回 Months 概览（保留 year）
      setState({ view: 'months', year: state.year });
    } else if (state.year) {
      // D17: 仅带 year → 回 Years 概览
      setState({ view: 'years' });
    }
  };

  // D18: 切 tab 清空 filter；D21: 选择模式下切到概览图退出选择模式
  const handleTabClick = (v: TimelineViewType) => {
    if (selectionMode && (v === 'years' || v === 'months')) {
      onSelect?.();
    }
    setState({ view: v });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-page">
      {/* D5: 返回按钮（仅 All Photos 带 filter 时显示） */}
      {showBack && (
        <div className="flex items-center px-5 py-1.5 bg-card border-b border-border">
          <button
            onClick={handleBack}
            className="flex items-center gap-1 text-text-secondary hover:text-primary text-[13px] cursor-pointer bg-transparent border-none transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            {t('preview.back')}
          </button>
        </div>
      )}
      {/* 公共工具栏（v0.7 §4.2：与 MainContent 共用 PhotoToolbar） */}
      <PhotoToolbar
        title={title}
        count={photos.length}
        loading={loading}
        layoutMode={layoutMode}
        onLayoutModeChange={setLayoutMode}
        zoomLevel={zoomLevel}
        onZoomChange={setZoomLevel}
        filters={filters}
        onFiltersChange={setFilters}
        filterOptions={filterOptions}
        sort={sort}
        onSortChange={setSort}
        sortOptions={sortOptions}
        selectionMode={selectionMode}
        onSelect={onSelect || (() => {})}
        actionsDisabled={isOverviewMode}
      />
      {/* 选择模式 banner（v0.7 §2.7：与 MainContent 共用 SelectionBanner） */}
      {selectionMode && !isOverviewMode && (
        <SelectionBanner
          selectedCount={selectedIds.size}
          totalCount={photos.length}
          selectedIds={selectedIds}
          onSelectAll={onSelectAll || (() => {})}
          onDelete={onDeleteSelected || (() => {})}
          onJoinAlbums={onJoinAlbums}
          onRemoveFromAlbum={onRemoveFromAlbum}
          onCancel={onSelect || (() => {})}
        />
      )}
      {/* View Tabs（TimelineView 独有，D2: 去掉 Days） */}
      <div className="flex items-center gap-0.5 px-3 bg-card border-b border-border">
        {(['all', 'months', 'years'] as TimelineViewType[]).map(v => (
          <button
            key={v}
            onClick={() => handleTabClick(v)}
            className={`px-3.5 py-2 text-[13px] cursor-pointer bg-transparent border-none border-b-2 transition-all ${
              state.view === v
                ? 'text-primary font-semibold border-b-primary'
                : 'text-text-secondary font-medium border-b-transparent hover:text-text-primary hover:border-b-border'
            }`}
          >
            {v === 'all' ? t('timeline.allPhotos') : v === 'months' ? t('timeline.month') : t('timeline.year')}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-5">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin w-8 h-8 border-3 border-border border-t-primary rounded-full" />
          </div>
        ) : state.view === 'years' ? (
          <>
            <div
              className="grid gap-2 p-3"
              style={{
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gridAutoRows: '220px',
                alignContent: 'start',
              }}
            >
              {years.map(y => {
                const covers = y.cover_photo_paths && y.cover_photo_paths.length > 0
                  ? y.cover_photo_paths
                  : (y.cover_photo_path ? [y.cover_photo_path] : []);
                return (
                  <div
                    key={y.year}
                    className="relative rounded-md overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
                    // D3: 双击直接进 All Photos（带 year filter）
                    onDoubleClick={() => setState({ view: 'all', year: y.year })}
                  >
                    {covers.length >= 4 ? (
                      <div className="w-full h-full grid grid-cols-2 grid-rows-2 gap-0.5">
                        {covers.slice(0, 4).map((p: string, i: number) => (
                          <img key={i} src={api.getThumbnail(p)} alt="" className="w-full h-full object-cover" loading="lazy" />
                        ))}
                      </div>
                    ) : covers.length > 0 ? (
                      <img src={api.getThumbnail(covers[0])} alt="" className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                      <AlbumCoverDefault size="tile" />
                    )}
                    <div className="absolute bottom-0 left-0 right-0 px-3 py-2.5 bg-gradient-to-t from-black/65 to-transparent text-white">
                      <div className="text-sm font-medium truncate">{t('timeline.yearLabel', { year: y.year })}</div>
                      <div className="text-[11px] font-mono opacity-85 mt-0.5">{t('main.photoCount', { count: y.count })}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            {/* D6: 分批加载 sentinel + loading 指示 */}
            {yearsHasMore && (
              <div ref={yearsSentinelRef} className="flex items-center justify-center py-6">
                {yearsLoadingMore && <div className="animate-spin w-6 h-6 border-2 border-border border-t-primary rounded-full" />}
              </div>
            )}
          </>
        ) : state.view === 'months' ? (
          <>
            <div
              className="grid gap-2 p-3"
              style={{
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gridAutoRows: '220px',
                alignContent: 'start',
              }}
            >
              {months.map(m => {
                const covers = m.cover_photo_paths && m.cover_photo_paths.length > 0
                  ? m.cover_photo_paths
                  : (m.cover_photo_path ? [m.cover_photo_path] : []);
                return (
                  <div
                    key={`${m.year}-${m.month}`}
                    className="relative rounded-md overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
                    // D3: 双击直接进 All Photos（带 year+month filter）
                    onDoubleClick={() => setState({ view: 'all', year: m.year, month: m.month })}
                  >
                    {covers.length >= 4 ? (
                      <div className="w-full h-full grid grid-cols-2 grid-rows-2 gap-0.5">
                        {covers.slice(0, 4).map((p: string, i: number) => (
                          <img key={i} src={api.getThumbnail(p)} alt="" className="w-full h-full object-cover" loading="lazy" />
                        ))}
                      </div>
                    ) : covers.length > 0 ? (
                      <img src={api.getThumbnail(covers[0])} alt="" className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                      <AlbumCoverDefault size="tile" />
                    )}
                    <div className="absolute bottom-0 left-0 right-0 px-3 py-2.5 bg-gradient-to-t from-black/65 to-transparent text-white">
                      <div className="text-sm font-medium truncate">{t('timeline.yearMonthLabel', { year: m.year, month: m.month })}</div>
                      <div className="text-[11px] font-mono opacity-85 mt-0.5">{t('main.photoCount', { count: m.count })}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            {/* D6: 分批加载 sentinel + loading 指示 */}
            {monthsHasMore && (
              <div ref={monthsSentinelRef} className="flex items-center justify-center py-6">
                {monthsLoadingMore && <div className="animate-spin w-6 h-6 border-2 border-border border-t-primary rounded-full" />}
              </div>
            )}
          </>
        ) : (
          // D7: All Photos（无论是否带 filter）按天分组显示照片
          <div className="space-y-6">
            {groupPhotosByDay(photos, sort).map(([date, dayPhotos]) => (
              <div key={date}>
                <h3 className="text-sm font-semibold text-text-primary mb-3 px-1">
                  {new Date(date).toLocaleDateString(t('common.locale') === 'English' ? 'en-US' : 'zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}
                  <span className="text-text-tertiary font-normal ml-2">({t('main.photoCount', { count: dayPhotos.length })})</span>
                </h3>
                <PhotoGrid
                  photos={dayPhotos}
                  selectionMode={selectionMode}
                  selectedIds={selectedIds}
                  onPhotoClick={onPhotoClick}
                  onJoinAlbum={onJoinAlbum}
                  onDelete={onDelete}
                  onRemoveFromAlbum={onRemoveFromAlbum}
                  onFavoriteChange={onFavoriteChange}
                  layoutMode={layoutMode}
                  zoomLevel={zoomLevel}
                />
              </div>
            ))}
            {/* 无限滚动 sentinel + loading 指示 */}
            {photosHasMore && (
              <div ref={photosSentinelRef} className="flex items-center justify-center py-6">
                {photosLoadingMore && <div className="animate-spin w-6 h-6 border-2 border-border border-t-primary rounded-full" />}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
