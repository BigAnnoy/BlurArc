// Photo types
export interface Photo {
  id: string;
  name: string;
  path: string;
  size: number;
  date: string;
  type: 'photo' | 'video';
  duration?: string; // for videos
  thumbnail?: string;
}

// Directory tree types
export interface MonthNode {
  name: string;
  path: string;
  count: number;
}

export interface YearNode {
  year: string;
  months: MonthNode[];
}

export interface DirNode {
  name: string;
  path: string;
  count: number;
  children: DirNode[];
}

// Stats types
export interface Stats {
  totalFiles: number;
  videoCount: number;
  totalSize: string;
  lastImport: string;
}

// Import types
export interface ImportProgress {
  step: number;
  total: number;
  current: string;
  status: 'scanning' | 'importing' | 'done' | 'error';
}

export interface ImportResult {
  imported: number;
  skipped: number;
  duplicates: number;
  errors: string[];
}

// Settings types
export interface Settings {
  albumPath: string;
  theme: 'light' | 'dark' | 'system';
  language: 'zh' | 'en';
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
