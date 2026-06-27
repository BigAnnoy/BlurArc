import { useState } from 'react';
import type { DirNode } from '../../types';
import { ContextMenu } from '../common/ContextMenu';
import { api } from '../../services/api';

interface DirectoryTreeProps {
  /** 已废弃：v0.7.1 文件夹视图不再按年份单独分组，仅保留根节点递归展开 */
  years?: unknown[];
  rootDir: DirNode | null;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

export function DirectoryTree({ rootDir, selectedPath, onSelect }: DirectoryTreeProps) {
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set([rootDir?.path || '']));
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; path: string } | null>(null);

  const handleShowInExplorer = async (path: string) => {
    try {
      await api.openInExplorer(path);
    } catch (error) {
      console.error('打开资源管理器失败:', error);
    }
  };

  const handleScanNewFiles = async (path: string) => {
    try {
      await api.scanDirectory(path);
      onSelect(path);
    } catch (error) {
      console.error('扫描新增失败:', error);
    }
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

  // 递归渲染文件夹树（按 rootDir 实际子目录结构展开，不再按 YYYY 年份分组）
  const renderDirNode = (dir: DirNode, depth: number) => {
    const isExpanded = expandedDirs.has(dir.path);
    const hasChildren = dir.children && dir.children.length > 0;
    const isSelected = selectedPath === dir.path;
    // 与原型 album-management-v2-light.html 一致：每层缩进 14px
    const paddingLeft = 8 + depth * 14;

    return (
      <div key={dir.path}>
        <div
          className={`group flex items-center py-1.5 pr-2.5 text-[13px] cursor-pointer rounded-md transition-all duration-150 ${
            isSelected
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:bg-page hover:text-text-primary'
          }`}
          style={{ paddingLeft: `${paddingLeft}px` }}
          onContextMenu={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setContextMenu({ x: e.clientX, y: e.clientY, path: dir.path });
          }}
        >
          {hasChildren ? (
            <span
              className="w-3 mr-1 text-[10px] text-text-tertiary transition-transform duration-150 flex-shrink-0 leading-none"
              style={{ transform: isExpanded ? 'rotate(90deg)' : 'none' }}
              onClick={(e) => {
                e.stopPropagation();
                toggleDir(dir.path);
              }}
            >
              ▶
            </span>
          ) : (
            <span className="w-3 mr-1 flex-shrink-0" />
          )}
          <span
            className="flex-1 truncate"
            onClick={() => onSelect(dir.path)}
          >
            {dir.name}
          </span>
          <span
            className="font-mono text-[11px] opacity-70 flex-shrink-0 ml-2 tabular-nums"
            onClick={() => onSelect(dir.path)}
          >
            {dir.count}
          </span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {dir.children!.map((child) => renderDirNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (!rootDir) {
    return (
      <div className="text-[12px] text-text-tertiary px-2.5 py-1.5">
        暂无文件夹
      </div>
    );
  }

  return (
    <div>
      {/* 递归展开 rootDir 全部子目录（年份/月份/任意嵌套文件夹都按实际目录显示） */}
      {rootDir.children && rootDir.children.length > 0 && (
        <div>
          {rootDir.children.map((child) => renderDirNode(child, 0))}
        </div>
      )}

      {contextMenu && (
        <ContextMenu
          isOpen={true}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          groups={[
            {
              items: [
                {
                  label: '在资源管理器中显示',
                  onClick: () => {
                    handleShowInExplorer(contextMenu.path);
                  }
                },
                {
                  label: '扫描新增',
                  onClick: () => {
                    handleScanNewFiles(contextMenu.path);
                  }
                }
              ]
            }
          ]}
        />
      )}
    </div>
  );
}
