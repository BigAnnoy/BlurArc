import { useState, useMemo } from 'react';
import { useI18n } from '../../../contexts/I18nContext';
import { StatsCards } from './StatsCards';
import { TimelineTab } from './TimelineTab';
import { TargetDuplicatesTab } from './TargetDuplicatesTab';
import { SourceDuplicatesTab } from './SourceDuplicatesTab';
import type { CheckResult, ImportPhoto } from './types';

interface Step2PreviewProps {
  previewData: CheckResult | null;
  onPreviewPhoto: (photo: ImportPhoto) => void;
  onDeleteFiles: (paths: string[]) => void;
  onStartImport: () => void;
  onBack: () => void;
}

type TabType = 'timeline' | 'target-duplicates' | 'source-duplicates';

export function Step2Preview({
  previewData,
  onPreviewPhoto,
  onDeleteFiles,
  onStartImport,
  onBack,
}: Step2PreviewProps) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<TabType>('timeline');

  // 统计数据
  const stats = useMemo(() => {
    if (!previewData) {
      return { mediaCount: 0, totalSizeMB: 0, targetDupCount: 0, sourceDupCount: 0 };
    }
    return {
      mediaCount: previewData.media_count,
      totalSizeMB: previewData.total_size_mb,
      targetDupCount: Object.keys(previewData.target_duplicates).length,
      sourceDupCount: Object.keys(previewData.source_duplicates).length,
    };
  }, [previewData]);

  if (!previewData) {
    return (
      <div className="p-8 text-center text-text-secondary">
        {t('preview.loadFailed')}
      </div>
    );
  }

  // 空文件夹提示
  if (previewData.media_count === 0) {
    return (
      <div className="p-8 text-center space-y-4">
        <div className="text-4xl">📭</div>
        <div className="text-lg font-medium text-text-primary">{t('preview.noMedia')}</div>
        <div className="text-sm text-text-secondary">
          {t('preview.noMediaDesc')}
        </div>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all"
        >
          {t('preview.backToSelect')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 源路径显示 */}
      <div className="text-sm text-text-secondary">
        {t('preview.sourcePath')}<span className="text-text-primary">{previewData.source_path}</span>
      </div>

      {/* 统计卡片 */}
      <StatsCards
        mediaCount={stats.mediaCount}
        totalSizeMB={stats.totalSizeMB}
      />

      {/* 标签页导航 */}
      <div className="flex gap-1 border-b border-border">
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === 'timeline'
              ? 'text-primary'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          📅 {t('preview.timeline')}
          {previewData.date_folders.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs bg-page rounded-full">
              {previewData.date_folders.length}
            </span>
          )}
          {activeTab === 'timeline' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('target-duplicates')}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === 'target-duplicates'
              ? 'text-primary'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          ⚠️ {t('preview.inAlbum')}
          {stats.targetDupCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded-full">
              {stats.targetDupCount}
            </span>
          )}
          {activeTab === 'target-duplicates' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('source-duplicates')}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === 'source-duplicates'
              ? 'text-primary'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          🗂 {t('preview.sourceDuplicates')}
          {stats.sourceDupCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded-full">
              {stats.sourceDupCount}
            </span>
          )}
          {activeTab === 'source-duplicates' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
          )}
        </button>
      </div>

      {/* 标签页内容 */}
      <div className="min-h-[350px]">
        {activeTab === 'timeline' && (
          <TimelineTab
            dateFolders={previewData.date_folders}
            onPreviewPhoto={onPreviewPhoto}
            onDeleteFiles={onDeleteFiles}
          />
        )}
        {activeTab === 'target-duplicates' && (
          <TargetDuplicatesTab
            duplicates={previewData.target_duplicates}
            onPreviewPhoto={onPreviewPhoto}
            onDeleteFiles={onDeleteFiles}
          />
        )}
        {activeTab === 'source-duplicates' && (
          <SourceDuplicatesTab
            duplicates={previewData.source_duplicates}
            onPreviewPhoto={onPreviewPhoto}
            onDeleteFiles={onDeleteFiles}
          />
        )}
      </div>

      {/* 操作按钮 */}
      <div className="flex justify-between pt-4 border-t border-border">
        <button
          onClick={onBack}
          className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all"
        >
          {t('preview.back')}
        </button>
        <button
          onClick={onStartImport}
          disabled={stats.mediaCount === 0}
          className="px-4 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover disabled:opacity-50 transition-all"
        >
          {t('preview.startImport')}
        </button>
      </div>
    </div>
  );
}
