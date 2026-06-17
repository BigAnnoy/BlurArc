import type { YearNode, DirNode } from '../../types';
import { StatsCard } from '../sidebar/StatsCard';
import { DirectoryTree } from '../sidebar/DirectoryTree';
import { useI18n } from '../../contexts/I18nContext';

interface SidebarProps {
  stats: { total: number; videos: number; size: string } | null;
  years: YearNode[];
  rootDir: DirNode | null;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  onImport: () => void;
}

export function Sidebar({ stats, years, rootDir, selectedPath, onSelectPath, onImport }: SidebarProps) {
  const { t } = useI18n();

  return (
    <aside className="w-[250px] h-full bg-card border-r border-border flex flex-col overflow-hidden">
      {/* 可滚动区域 */}
      <div className="flex-1 overflow-y-auto p-4 min-h-0">
        {stats && <StatsCard total={stats.total} videos={stats.videos} size={stats.size} />}
        <DirectoryTree years={years} rootDir={rootDir} selectedPath={selectedPath} onSelect={onSelectPath} />
      </div>
      {/* 导入按钮 - 固定在底部，永远可见 */}
      <div className="p-4 border-t border-border flex-shrink-0">
        <button
          onClick={onImport}
          className="w-full py-2.5 bg-primary text-white border-none rounded-md font-medium text-sm cursor-pointer hover:bg-primary-hover transition-all duration-150"
        >
          {t('sidebar.importPhotos')}
        </button>
      </div>
    </aside>
  );
}
