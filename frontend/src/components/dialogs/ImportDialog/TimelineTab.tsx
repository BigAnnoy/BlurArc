import { useState, useMemo } from 'react';
import { api } from '../../../services/api';
import { useI18n } from '../../../contexts/I18nContext';
import type { DateFolder, ImportPhoto } from './types';

interface TimelineTabProps {
  dateFolders: DateFolder[];
  onPreviewPhoto: (photo: ImportPhoto) => void;
  onDeleteFiles: (paths: string[]) => void;
}

export function TimelineTab({ dateFolders, onPreviewPhoto, onDeleteFiles }: TimelineTabProps) {
  const { t } = useI18n();
  const [selectedDate, setSelectedDate] = useState<string | null>(
    dateFolders.length > 0 ? dateFolders[0].name : null
  );
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [selectionMode, setSelectionMode] = useState(false);

  // 当前选中日期的照片
  const currentPhotos = useMemo(() => {
    if (!selectedDate) return [];
    const folder = dateFolders.find((f) => f.name === selectedDate);
    return folder?.files || [];
  }, [selectedDate, dateFolders]);

  // 待导入总数
  const totalCount = useMemo(() => {
    return dateFolders.reduce((sum, f) => sum + f.count, 0);
  }, [dateFolders]);

  // 切换选择模式
  const handleToggleSelectionMode = () => {
    setSelectionMode(!selectionMode);
    setSelectedPaths(new Set());
  };

  // 点击照片
  const handlePhotoClick = (photo: ImportPhoto) => {
    if (selectionMode) {
      setSelectedPaths((prev) => {
        const next = new Set(prev);
        if (next.has(photo.path)) {
          next.delete(photo.path);
        } else {
          next.add(photo.path);
        }
        return next;
      });
    } else {
      onPreviewPhoto(photo);
    }
  };

  // 全选
  const handleSelectAll = () => {
    if (selectedPaths.size === currentPhotos.length) {
      setSelectedPaths(new Set());
    } else {
      setSelectedPaths(new Set(currentPhotos.map((p) => p.path)));
    }
  };

  // 删除所选
  const handleDeleteSelected = () => {
    if (selectedPaths.size > 0) {
      if (!window.confirm(t('timeline.deleteConfirm', { count: selectedPaths.size }))) return;
      onDeleteFiles(Array.from(selectedPaths));
      setSelectedPaths(new Set());
    }
  };

  // 切换日期时清理选中状态
  const handleDateChange = (date: string) => {
    setSelectedDate(date);
    setSelectedPaths(new Set());
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-text-secondary">
        {t('timeline.description')}
      </p>

      {/* 操作栏 */}
      <div className="flex items-center justify-between p-2 bg-page rounded-lg border border-border">
        <span className="text-sm">
          <strong>{t('timeline.toImport')}</strong> {t('timeline.files', { count: totalCount })}
        </span>
        <div className="flex gap-2">
          {selectionMode ? (
            <>
              <button
                onClick={handleToggleSelectionMode}
                className="px-3 py-1 text-xs bg-card border border-border rounded hover:border-primary transition-all"
              >
                {t('timeline.cancel')}
              </button>
              <button
                onClick={handleSelectAll}
                className="px-3 py-1 text-xs bg-card border border-border rounded hover:border-primary transition-all"
              >
                {selectedPaths.size === currentPhotos.length ? t('timeline.cancelSelect') : t('timeline.selectAll')}
              </button>
              <button
                onClick={handleDeleteSelected}
                disabled={selectedPaths.size === 0}
                className="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50 transition-all"
              >
                🗑 {t('timeline.deleteSelected')} ({selectedPaths.size})
              </button>
            </>
          ) : (
            <button
              onClick={handleToggleSelectionMode}
              className="px-3 py-1 text-xs bg-card border border-border rounded hover:border-primary transition-all"
            >
              {t('timeline.select')}
            </button>
          )}
        </div>
      </div>

      {/* 日期筛选 + 照片网格 */}
      <div className="flex gap-3 h-[500px]">
        {/* 左侧：日期列表 */}
        <div className="w-48 flex-shrink-0 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
          <div className="px-3 py-2 border-b border-border text-sm font-medium bg-page">{t('timeline.dateFilter')}</div>
          <div className="flex-1 overflow-y-auto">
            {dateFolders.length > 0 ? (
              dateFolders.map((folder) => (
                <div
                  key={folder.name}
                  onClick={() => handleDateChange(folder.name)}
                  className={`px-3 py-2 cursor-pointer text-sm transition-colors ${
                    selectedDate === folder.name
                      ? 'bg-primary-light text-primary'
                      : 'hover:bg-page'
                  }`}
                >
                  <div className="font-medium">{folder.name}</div>
                  <div className="text-xs text-text-secondary">{t('timeline.files', { count: folder.count })}</div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-sm text-text-tertiary">{t('timeline.noFiles')}</div>
            )}
          </div>
        </div>

        {/* 右侧：照片网格 */}
        <div className="flex-1 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
          <div className="px-3 py-2 border-b border-border text-sm font-medium bg-page">{t('timeline.photoPreview')}</div>
          <div className="flex-1 overflow-y-auto p-2">
            {currentPhotos.length > 0 ? (
              <div className="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-2">
                {currentPhotos.map((photo) => {
                  const isSelected = selectedPaths.has(photo.path);
                  return (
                    <div
                      key={photo.path}
                      onClick={() => handlePhotoClick(photo)}
                      className={`relative aspect-square rounded cursor-pointer overflow-hidden transition-all ${
                        isSelected
                          ? 'ring-2 ring-primary ring-offset-1'
                          : 'hover:ring-1 hover:ring-primary'
                      }`}
                    >
                      <img
                        src={photo.thumbnail_url || api.getThumbnail(photo.path)}
                        alt={photo.name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                      {isSelected && (
                        <div className="absolute top-1 left-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                          <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-text-tertiary">
                {t('timeline.selectDate')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
