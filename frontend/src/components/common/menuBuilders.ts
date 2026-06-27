import type { MenuGroup } from './ContextMenu';

export interface PhotoMenuOptions {
  isFavorite: boolean;
  inAlbumId?: string | number | null;
  onPreview: () => void;
  onToggleFavorite: () => void;
  onJoinAlbum: () => void;
  onRemoveFromAlbum?: () => void;
  onOpenInExplorer: () => void;
  onDelete: () => void;
  t: (key: string) => string;
}

export function buildPhotoMenu(opts: PhotoMenuOptions): MenuGroup[] {
  const { isFavorite, inAlbumId, onPreview, onToggleFavorite, onJoinAlbum, onRemoveFromAlbum, onOpenInExplorer, onDelete, t } = opts;

  const groups: MenuGroup[] = [
    {
      items: [
        { label: t('menu.preview'), onClick: onPreview },
        {
          label: isFavorite ? t('menu.removeFavorite') : t('menu.addFavorite'),
          onClick: onToggleFavorite,
        },
      ],
    },
  ];

  // Album operations
  if (inAlbumId) {
    groups.push({
      items: [
        { label: t('menu.removeFromAlbum'), onClick: onRemoveFromAlbum || (() => {}), danger: true },
        { label: t('menu.joinOtherAlbum'), onClick: onJoinAlbum },
      ],
    });
  } else {
    groups.push({
      items: [{ label: t('menu.joinAlbum'), onClick: onJoinAlbum }],
    });
  }

  // File system
  groups.push({
    items: [{ label: t('menu.openInExplorer'), onClick: onOpenInExplorer }],
  });

  // Delete
  groups.push({
    items: [{ label: t('menu.delete'), onClick: onDelete, danger: true }],
  });

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
