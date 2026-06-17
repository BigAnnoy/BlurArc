import { useState } from 'react';
import type { YearNode, DirNode } from '../../types';
import { useI18n } from '../../contexts/I18nContext';

interface DirectoryTreeProps {
  years: YearNode[];
  rootDir: DirNode | null;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

export function DirectoryTree({ years, rootDir, selectedPath, onSelect }: DirectoryTreeProps) {
  const [expandedYears, setExpandedYears] = useState<Set<string>>(new Set());
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const { t, language } = useI18n();

  const toggleYear = (year: string) => {
    const next = new Set(expandedYears);
    if (next.has(year)) {
      next.delete(year);
    } else {
      next.add(year);
    }
    setExpandedYears(next);
  };

  const toggleDir = (path: string) => {
    const next = new Set(expandedDirs);
    if (next.has(path)) {
      next.delete(path);
    } else {
      next.add(path);
    }
    setExpandedDirs(next);
  };

  // 格式化月份名称（支持国际化）
  const formatMonthName = (monthName: string): string => {
    // monthName 现在是原始目录名，如 "2024-01"
    const match = monthName.match(/^(\d{4})-(\d{2})$/);
    if (!match) return monthName;
    
    const monthNum = parseInt(match[2]);
    
    if (language === 'zh') {
      return `${monthNum}月`;
    } else {
      // 英文月份缩写
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return monthNames[monthNum - 1] || monthName;
    }
  };

  const renderDirNode = (dir: DirNode, depth: number) => {
    const isExpanded = expandedDirs.has(dir.path);
    const hasChildren = dir.children && dir.children.length > 0;
    const isSelected = selectedPath === dir.path;
    const paddingLeft = depth * 14;

    return (
      <div key={dir.path}>
        <div
          className={`flex items-center py-1.5 px-2.5 mb-0.5 text-[13px] cursor-pointer rounded transition-all ${
            isSelected
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:bg-page hover:text-text-primary'
          }`}
          style={{ paddingLeft: `${paddingLeft + 8}px` }}
        >
          {hasChildren ? (
            <span
              className="text-[8px] text-text-tertiary transition-transform duration-150 mr-1.5 flex-shrink-0"
              style={{ transform: isExpanded ? 'rotate(90deg)' : 'none' }}
              onClick={(e) => {
                e.stopPropagation();
                toggleDir(dir.path);
              }}
            >
              ▶
            </span>
          ) : (
            <span className="w-[11px] mr-1.5 flex-shrink-0" />
          )}
          <span
            className="truncate flex-1"
            onClick={() => onSelect(dir.path)}
          >
            {dir.name}
          </span>
          <span
            className="font-mono text-[11px] opacity-70 flex-shrink-0 ml-2"
            onClick={() => onSelect(dir.path)}
          >
            {dir.count}
          </span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {dir.children.map((child) => renderDirNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      {years.length > 0 && (
        <>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-text-tertiary mb-2">
            {t('sidebar.browseByYear')}
          </div>
          {years.map((yearNode) => (
            <div key={yearNode.year} className="mb-1">
              <button
                onClick={() => toggleYear(yearNode.year)}
                className="flex items-center gap-1.5 py-2 w-full text-left text-sm font-medium text-text-primary hover:text-primary transition-colors"
              >
                <span
                  className="text-[8px] text-text-tertiary transition-transform duration-150"
                  style={{ transform: expandedYears.has(yearNode.year) ? 'rotate(90deg)' : 'none' }}
                >
                  ▶
                </span>
                {yearNode.year}
              </button>
              {expandedYears.has(yearNode.year) && (
                <div className="pl-3.5">
                  {yearNode.months.map((month) => (
                    <div
                      key={month.path}
                      onClick={() => onSelect(month.path)}
                      className={`flex justify-between items-center py-1.5 px-2.5 -ml-2.5 mb-0.5 text-[13px] cursor-pointer rounded transition-all ${
                        selectedPath === month.path
                          ? 'bg-primary text-white'
                          : 'text-text-secondary hover:bg-page hover:text-text-primary'
                      }`}
                    >
                      <span>{formatMonthName(month.name)}</span>
                      <span className="font-mono text-[11px] opacity-70">{month.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {rootDir && (
        <>
          {years.length > 0 && (
            <div className="text-[11px] font-semibold uppercase tracking-wide text-text-tertiary mb-2 mt-4">
              {t('sidebar.folders')}
            </div>
          )}
          {renderDirNode(rootDir, 0)}
        </>
      )}
    </div>
  );
}
