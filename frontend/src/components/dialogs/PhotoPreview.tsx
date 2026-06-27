import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import { useI18n } from '../../contexts/I18nContext';
import type { Photo } from '../../types';

interface PhotoAlbum {
  id: number;
  name: string;
  description: string | null;
  cover_photo_id: number | null;
  cover_photo_path?: string | null;
  photo_count: number;
  created_at: string | null;
}

interface PhotoPreviewProps {
  isOpen: boolean;
  onClose: () => void;
  photo: Photo | null;
  photos?: Photo[];  // 可选：若不传则只显示当前 photo（不带 prev/next 导航）
  onNavigate?: (photo: Photo) => void;
  onSelectAlbum?: (albumId: number) => void;
  onPhotoUpdate?: (updated: Photo) => void;
}

export function PhotoPreview({ isOpen, onClose, photo, photos, onNavigate, onSelectAlbum, onPhotoUpdate }: PhotoPreviewProps) {
  const { t } = useI18n();
  const photosList = photos && photos.length > 0 ? photos : (photo ? [photo] : []);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showInfoPanel, setShowInfoPanel] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [photoAlbums, setPhotoAlbums] = useState<PhotoAlbum[]>([]);
  const [albumsLoading, setAlbumsLoading] = useState(false);
  const [isSlideshow, setIsSlideshow] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const thumbsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (photo && photosList.length > 0) {
      const idx = photosList.findIndex((p) => p.id === photo.id);
      setCurrentIndex(idx >= 0 ? idx : 0);
      setIsFavorite((photo as any).is_favorite || false);
    }
  }, [photo, photosList]);

  useEffect(() => {
    if (!photo) { setPhotoAlbums([]); return; }
    let cancelled = false;
    setAlbumsLoading(true);
    api.getPhotoAlbums(Number(photo.id))
      .then((res) => { if (!cancelled) setPhotoAlbums(res.albums || []); })
      .catch((err) => {
        if (!cancelled) { console.error('Failed to load photo albums:', err); setPhotoAlbums([]); }
      })
      .finally(() => { if (!cancelled) setAlbumsLoading(false); });
    return () => { cancelled = true; };
  }, [photo?.id]);

  // 幻灯片播放（F2）
  useEffect(() => {
    if (!isSlideshow || photosList.length === 0) return;
    const timer = setInterval(() => {
      const nextIndex = (currentIndex + 1) % photosList.length;
      const nextPhoto = photosList[nextIndex];
      setCurrentIndex(nextIndex);
      onNavigate?.(nextPhoto);
      setIsFavorite((nextPhoto as any).is_favorite || false);
    }, 3000);
    return () => clearInterval(timer);
  }, [isSlideshow, currentIndex, photosList, onNavigate]);

  // 视频播放 + 资源清理（F4/F5/D1）
  useEffect(() => {
    if (!photo) return;
    const video = videoRef.current;
    if (photo.type === 'video' && video) {
      // 切下一张时先释放旧 src
      if (video.src) {
        video.pause();
        video.removeAttribute('src');
        video.load();
      }
      // 设置新 src 并自动播放
      video.src = api.getFile(photo.path);
      video.load();
      video.play().catch(() => {});
    }
    // cleanup：离开预览页时暂停
    return () => {
      if (video) {
        video.pause();
        video.removeAttribute('src');
        video.load();
      }
    };
  }, [photo]);

  useEffect(() => {
    if (thumbsRef.current) {
      const activeThumb = thumbsRef.current.children[currentIndex] as HTMLElement;
      if (activeThumb) {
        activeThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    }
  }, [currentIndex]);

  const handlePrev = useCallback(() => {
    if (photosList.length <= 1) return;
    const prevIndex = (currentIndex - 1 + photosList.length) % photosList.length;
    const prevPhoto = photosList[prevIndex];
    setCurrentIndex(prevIndex);
    onNavigate?.(prevPhoto);
    setIsFavorite((prevPhoto as any).is_favorite || false);
  }, [currentIndex, photosList, onNavigate]);

  const handleNext = useCallback(() => {
    if (photosList.length <= 1) return;
    const nextIndex = (currentIndex + 1) % photosList.length;
    const nextPhoto = photosList[nextIndex];
    setCurrentIndex(nextIndex);
    onNavigate?.(nextPhoto);
    setIsFavorite((nextPhoto as any).is_favorite || false);
  }, [currentIndex, photosList, onNavigate]);

  const handleFavoriteToggle = useCallback(async () => {
    if (!photo) return;
    // 用 ref 模式避免闭包陷阱：基于当前状态取反
    let newState = false;
    setIsFavorite((prev) => { newState = !prev; return newState; });
    try {
      if (newState) {
        await api.addFavorite(Number(photo.id));
      } else {
        await api.removeFavorite(Number(photo.id));
      }
      // 通知父组件更新（用新的 is_favorite 值）
      const updated = { ...photo, is_favorite: newState };
      onPhotoUpdate?.(updated);
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      // 回滚状态
      setIsFavorite(!newState);
    }
  }, [photo, onPhotoUpdate]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isSlideshow) {
          setIsSlideshow(false);
          return;
        }
        onClose();
      }
      if (e.key === 'ArrowLeft') handlePrev();
      if (e.key === 'ArrowRight') handleNext();
      if (e.key === 'i' || e.key === 'I') setShowInfoPanel(!showInfoPanel);
      if (e.key === 'f' || e.key === 'F') handleFavoriteToggle();
      if (e.key === ' ') {
        e.preventDefault();
        if (photo?.type === 'video' && videoRef.current) {
          if (videoRef.current.paused) videoRef.current.play();
          else videoRef.current.pause();
        }
      }
    },
    [handlePrev, handleNext, onClose, showInfoPanel, photo, isSlideshow, handleFavoriteToggle]
  );

  useEffect(() => {
    if (isOpen) document.addEventListener('keydown', handleKeyDown);
    return () => { document.removeEventListener('keydown', handleKeyDown); };
  }, [isOpen, handleKeyDown]);

  const handleMouseMove = () => {
    if (photo?.type === 'video') {
      setShowControls(true);
      setTimeout(() => setShowControls(false), 2500);
    }
  };

  if (!photo || !isOpen) return null;

  const isVideo = photo.type === 'video';
  const dateStr = (() => {
    if (!photo.date) return t('preview.unknownDate');
    try {
      const d = new Date(photo.date);
      if (isNaN(d.getTime())) return photo.date;
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    } catch { return photo.date; }
  })();

  return (
    <div
      className="preview-shell fixed inset-0 z-50 bg-page grid"
      style={{
        gridTemplateRows: '56px 1fr 100px',
        gridTemplateColumns: showInfoPanel ? '1fr 340px' : '1fr 0',
        gridTemplateAreas: '"topbar topbar" "main panel" "thumbs thumbs"'
      }}
    >
      {/* 顶部工具栏（v2 原型一致） */}
      <div
        className="topbar flex items-center justify-between px-5 bg-card border-b border-border"
        style={{ gridArea: 'topbar', boxShadow: 'var(--shadow-sm)' }}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={onClose}
            className="back-btn w-[34px] h-[34px] inline-flex items-center justify-center rounded-md text-text-secondary hover:bg-page hover:text-text-primary transition-all duration-150"
            title={`${t('preview.back')} (Esc)`}
          >
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex flex-col min-w-0 leading-tight">
            <div className="text-sm font-semibold text-text-primary whitespace-nowrap overflow-hidden text-ellipsis max-w-[380px]">
              {photo.name}
            </div>
            <div className="text-xs text-text-secondary font-mono mt-0.5 flex items-center gap-1.5">
              <span className="text-primary font-semibold">{currentIndex + 1} / {photosList.length}</span>
              <span className="opacity-40">·</span>
              <span>{dateStr}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span
            className="inline-flex items-center gap-1 h-6 px-2.5 rounded-full text-xs font-medium"
            style={{
              background: isVideo ? 'var(--color-primary-light)' : 'var(--color-page)',
              color: isVideo ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            }}
          >
            {isVideo ? (
              <>
                <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                {t('preview.video')}
              </>
            ) : (
              <>
                <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9 3l-1.5 1.5H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-12a2 2 0 0 0-2-2h-3.5L15 3H9zm3 5a5 5 0 1 1 0 10 5 5 0 0 1 0-10z" />
                </svg>
                {t('preview.photo')}
              </>
            )}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={handleFavoriteToggle}
            className={`w-9 h-9 inline-flex items-center justify-center rounded-md transition-all duration-150 ${
              isFavorite ? 'text-[#f43f5e] bg-[rgba(244,63,94,0.08)]' : 'text-text-secondary hover:bg-page hover:text-text-primary'
            }`}
            title={`${t('preview.favorite')} (F)`}
          >
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill={isFavorite ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
          </button>
          <div className="w-px h-5 bg-border mx-1" />
          <button
            onClick={() => setShowInfoPanel(!showInfoPanel)}
            className={`w-9 h-9 inline-flex items-center justify-center rounded-md transition-all duration-150 ${
              showInfoPanel ? 'text-primary bg-primary-light' : 'text-text-secondary hover:bg-page hover:text-text-primary'
            }`}
            title={`${t('preview.infoPanel')} (i)`}
          >
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </button>
          <button
            onClick={() => setIsSlideshow(!isSlideshow)}
            className={`w-9 h-9 inline-flex items-center justify-center rounded-md transition-all duration-150 ${
              isSlideshow ? 'text-primary bg-primary-light' : 'text-text-secondary hover:bg-page hover:text-text-primary'
            }`}
            title={`${t('preview.slideShow')} (Esc 退出)`}
          >
            {isSlideshow ? (
              <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            ) : (
              <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            )}
          </button>
          <div className="w-px h-5 bg-border mx-1" />
          <button
            onClick={onClose}
            className="w-9 h-9 inline-flex items-center justify-center rounded-md text-text-secondary hover:bg-page hover:text-text-primary transition-all duration-150"
            title={`${t('common.close')} (Esc)`}
          >
            <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* 主图区 */}
      <div
        className="flex items-center justify-center relative p-6 bg-page min-w-0 min-h-0 overflow-hidden"
        style={{ gridArea: 'main' }}
        onMouseMove={handleMouseMove}
      >
        <button
          onClick={handlePrev}
          disabled={photosList.length <= 1}
          className="absolute left-0 top-1/2 -translate-y-1/2 w-11 h-11 bg-card border border-border rounded-full flex items-center justify-center text-text-secondary hover:text-primary hover:border-primary hover:scale-105 active:scale-95 transition-all duration-150 z-10 shadow-md disabled:opacity-30 disabled:cursor-not-allowed"
          title={`${t('preview.prev')} (←)`}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <button
          onClick={handleNext}
          disabled={photosList.length <= 1}
          className="absolute right-0 top-1/2 -translate-y-1/2 w-11 h-11 bg-card border border-border rounded-full flex items-center justify-center text-text-secondary hover:text-primary hover:border-primary hover:scale-105 active:scale-95 transition-all duration-150 z-10 shadow-md disabled:opacity-30 disabled:cursor-not-allowed"
          title={`${t('preview.next')} (→)`}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>

        {isVideo ? (
          <video
            ref={videoRef}
            src={api.getFile(photo.path)}
            controls={showControls}
            muted
            playsInline
            className="w-full max-w-[calc(100%-104px)] max-h-full rounded-md shadow-lg object-contain flex-shrink-0"
            style={{
              background: '#000',
            }}
            onEnded={handleNext}
          />
        ) : (
          <img
            src={api.getFile(photo.path)}
            alt={photo.name}
            className="w-full max-w-[calc(100%-104px)] max-h-full rounded-md shadow-lg object-contain flex-shrink-0"
            style={{
              background: 'var(--color-page)',
            }}
          />
        )}
      </div>

      {/* 右侧信息面板 */}
      {showInfoPanel && (
        <div className="info-panel bg-card border-l border-border overflow-y-auto" style={{ gridArea: 'panel' }}>
          <div className="px-[22px] py-5">
            {/* 标题和描述 */}
            <div className="panel-section space-y-2 pb-5 border-b border-border">
              <input
                type="text"
                defaultValue={photo.title || photo.name}
                onBlur={(e) => {
                  const newTitle = e.target.value;
                  if (newTitle !== (photo.title || photo.name)) {
                    api.updatePhotoTitle(Number(photo.id), newTitle).then(() => {
                      const updated = { ...photo, title: newTitle };
                      onPhotoUpdate?.(updated);
                    }).catch(() => {
                      // TODO: toast 错误提示
                    });
                  }
                }}
                className="w-full text-[22px] font-bold text-text-primary bg-transparent border-none outline-none focus:bg-page rounded px-1 -mx-1 transition-colors"
                placeholder={t('preview.addTitle')}
              />
              <textarea
                defaultValue={photo.description || ''}
                onBlur={(e) => {
                  const newDesc = e.target.value;
                  if (newDesc !== (photo.description || '')) {
                    api.updatePhotoDescription(Number(photo.id), newDesc).then(() => {
                      const updated = { ...photo, description: newDesc };
                      onPhotoUpdate?.(updated);
                    }).catch(() => {
                      // TODO: toast 错误提示
                    });
                  }
                }}
                className="w-full min-h-[48px] text-sm text-text-primary bg-transparent border-none outline-none focus:bg-page rounded px-1 -mx-1 resize-none transition-colors leading-[1.65]"
                placeholder={t('preview.addDesc')}
              />
            </div>

            {/* 拍摄信息 */}
            <div className="panel-section py-5 border-b border-border">
              <div className="text-[11px] font-medium text-text-tertiary uppercase tracking-[0.6px] mb-2">拍摄信息</div>
              <div className="flex items-center gap-2 text-sm text-text-secondary mb-2.5">
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <span>{dateStr}</span>
              </div>
              <div className="flex flex-wrap gap-[5px]">
                <span className="inline-flex items-center h-6 px-[9px] bg-page border border-border rounded-[12px] text-[12px] font-mono text-text-secondary">
                  3 : 2
                </span>
                <span className="inline-flex items-center h-6 px-[9px] bg-page border border-border rounded-[12px] text-[12px] font-mono text-text-secondary">
                  {(photo as any).width || '4032'} × {(photo as any).height || '3024'}
                </span>
                <span className="inline-flex items-center h-6 px-[9px] bg-page border border-border rounded-[12px] text-[12px] font-mono text-text-secondary">
                  {(photo.size / 1024 / 1024).toFixed(1)} MB
                </span>
                {isVideo && (
                  <span className="inline-flex items-center h-6 px-[9px] bg-primary-light border border-primary rounded-[12px] text-[12px] font-mono text-primary">
                    {(photo as any).duration || '0:00'}
                  </span>
                )}
              </div>
            </div>

            {/* 相册 */}
            <div className="panel-section pt-5">
              <div className="text-[11px] font-medium text-text-tertiary uppercase tracking-[0.6px] mb-2">
                {t('preview.albums')}
              </div>
              {albumsLoading ? (
                <div className="flex items-center gap-2 text-xs text-text-tertiary py-3">
                  <div className="animate-spin w-3 h-3 border-2 border-border border-t-primary rounded-full" />
                  <span>{t('common.loading')}</span>
                </div>
              ) : photoAlbums.length === 0 ? (
                <div className="text-sm text-text-tertiary py-3">{t('preview.noAlbums')}</div>
              ) : (
                <div className="space-y-1.5">
                  {photoAlbums.map((album) => (
                    <button
                      key={album.id}
                      onClick={() => { onSelectAlbum?.(album.id); onClose(); }}
                      className="w-full flex items-center gap-3 p-2 rounded-md bg-page hover:bg-page/80 transition-colors text-left"
                    >
                      {album.cover_photo_path ? (
                        <img
                          src={api.getThumbnail(album.cover_photo_path)}
                          alt={album.name}
                          className="w-12 h-12 rounded-[4px] flex-shrink-0 object-cover"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-[4px] flex-shrink-0 overflow-hidden">
                          <div className="thumb-default">📷</div>
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-text-primary truncate">{album.name}</div>
                        <div className="text-[11px] font-mono text-text-tertiary">{album.photo_count} {t('preview.photoCount')}</div>
                      </div>
                      <svg className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 18l6-6-6-6" />
                      </svg>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 底部缩略图条 */}
      <div
        className="thumbs-bar bg-card border-t border-border flex items-center px-5 overflow-x-auto"
        style={{ gridArea: 'thumbs' }}
        ref={thumbsRef}
      >
        <div className="flex gap-1.5">
          {photosList.map((p, idx) => (
            <button
              key={p.id}
              onClick={() => {
                setCurrentIndex(idx);
                onNavigate?.(p);
                setIsFavorite((p as any).is_favorite || false);
              }}
              className={`relative w-20 h-20 rounded-[6px] overflow-hidden flex-shrink-0 transition-all duration-150 hover:-translate-y-0.5 ${
                idx === currentIndex
                  ? 'border-2 border-primary scale-105'
                  : 'opacity-70 hover:opacity-100'
              }`}
              style={idx === currentIndex ? {
                boxShadow: '0 0 0 3px rgba(8,145,178,0.08)',
              } : undefined}
            >
              {p.type === 'video' ? (
                <>
                  <div className="w-full h-full" style={{ background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)' }} />
                  <div className="absolute top-1.5 right-1.5 w-[18px] h-[18px] bg-black/70 rounded-full flex items-center justify-center">
                    <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                  </div>
                  <div className="absolute bottom-1 left-1 text-[10px] text-white bg-black/65 px-[5px] rounded-[3px] font-mono">
                    {(p as any).duration || '0:00'}
                  </div>
                </>
              ) : (
                <img
                  src={api.getThumbnail(p.path)}
                  alt={p.name}
                  className="w-full h-full object-cover"
                  style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)' }}
                />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
