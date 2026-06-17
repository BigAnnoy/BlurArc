import { useState, useMemo } from 'react';
import { api } from '../../../services/api';
import { useI18n } from '../../../contexts/I18nContext';
import type { ImportPhoto } from './types';

interface TargetDuplicatesTabProps {
  duplicates: Record<string, ImportPhoto[]>;
  onPreviewPhoto: (photo: ImportPhoto) => void;
  onDeleteFiles: (paths: string[]) => void;
  albumPath?: string;
}

export function TargetDuplicatesTab({
  duplicates,
  onPreviewPhoto,
  onDeleteFiles,
  albumPath = '',
}: TargetDuplicatesTabProps) {
  const { t } = useI18n();
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());

  // 重复组数量
  const dupCount = Object.keys(duplicates).length;

  // 当前选中组的照片
  const currentPhotos = useMemo(() => {
    if (!selectedHash) return [];
    return duplicates[selectedHash] || [];
  }, [selectedHash, duplicates]);

  // 选择重复照片（每组保留一张，选择其他重复文件）
  const handleSelectDuplicates = () => {
    const newSelected = new Set<string>();
    for (const files of Object.values(duplicates)) {
      if (files.length <= 1) continue;
      
      // 找到相册中的文件（在 albumPath 中的文件）
      const albumFile = files.find(f => albumPath && f.path.startsWith(albumPath));
      
      // 如果找到相册中的文件，选择其他所有文件（准备删除）
      // 如果没找到，选择除了第一张之外的所有文件
      for (const file of files) {
        if (albumFile) {
          // 不选择相册中的文件，选择其他所有文件
          if (file.path !== albumFile.path) {
            newSelected.add(file.path);
          }
        } else {
          // 没有相册文件时，保留第一张，选择其他所有文件
          if (file !== files[0]) {
            newSelected.add(file.path);
          }
        }
      }
    }
    setSelectedPaths(newSelected);
    
    // 自动选中第一个重复组，让用户能看到选中的照片
    const firstHash = Object.keys(duplicates)[0];
    if (firstHash && !selectedHash) {
      setSelectedHash(firstHash);
    }
  };

  // 删除所选
  const handleDeleteSelected = () => {
    if (selectedPaths.size > 0) {
      if (!window.confirm(t('target.deleteConfirm', { count: selectedPaths.size }))) return;
      onDeleteFiles(Array.from(selectedPaths));
      setSelectedPaths(new Set());
    }
  };

  // 点击照片 - 预览
  const handlePhotoClick = (photo: ImportPhoto) => {
    onPreviewPhoto(photo);
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-text-secondary">
        {t('target.description')}
      </p>

      {/* 操作栏 */}
      <div className="flex items-center justify-between flex-wrap gap-2 p-2 bg-page rounded-lg border border-border">
        <div className="flex items-center gap-4">
          <span className="text-sm">
            <strong>{t('target.inAlbum')}</strong> {t('target.groups', { count: dupCount })}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSelectDuplicates}
            disabled={dupCount === 0}
            className="px-3 py-1 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50 transition-all"
          >
            {selectedPaths.size > 0 ? t('target.selectedSourceFiles', { count: selectedPaths.size }) : t('target.selectDuplicates')}
          </button>
          <button
            onClick={handleDeleteSelected}
            disabled={selectedPaths.size === 0}
            className="px-3 py-1 text-xs bg-card border border-border rounded hover:border-primary disabled:opacity-50 transition-all"
          >
            {t('target.deleteSelection')} ({selectedPaths.size})
          </button>
        </div>
      </div>

      {/* 选中摘要 */}
      {selectedPaths.size > 0 && (
        <div className="flex items-center gap-2 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-sm">
          <span>{t('target.selectedSummary', { count: selectedPaths.size })}</span>
          <button
            onClick={() => setSelectedPaths(new Set())}
            className="ml-auto text-xs text-text-secondary hover:text-text-primary"
          >
            {t('target.clearSelection')}
          </button>
        </div>
      )}

      {/* 重复组列表 + 照片预览 */}
      <div className="flex gap-3 h-[500px]">
        {/* 左侧：重复组列表 */}
        <div className="w-48 flex-shrink-0 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
          <div className="px-3 py-2 border-b border-border text-sm font-medium bg-page">{t('target.duplicateFiles')}</div>
          <div className="flex-1 overflow-y-auto">
            {dupCount > 0 ? (
              Object.entries(duplicates).map(([hash, files]) => {
                const lastName = files[files.length - 1]?.name || hash.slice(0, 8);
                return (
                  <div
                    key={hash}
                    onClick={() => setSelectedHash(hash)}
                    className={`px-3 py-2 cursor-pointer text-sm transition-colors ${
                      selectedHash === hash
                        ? 'bg-primary-light text-primary'
                        : 'hover:bg-page'
                    }`}
                  >
                    <div className="font-medium truncate" title={lastName}>📷 {lastName}</div>
                    <div className="text-xs text-text-secondary">{t('target.duplicateWithAlbum')}</div>
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-center text-sm text-text-tertiary">{t('target.noDuplicates')}</div>
            )}
          </div>
        </div>

        {/* 右侧：照片预览 */}
        <div className="flex-1 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
          <div className="px-3 py-2 border-b border-border text-sm font-medium bg-page">{t('target.duplicatePreview')}</div>
          <div className="flex-1 overflow-y-auto p-2">
            {currentPhotos.length > 0 ? (
              <div className="grid grid-cols-[repeat(auto-fill,minmax(80px,1fr))] gap-1">
                {currentPhotos.map((photo) => {
                  const isSelected = selectedPaths.has(photo.path);
                  const isAlbumFile = photo.path.startsWith(albumPath);
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
                      {isAlbumFile && (
                        <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[8px] text-center py-0.5">
                          {t('target.album')}
                        </div>
                      )}
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
                {t('target.selectGroup')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
