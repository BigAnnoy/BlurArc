import { useI18n } from '../../contexts/I18nContext';

interface FilterOption {
  key: string;
  label: string;
  icon: string;
}

interface FilterMenuProps {
  isOpen: boolean;
  options: FilterOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  onClose: () => void;  // 新增：关闭回调
}

export function FilterMenu({ isOpen, options, selected, onChange, onClose }: FilterMenuProps) {
  const { t } = useI18n();
  if (!isOpen) return null;

  const toggle = (key: string) => {
    if (selected.includes(key)) {
      onChange(selected.filter(k => k !== key));
    } else {
      onChange([...selected, key]);
    }
  };

  // Apple Photos 风格：modal-mask 居中卡片，多选不关闭
  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="w-[360px] bg-card rounded-lg shadow-lg py-2"
        onClick={e => e.stopPropagation()}
      >
        {/* 卡片标题：小号大写灰色文字 */}
        <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-border">
          <div className="text-[13px] text-text-secondary uppercase tracking-wider">{t('main.filter')}</div>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded-full border-none bg-transparent text-text-tertiary cursor-pointer text-lg leading-none hover:bg-page hover:text-text-primary transition-colors"
          >
            ×
          </button>
        </div>
        {/* 选项列表：filter-item 样式，左 icon + label + 右 ✓（多选，点击不关闭） */}
        <div className="max-h-[400px] overflow-y-auto">
          {options.map(opt => (
            <button
              key={opt.key}
              onClick={() => toggle(opt.key)}
              className="w-full flex items-center gap-3 px-4 py-2 bg-transparent border-none text-[13px] text-text-primary text-left cursor-pointer hover:bg-page transition-colors"
            >
              <span className="w-5 text-center text-sm text-text-secondary">{opt.icon}</span>
              <span>{opt.label}</span>
              <span className={`ml-auto text-primary ${selected.includes(opt.key) ? 'opacity-100' : 'opacity-0'}`}>✓</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
