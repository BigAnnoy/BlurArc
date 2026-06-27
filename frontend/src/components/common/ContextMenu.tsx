import { useEffect, useRef } from 'react';

interface MenuItem {
  label: string;
  icon?: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}

interface MenuGroup {
  items: MenuItem[];
}

interface ContextMenuProps {
  isOpen: boolean;
  onClose: () => void;
  x: number;
  y: number;
  groups: MenuGroup[];
}

export function ContextMenu({ isOpen, onClose, x, y, groups }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEsc);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEsc);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // 调整位置避免超出屏幕
  const menuStyle = {
    position: 'fixed' as const,
    left: Math.min(x, window.innerWidth - 200),
    top: Math.min(y, window.innerHeight - 300),
    zIndex: 100,
  };

  return (
    <div ref={menuRef} style={menuStyle} className="bg-card rounded-lg shadow-lg border border-border py-1 min-w-[180px]">
      {groups.map((group, groupIdx) => (
        <div key={groupIdx}>
          {groupIdx > 0 && <div className="my-1 border-t border-border" />}
          {group.items.map((item, itemIdx) => (
            <button
              key={itemIdx}
              onClick={() => {
                item.onClick();
                onClose();
              }}
              disabled={item.disabled}
              className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 transition-colors ${
                item.danger
                  ? 'text-red-500 hover:bg-red-50'
                  : item.disabled
                  ? 'text-text-tertiary cursor-not-allowed'
                  : 'text-text-primary hover:bg-hover'
              }`}
            >
              {item.icon && <span className="w-4">{item.icon}</span>}
              {item.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
