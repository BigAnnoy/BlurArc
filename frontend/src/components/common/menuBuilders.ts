import type { MenuGroup } from './ContextMenu';

export interface PhotoMenuOptions {
  isFavorite: boolean;
  inAlbumId?: string | number | null;
  onPreview?: () => void;
  onToggleFavorite?: () => void;
  onJoinAlbum?: () => void;
  onRemoveFromAlbum?: () => void;
  onOpenInExplorer?: () => void;
  onDelete?: () => void;
  t: (key: string) => string;
}

export function buildPhotoMenu(opts: PhotoMenuOptions): MenuGroup[] {
  const { isFavorite, inAlbumId, onPreview, onToggleFavorite, onJoinAlbum, onRemoveFromAlbum, onOpenInExplorer, onDelete, t } = opts;

  const groups: MenuGroup[] = [];

  // Group 1: Preview + Favorite
  const group1Items: MenuGroup['items'] = [];
  if (onPreview) group1Items.push({ label: t('menu.preview'), onClick: onPreview });
  if (onToggleFavorite) group1Items.push({
    label: isFavorite ? t('menu.removeFavorite') : t('menu.addFavorite'),
    onClick: onToggleFavorite,
  });
  if (group1Items.length > 0) groups.push({ items: group1Items });

  // Album operations
  const albumItems: MenuGroup['items'] = [];
  if (inAlbumId) {
    if (onRemoveFromAlbum) albumItems.push({ label: t('menu.removeFromAlbum'), onClick: onRemoveFromAlbum, danger: true });
    if (onJoinAlbum) albumItems.push({ label: t('menu.joinOtherAlbum'), onClick: onJoinAlbum });
  } else {
    if (onJoinAlbum) albumItems.push({ label: t('menu.joinAlbum'), onClick: onJoinAlbum });
  }
  if (albumItems.length > 0) groups.push({ items: albumItems });

  // File system
  if (onOpenInExplorer) {
    groups.push({ items: [{ label: t('menu.openInExplorer'), onClick: onOpenInExplorer }] });
  }

  // Delete
  if (onDelete) {
    groups.push({ items: [{ label: t('menu.delete'), onClick: onDelete, danger: true }] });
  }

  return groups;
}

export interface AlbumMenuOptions {
  onOpen: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  t: (key: string) => string;
}

export function buildAlbumMenu(opts: AlbumMenuOptions): MenuGroup[] {
  const { onOpen, onRename, onDuplicate, onDelete, t } = opts;
  return [
    {
      items: [
        { label: t('menu.open'), onClick: onOpen },
        { label: t('menu.rename'), onClick: onRename },
        { label: t('menu.duplicate'), onClick: onDuplicate },
        { label: t('menu.delete'), onClick: onDelete, danger: true },
      ],
    },
  ];
}

export interface DirectoryMenuOptions {
  onOpenInExplorer: () => void;
  onScanNew: () => void;
  t: (key: string) => string;
}

export function buildDirectoryMenu(opts: DirectoryMenuOptions): MenuGroup[] {
  const { onOpenInExplorer, onScanNew, t } = opts;
  return [
    {
      items: [
        { label: t('menu.openInExplorer'), onClick: onOpenInExplorer },
        { label: t('menu.scanNew'), onClick: onScanNew },
      ],
    },
  ];
}
