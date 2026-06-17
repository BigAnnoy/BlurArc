import { useTheme } from '../../hooks/useTheme';
import { useI18n } from '../../contexts/I18nContext';
import { Logo } from '../common/Logo';

interface HeaderProps {
  onSettings?: () => void;
}

export function Header({ onSettings }: HeaderProps) {
  const { toggleTheme } = useTheme();
  const { t } = useI18n();

  return (
    <header className="flex items-center justify-between px-5 h-[52px] bg-card border-b border-border">
      <div className="flex items-center gap-2.5">
        <Logo size={32} />
        <span className="font-semibold text-[16px] tracking-tight text-text-primary">Blur<span className="font-light text-primary"> Arc</span></span>
      </div>
      <div className="flex gap-1">
        <button
          onClick={toggleTheme}
          className="w-[34px] h-[34px] rounded-md border-none bg-transparent text-text-secondary cursor-pointer flex items-center justify-center hover:bg-page hover:text-primary transition-all duration-150"
          title={t('header.toggleTheme')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="5" />
            <path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
          </svg>
        </button>
        <button
          onClick={onSettings}
          className="w-[34px] h-[34px] rounded-md border-none bg-transparent text-text-secondary cursor-pointer flex items-center justify-center hover:bg-page hover:text-primary transition-all duration-150"
          title={t('header.settings')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v2m0 18v2M4.2 4.2l1.4 1.4m12.8 12.8l1.4 1.4M1 12h2m18 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
          </svg>
        </button>
      </div>
    </header>
  );
}
