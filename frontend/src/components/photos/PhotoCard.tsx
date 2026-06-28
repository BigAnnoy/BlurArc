import { useState, useEffect } from 'react';
import type { Photo } from '../../types';
import { api } from '../../services/api';
import { ContextMenu } from '../common/ContextMenu';
import { buildPhotoMenu } from '../common/menuBuilders';
import { useI18n } from '../../contexts/I18nContext';

interface PhotoCardProps {
  photo: Photo;
  selected?: boolean;
  selectionMode?: boolean;
  onClick: () => void;
  onFavoriteChange?: (photoId: string, isFavorite: boolean) => void;
  onJoinAlbum?: (photoId: string) => void;
  onDelete?: (photoId: string) => void;
  onRemoveFromAlbum?: () => void;
  albumId?: number | null;
  layoutMode?: 'grid' | 'masonry';
  draggable?: boolean;
  onDragStart?: () => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDrop?: (e: React.DragEvent) => void;
  isDragged?: boolean;
  isDragOver?: boolean;
}

export function PhotoCard({ photo, selected, selectionMode, onClick, onFavoriteChange, onJoinAlbum, onDelete, onRemoveFromAlbum, albumId, layoutMode = 'grid', draggable: draggableProp, onDragStart, onDragOver, onDrop, isDragged, isDragOver }: PhotoCardProps) {
  const { t } = useI18n();
  const thumbnailUrl = api.getThumbnail(photo.path);
  const [isFav, setIsFav] = useState(photo.is_favorite || false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [loadError, setLoadError] = useState(false);

  // photo.path 变化时重置加载失败状态
  useEffect(() => {
    setLoadError(false);
  }, [photo.path]);

  // 同步 photo.is_favorite 变化（外部更新时保持一致）
  useEffect(() => {
    setIsFav(photo.is_favorite || false);
  }, [photo.is_favorite]);

  const handleFavoriteClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (isFav) {
        await api.removeFavorite(Number(photo.id));
        setIsFav(false);
        onFavoriteChange?.(photo.id, false);
      } else {
        await api.addFavorite(Number(photo.id));
        setIsFav(true);
        onFavoriteChange?.(photo.id, true);
      }
    } catch (error) {
      console.error('收藏操作失败:', error);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  return (
    <>
      <div
        draggable={draggableProp !== false}
        onDragStart={(e) => {
          e.dataTransfer.setData('photo/id', photo.id);
          e.dataTransfer.effectAllowed = 'copy';
          onDragStart?.();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          onDragOver?.(e);
        }}
        onDrop={(e) => {
          e.preventDefault();
          onDrop?.(e);
        }}
        className={`relative group bg-card rounded-[6px] cursor-pointer overflow-hidden transition-all duration-200 ${
          selected
            ? 'outline-2 outline-primary outline-offset-[-2px] shadow-[0_4px_12px_rgba(0,0,0,0.15)]'
            : isDragOver
            ? 'outline-2 outline-primary outline-offset-[-2px]'
            : isDragged
            ? 'opacity-50'
            : 'hover:shadow-[0_0_0_2px_var(--color-primary),0_4px_12px_rgba(0,0,0,0.1)] hover:-translate-y-0.5'
        }`}
        onClick={onClick}
        onContextMenu={handleContextMenu}
      >
      {loadError ? (
        <div
          className={`w-full flex flex-col items-center justify-center bg-page text-tertiary transition-transform duration-300 ${
            layoutMode === 'grid'
              ? 'aspect-square'
              : 'h-auto min-h-[160px]'
          } ${selectionMode ? '' : 'hover:scale-105'}`}
        >
          <svg
            className="w-10 h-10 mb-2"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <polyline points="3 15 8 11 12 14 16 10 21 14" />
            <line x1="6" y1="7" x2="18" y2="17" />
          </svg>
          <span className="text-xs">无法加载</span>
        </div>
      ) : (
        <img
          src={thumbnailUrl}
          alt={photo.name}
          className={`w-full ${layoutMode === 'grid' ? 'aspect-square object-cover' : 'h-auto object-cover'} transition-transform duration-300 ${selectionMode ? '' : 'hover:scale-105'}`}
          loading="lazy"
          onError={() => setLoadError(true)}
        />
      )}
      
      {/* 收藏按钮（v0.7 §8.2 对齐原型：收藏后红色圆背景 + 白色心形，未收藏半透明黑底 + 白色描边心形） */}
      <button
        onClick={handleFavoriteClick}
        title={isFav ? '取消收藏' : '加入收藏'}
        className={`photo-heart absolute top-1.5 right-1.5 w-6 h-6 rounded-full flex items-center justify-center transition-all duration-150 z-[2] ${
          isFav
            ? 'opacity-100 bg-favorite hover:bg-red-600'
            : 'opacity-0 group-hover:opacity-100 bg-black/40 hover:bg-black/60'
        }`}
      >
        <svg
          className="w-3.5 h-3.5 text-white"
          viewBox="0 0 24 24"
          fill={isFav ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
        </svg>
      </button>

      {selected && (
        <div className="absolute top-2 left-2 w-[22px] h-[22px] bg-primary rounded-full flex items-center justify-center shadow-md">
          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )}
      {photo.type === 'video' && (
        <div className="absolute bottom-1.5 right-1.5 bg-black/65 text-white text-[11px] px-1.5 py-0.5 rounded font-medium">
          ▶ {photo.duration}
        </div>
      )}
      <div className="absolute bottom-0 left-0 right-0 pt-5 pb-2 px-2 bg-gradient-to-t from-black/65 to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100">
        <div className="text-[11px] text-white font-medium truncate">{photo.name}</div>
        <div className="font-mono text-[10px] text-white/75 mt-0.5">{photo.date}</div>
      </div>
      </div>

      {contextMenu && (
        <ContextMenu
          isOpen={true}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          groups={buildPhotoMenu({
            isFavorite: isFav,
            inAlbumId: albumId,
            onPreview: () => onClick(),
            onToggleFavorite: () => {
              handleFavoriteClick({ stopPropagation: () => {} } as React.MouseEvent);
            },
            onJoinAlbum: () => onJoinAlbum?.(photo.id),
            onRemoveFromAlbum: onRemoveFromAlbum,
            onOpenInExplorer: async () => {
              try {
                await api.openInExplorer(photo.path);
              } catch (error) {
                console.error('打开资源管理器失败:', error);
              }
            },
            onDelete: () => onDelete?.(photo.id),
            t,
          })}
        />
      )}
    </>
  );
}
