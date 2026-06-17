import type { Photo } from '../../types';
import { api } from '../../services/api';

interface PhotoCardProps {
  photo: Photo;
  selected?: boolean;
  selectionMode?: boolean;
  onClick: () => void;
}

export function PhotoCard({ photo, selected, selectionMode, onClick }: PhotoCardProps) {
  const thumbnailUrl = api.getThumbnail(photo.path);

  return (
    <div
      className={`relative bg-card rounded cursor-pointer overflow-hidden transition-all duration-200 ${
        selected
          ? 'ring-3 ring-primary ring-offset-1 shadow-[0_4px_12px_rgba(0,0,0,0.15)]'
          : 'hover:shadow-[0_0_0_2px_var(--color-primary),0_4px_12px_rgba(0,0,0,0.1)] hover:-translate-y-0.5'
      }`}
      onClick={onClick}
    >
      <img
        src={thumbnailUrl}
        alt={photo.name}
        className={`w-full h-full object-cover transition-transform duration-300 ${selectionMode ? '' : 'hover:scale-105'}`}
        loading="lazy"
      />
      {selected && (
        <div className="absolute top-2 left-2 w-5 h-5 bg-primary rounded-full flex items-center justify-center shadow-md">
          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )}
      {photo.type === 'video' && (
        <div className="absolute top-2 right-2 bg-primary text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
          ▶ {photo.duration}
        </div>
      )}
      <div className="absolute bottom-0 left-0 right-0 pt-5 pb-2 px-2 bg-gradient-to-t from-black/65 to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100">
        <div className="text-[11px] text-white font-medium truncate">{photo.name}</div>
        <div className="font-mono text-[10px] text-white/75 mt-0.5">{photo.date}</div>
      </div>
    </div>
  );
}
