// 导入弹窗类型定义

export type ImportMode = 'copy' | 'move';
export type ImportStep = 'select-mode' | 'select-path' | 'phone-upload' | 'checking' | 'preview' | 'importing';

// 照片信息
export interface ImportPhoto {
  name: string;
  path: string;
  size: number;
  date?: string;
  thumbnail_url?: string;
  url?: string;
}

// 日期文件夹
export interface DateFolder {
  name: string;
  count: number;
  size: number;
  files: ImportPhoto[];
}

// 检查结果
export interface CheckResult {
  status: string;
  source_path: string;
  media_count: number;
  total_size_mb: number;
  date_folders: DateFolder[];
  target_duplicates: Record<string, ImportPhoto[]>;
  source_duplicates: Record<string, ImportPhoto[]>;
}

// 检查进度
export interface CheckProgress {
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  stage: 'queued' | 'scanning' | 'grouping' | 'source_duplicates' | 'target_duplicates' | 'completed' | 'failed';
  detail: string;
  result?: CheckResult;
}

// 导入进度
export interface ImportProgress {
  step: number;
  total: number;
  current: string;
  status: 'idle' | 'pending' | 'running' | 'scanning' | 'paused' | 'completed' | 'done' | 'failed' | 'error' | 'cancelled';
  progress?: number;
  error?: string;
  failed?: number;
  duplicated?: number;
}

// 阶段文本映射
export function getCheckStageText(t: (key: string) => string): Record<string, string> {
  return {
    queued: t('checkStage.queued'),
    scanning: t('checkStage.scanning'),
    grouping: t('checkStage.grouping'),
    source_duplicates: t('checkStage.source_duplicates'),
    target_duplicates: t('checkStage.target_duplicates'),
    completed: t('checkStage.completed'),
    failed: t('checkStage.failed'),
  };
}
