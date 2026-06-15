"""
导入管理模块 - 处理照片导入逻辑
支持后台线程、进度跟踪、MD5 去重、文件整理
"""

import os
import sys
import json
import shutil
import hashlib
import logging
import threading
import time
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from enum import Enum
from collections import defaultdict

# 视频处理模块
from .video_processor import VideoProcessor

# 数据库模块
from .database import SessionLocal, Photo, ImportHistory

# 共享常量和工具
from .constants import MEDIA_FORMATS, VIDEO_FORMATS
from .utils import compute_md5

# 日志配置
logger = logging.getLogger(__name__)

# ============================================================================
# 常量和枚举
# ============================================================================

RECORD_FILENAME = ".photo_organizer.json"


class ImportStatus(Enum):
    """导入状态"""
    PENDING = "pending"          # 等待中
    SCANNING = "scanning"        # 扫描源目录
    PROCESSING = "processing"    # 处理中
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


class FileConflict(Enum):
    """文件冲突类型"""
    NONE = "none"                # 无冲突
    MD5_DUPLICATE = "md5"        # MD5 重复
    NAME_DUPLICATE = "name"      # 文件名重复


# ============================================================================
# 进度跟踪
# ============================================================================

class ImportProgress:
    """导入进度跟踪（线程安全版）"""
    
    def __init__(self, import_id: str):
        self.import_id = import_id
        self.status = ImportStatus.PENDING
        self.total_files = 0
        self.processed_files = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.duplicated_files = 0
        self.total_size = 0
        self.processed_size = 0
        self.start_time = None
        self.end_time = None
        self.current_file = None
        self.error_message = None
        self.file_details = []  # 文件详细信息
        
        # 添加线程锁，确保多线程环境下的安全访问
        self._lock = threading.Lock()
    
    def to_dict(self) -> Dict:
        """转换为字典（线程安全）"""
        with self._lock:
            elapsed_time = 0
            if self.start_time:
                end = self.end_time or datetime.now()
                elapsed_time = (end - self.start_time).total_seconds()
            
            return {
                'import_id': self.import_id,
                'status': self.status.value,
                'progress': self._calculate_progress(),
                'total_files': self.total_files,
                'processed_files': self.processed_files,
                'skipped_files': self.skipped_files,
                'failed_files': self.failed_files,
                'duplicated_files': self.duplicated_files,
                'total_size': self.total_size,
                'total_size_mb': round(self.total_size / (1024 * 1024), 2),
                'processed_size': self.processed_size,
                'processed_size_mb': round(self.processed_size / (1024 * 1024), 2),
                'current_file': self.current_file,
                'elapsed_time': round(elapsed_time, 1),
                'error_message': self.error_message
            }
    
    def _calculate_progress(self) -> int:
        """计算进度百分比（内部方法，调用者需确保已获取锁）"""
        if self.total_files == 0:
            return 0
        # 进度 = (成功 + 跳过 + 失败) / 总数
        completed = self.processed_files + self.skipped_files + self.failed_files
        return min(100, int((completed / self.total_files) * 100))
    
    def add_file(self, filepath: Path, size: int, conflict: FileConflict = FileConflict.NONE, success: bool = True):
        """添加文件记录（线程安全）"""
        detail = {
            'filename': filepath.name,
            'size': size,
            'conflict': conflict.value,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        with self._lock:
            self.file_details.append(detail)
            
            if success:
                self.processed_files += 1
                self.processed_size += size
                if conflict != FileConflict.NONE:
                    self.duplicated_files += 1
            else:
                self.failed_files += 1
    
    def skip_file(self, filepath: Path, size: int):
        """跳过文件（线程安全）"""
        with self._lock:
            self.skipped_files += 1
    
    def update_total_files(self, total: int):
        """更新总文件数（线程安全）"""
        with self._lock:
            self.total_files = total
    
    def update_total_size(self, size: int):
        """更新总大小（线程安全）"""
        with self._lock:
            self.total_size = size
    
    def update_current_file(self, filename: str):
        """更新当前处理的文件名（线程安全）"""
        with self._lock:
            self.current_file = filename
    
    def update_status(self, status: ImportStatus):
        """更新导入状态（线程安全）"""
        with self._lock:
            self.status = status


# ============================================================================
# 导入管理器
# ============================================================================

class ImportManager:
    """导入管理器 - 处理导入逻辑"""
    
    def __init__(self):
        self.imports: Dict[str, ImportProgress] = {}
        self.import_threads: Dict[str, threading.Thread] = {}
        self.cancel_flags: Dict[str, bool] = {}
        self.pause_events: Dict[str, threading.Event] = {}
        self.lock = threading.Lock()
    
    def create_import(self, import_id: str, source_path: str, target_path: str) -> ImportProgress:
        """创建导入任务"""
        with self.lock:
            progress = ImportProgress(import_id)
            self.imports[import_id] = progress
            self.cancel_flags[import_id] = False
            # pause_event 默认 set()，即不阻塞；暂停时 clear()，恢复时 set()
            event = threading.Event()
            event.set()
            self.pause_events[import_id] = event
            return progress
    
    def get_progress(self, import_id: str) -> Optional[ImportProgress]:
        """获取导入进度"""
        with self.lock:
            return self.imports.get(import_id)
    
    def cancel_import(self, import_id: str):
        """取消导入"""
        with self.lock:
            if import_id in self.cancel_flags:
                self.cancel_flags[import_id] = True
            # 取消时同时恢复暂停，让阻塞线程得以检测 cancel 并退出
            if import_id in self.pause_events:
                self.pause_events[import_id].set()
    
    def pause_import(self, import_id: str):
        """暂停导入（处理完当前文件后生效）"""
        with self.lock:
            event = self.pause_events.get(import_id)
            progress = self.imports.get(import_id)
        if event and progress and progress.status == ImportStatus.PROCESSING:
            event.clear()
            progress.update_status(ImportStatus.PAUSED)
            logger.info(f"导入已暂停: {import_id}")

    def resume_import(self, import_id: str):
        """继续导入"""
        with self.lock:
            event = self.pause_events.get(import_id)
            progress = self.imports.get(import_id)
        if event and progress and progress.status == ImportStatus.PAUSED:
            progress.update_status(ImportStatus.PROCESSING)
            event.set()
            logger.info(f"导入已继续: {import_id}")

    def get_progress_dict(self, import_id: str) -> Optional[Dict]:
        """获取进度字典，状态字段已反映 paused"""
        with self.lock:
            progress = self.imports.get(import_id)
        if not progress:
            return None
        return progress.to_dict()
    
    def _should_cancel(self, import_id: str) -> bool:
        """检查是否应该取消"""
        with self.lock:
            return self.cancel_flags.get(import_id, False)
    
    def start_import_async(self, import_id: str, source_path: str, target_path: str, import_mode: str = 'copy', skip_source_duplicates: bool = False, skip_target_duplicates: bool = False):
        """后台启动导入任务"""
        thread = threading.Thread(
            target=self._do_import,
            args=(import_id, source_path, target_path, import_mode, skip_source_duplicates, skip_target_duplicates),
            daemon=True  # 守护线程：窗口关闭后不阻止进程退出
        )
        thread.start()
        
        with self.lock:
            self.import_threads[import_id] = thread
    
    def _do_import(self, import_id: str, source_path: str, target_path: str, import_mode: str = 'copy', skip_source_duplicates: bool = False, skip_target_duplicates: bool = False):
        """执行导入（后台线程，优化版）
        
        优化点：
        1. 并行处理文件导入过程
        2. 批量加载文件大小信息
        3. 减少循环内的方法调用
        """
        logger.info(f"[_do_import] 导入任务开始: {import_id}, skip_source_duplicates={skip_source_duplicates}, skip_target_duplicates={skip_target_duplicates}")
        progress = self.get_progress(import_id)
        if not progress:
            return
        
        import_history_id = None
        
        try:
            # 创建导入历史记录
            db = SessionLocal()
            try:
                import_history = ImportHistory(
                    source_path=source_path,
                    target_path=target_path,
                    status=ImportStatus.SCANNING.value,
                    start_time=datetime.now(),
                    total_files=0,
                    imported_files=0,
                    skipped_files=0,
                    failed_files=0
                )
                db.add(import_history)
                db.commit()
                import_history_id = import_history.id
                logger.info(f"导入历史记录已创建，ID: {import_history_id}")
            except Exception as e:
                logger.error(f"创建导入历史记录失败: {e}")
                db.rollback()
            finally:
                db.close()
            
            progress.status = ImportStatus.SCANNING
            progress.start_time = datetime.now()
            
            source_path = Path(source_path)
            target_path = Path(target_path)
            
            # 验证路径
            if not source_path.exists() or not source_path.is_dir():
                raise ValueError(f"源路径无效: {source_path}")
            
            if not target_path.exists() or not target_path.is_dir():
                raise ValueError(f"目标路径无效: {target_path}")
            
            # 扫描源目录（忽略最后扫描时间，确保每次都能找到所有文件）
            logger.info(f"开始导入：{source_path} -> {target_path}")
            media_files = self._scan_source(source_path, ignore_last_scan=True)
            
            if not media_files:
                progress.status = ImportStatus.COMPLETED
                progress.error_message = "源目录中没有媒体文件"
                return
            
            # 保存原始扫描到的文件总数（用于统计）
            original_total_files = len(media_files)
            original_total_size = 0
            for file_path in media_files:
                try:
                    original_total_size += file_path.stat().st_size
                except Exception as e:
                    logger.debug(f"获取文件大小失败 {file_path}: {e}")
                    original_total_size += 0
            
            # 跳过源文件夹中重复的文件
            if skip_source_duplicates:
                logger.info(f"开始检测源文件夹中的重复文件，共 {len(media_files)} 个文件")
                # 计算所有文件的 MD5 哈希值
                md5_to_files = {}
                for file_path in media_files:
                    try:
                        file_md5 = self._compute_md5(file_path)
                        if file_md5:
                            if file_md5 not in md5_to_files:
                                md5_to_files[file_md5] = []
                            md5_to_files[file_md5].append(file_path)
                    except Exception as e:
                        logger.error(f"计算文件 MD5 失败 {file_path}: {e}")
                
                # 过滤出重复的文件组（只保留每个组的第一个文件）
                unique_files = []
                skipped_duplicates = 0
                for md5, files in md5_to_files.items():
                    if len(files) > 1:
                        # 保留第一个文件，跳过其他重复文件
                        unique_files.append(files[0])
                        skipped_duplicates += len(files) - 1
                        logger.debug(f"跳过 {len(files) - 1} 个重复文件，MD5: {md5}")
                    else:
                        # 只有一个文件，直接添加
                        unique_files.append(files[0])
                
                if skipped_duplicates > 0:
                    logger.info(f"检测到 {skipped_duplicates} 个源重复文件，已跳过")
                    media_files = unique_files
                    progress.skipped_files += skipped_duplicates
            
            # 使用原始扫描的文件总数作为总文件数（包含被跳过的源重复文件）
            progress.total_files = original_total_files
            progress.total_size = original_total_size
            
            # 更新导入历史记录的总文件数和总大小
            if import_history_id:
                db = SessionLocal()
                try:
                    import_history = db.query(ImportHistory).filter(ImportHistory.id == import_history_id).first()
                    if import_history:
                        import_history.status = ImportStatus.PROCESSING.value
                        import_history.total_files = original_total_files
                        import_history.total_size = original_total_size
                        db.commit()
                        logger.debug(f"导入历史记录已更新，总文件数: {original_total_files}, 总大小: {original_total_size}")
                except Exception as e:
                    logger.error(f"更新导入历史记录失败: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            # 加载目标目录的 MD5 记录
            progress.status = ImportStatus.PROCESSING
            target_records = self._load_target_records(target_path)
            
            # 如果启用了跳过相册重复，预计算相册中已存在的 MD5 集合
            existing_md5s = set()
            logger.info(f"[_do_import] skip_target_duplicates={skip_target_duplicates}, target_records数量={len(target_records)}")
            if skip_target_duplicates:
                logger.info(f"开始检测相册中已存在的文件，用于跳过重复")
                # target_records 是 {md5_hash: path} 格式的字典
                for md5_hash, file_path in target_records.items():
                    if md5_hash:
                        existing_md5s.add(md5_hash)
                logger.info(f"相册中已有 {len(existing_md5s)} 个不同的MD5，前5个: {list(existing_md5s)[:5]}")
            
            # 使用线程池并行处理文件导入（保留1个核心给系统）
            max_workers = max(1, os.cpu_count() - 1)
            logger.info(f"使用 {max_workers} 个线程并行导入文件")
            
            # file_lock：保护 target_records 读写 + 路径解析 + 文件复制的原子性
            # 避免多线程并发时同一文件被重复复制（TOCTOU竞态）
            file_lock = threading.Lock()
            
            def process_file(file_path):
                # 检查取消标志
                if self._should_cancel(import_id):
                    return False
                
                # 暂停等待：若 pause_event 未 set，阻塞在此直到 resume 或 cancel
                pause_event = self.pause_events.get(import_id)
                if pause_event:
                    pause_event.wait()
                
                # 再次检查取消（resume 后可能已被取消）
                if self._should_cancel(import_id):
                    return False
                
                try:
                    # 更新当前处理的文件名（ImportProgress 内部已有 _lock，线程安全）
                    progress.update_current_file(file_path.name)
                    
                    # 如果启用了跳过相册重复，检查文件是否已存在
                    if skip_target_duplicates and existing_md5s:
                        file_md5 = self._compute_md5(file_path)
                        logger.debug(f"[_do_import] 检查文件: {file_path.name}, MD5={file_md5}, 是否在existing_md5s中={file_md5 in existing_md5s if file_md5 else 'N/A'}")
                        if file_md5 and file_md5 in existing_md5s:
                            # 文件已存在于相册中，跳过（统一计入 skipped_files）
                            file_size = file_path.stat().st_size
                            progress.skip_file(file_path, file_size)
                            logger.info(f"跳过相册重复文件: {file_path.name}, MD5={file_md5}")
                            return True
                    
                    # 执行导入逻辑（传入 file_lock 保证原子性）
                    self._import_file(file_path, target_path, target_records, progress, file_lock, import_mode)
                    return True
                except Exception as e:
                    logger.error(f"导入文件失败: {file_path} - {e}")
                    try:
                        progress.add_file(file_path, file_path.stat().st_size, success=False)
                    except Exception:
                        pass
                    return False
            
            # 并行处理文件
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有文件处理任务
                futures = [executor.submit(process_file, file_path) for file_path in media_files]
                
                # 等待所有任务完成或取消
                for future in concurrent.futures.as_completed(futures):
                    if self._should_cancel(import_id):
                        # 取消所有未完成的任务
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break
                    
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"任务执行异常: {e}")
            
            # 保存最终的 MD5 记录
            self._save_target_records(target_path, target_records)
            
            if progress.status not in (ImportStatus.CANCELLED, ImportStatus.PAUSED):
                progress.status = ImportStatus.COMPLETED
                logger.info(f"导入完成: {progress.processed_files} 个文件, 跳过 {progress.skipped_files} 个, 失败 {progress.failed_files} 个")
        
        except Exception as e:
            logger.error(f"导入出错: {e}")
            progress.status = ImportStatus.FAILED
            progress.error_message = str(e)
        
        finally:
            progress.end_time = datetime.now()
            
            # 更新导入历史记录的最终状态
            if import_history_id:
                db = SessionLocal()
                try:
                    import_history = db.query(ImportHistory).filter(ImportHistory.id == import_history_id).first()
                    if import_history:
                        import_history.status = progress.status.value
                        import_history.end_time = progress.end_time
                        import_history.imported_files = progress.processed_files
                        import_history.skipped_files = progress.skipped_files
                        import_history.failed_files = progress.failed_files
                        # ImportHistory 模型中无 error_message 字段，不写入（避免 SQLAlchemy 报错）
                        db.commit()
                        logger.info(f"导入历史记录已更新，最终状态: {progress.status.value}")
                except Exception as e:
                    logger.error(f"更新导入历史记录失败: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            # 导入完成后更新最后导入时间和最后扫描时间
            if progress.status == ImportStatus.COMPLETED:
                try:
                    from .config_manager import get_config_manager
                    config = get_config_manager()
                    config.set_last_import()
                    logger.info("最后导入时间已更新")
                    # 复用同一 config 对象更新 last_scan_time（仅在完成时才更新，防止取消/失败时漏扫）
                    src_key = f"last_scan_{hashlib.md5(str(source_path).encode()).hexdigest()[:8]}"
                    config.update_setting(src_key, datetime.now().isoformat())
                    logger.info(f"已更新源目录扫描时间: {source_path}")
                except Exception as e:
                    logger.error(f"更新最后导入/扫描时间失败: {e}")
    
    def _scan_source(self, source_path: Path, ignore_last_scan: bool = False) -> List[Path]:
        """扫描源目录，找到所有媒体文件（优化版，支持增量扫描）
        
        优化点：
        1. 使用os.scandir代替pathlib.rglob，减少系统调用
        2. 直接检查文件扩展名，避免不必要的文件类型检查
        3. 仅在必要时创建Path对象
        4. 增量扫描：只扫描最后修改时间大于最后扫描时间的目录
        
        参数：
            ignore_last_scan: 如果为True，忽略最后扫描时间，扫描所有文件
        """
        media_files = []
        source_path_str = str(source_path)
        
        # 从 JSON 配置获取最后扫描时间
        last_scan_time = None
        if not ignore_last_scan:
            try:
                from .config_manager import get_config_manager
                config = get_config_manager()
                last_scan_time_str = config.get_setting(f"last_scan_{hashlib.md5(source_path_str.encode()).hexdigest()[:8]}")
                last_scan_time = datetime.fromisoformat(last_scan_time_str) if last_scan_time_str else None
            except Exception as e:
                logger.warning(f"获取最后扫描时间失败: {e}")
                last_scan_time = None
        
        logger.info(f"开始扫描源目录: {source_path}, 最后扫描时间: {last_scan_time}, 忽略最后扫描: {ignore_last_scan}")
        
        for root, dirs, files in os.walk(source_path_str):
            root_path = Path(root)
            
            # 注意：不以目录 mtime 过滤，否则目录内新文件会被漏掉
            # 文件层面的 mtime 过滤已在下方处理
            
            # 扫描当前目录中的文件
            for file in files:
                file_lower = file.lower()
                for ext in MEDIA_FORMATS:
                    if file_lower.endswith(ext):
                        # 只在确认是媒体文件时创建Path对象
                        file_path = root_path / file
                        
                        # 检查文件是否在最后扫描后被修改（如果需要的话）
                        should_add = True
                        if not ignore_last_scan and last_scan_time:
                            try:
                                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                                should_add = file_mtime > last_scan_time
                            except Exception as e:
                                logger.debug(f"获取文件修改时间失败 {file_path}: {e}")
                                # 如果获取修改时间失败，仍然添加文件
                                should_add = True
                        
                        if should_add:
                            media_files.append(file_path)
                        
                        break
        
        # 注意：last_scan_time 不在此处更新，由 _do_import 在成功完成后更新。
        # 若在扫描阶段即更新，导入中途取消会导致下次扫描漏掉未导入的文件。
        logger.info(f"扫描完成，找到 {len(media_files)} 个媒体文件")
        return media_files
    
    def _import_file(self, file_path: Path, target_path: Path, target_records: Dict, progress: ImportProgress, file_lock: threading.Lock = None, import_mode: str = 'copy'):
        """导入单个文件
        
        file_lock 用于保护以下临界区的原子性（多线程导入时必须传入）：
          MD5 查重 → 目标路径解析 → 文件复制 → target_records 回写
        不传时退化为单线程行为（向后兼容）。
        
        import_mode: 'copy'（保留源文件）或 'move'（导入成功后删除源文件）
        """
        try:
            # 获取媒体日期
            media_date = self._get_media_date(file_path)
            if not media_date:
                # 降级到文件修改时间
                media_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # 构建目标路径：target/YYYY-MM/filename（不再创建 YYYY 层级）
            month = media_date.strftime('%Y-%m')
            month_dir = target_path / month
            
            # 创建目录（exist_ok=True，多线程安全）
            month_dir.mkdir(parents=True, exist_ok=True)
            
            # 计算源文件 MD5（锁外执行，IO密集型，不影响正确性）
            src_md5 = self._compute_md5(file_path)

            # ----------------------------------------------------------------
            # 临界区：MD5查重 + 路径解析 + records预占位
            # 必须原子完成，否则并发线程可能同时通过查重，导致重复复制
            # ----------------------------------------------------------------
            lock_ctx = file_lock if file_lock is not None else threading.Lock()
            with lock_ctx:
                # 判断是否 MD5 重复（重复文件仍复制，但加 _dup 后缀标记）
                is_dup = bool(src_md5 and src_md5 in target_records)
                conflict = FileConflict.MD5_DUPLICATE if is_dup else FileConflict.NONE

                # 构建目标路径：YYYYMMDD_HHmmss_NNN[_dup].ext
                # _build_dest_filename 内部探测序号，必须在临界区内调用（TOCTOU 安全）
                ext = file_path.suffix.lower()
                final_dest_path = self._build_dest_filename(media_date, ext, month_dir, is_dup=is_dup)

                # 预占位：立即写回 records，后续线程查重时可以看到
                # 即使文件复制尚未完成，也能防止其他线程重复处理同一 MD5
                if src_md5:
                    target_records[src_md5] = str(final_dest_path.relative_to(target_path))
            # ----------------------------------------------------------------

            # 文件复制/移动：在锁外执行，允许多线程并行 IO
            # 注意：如果此处失败，上一步的 records 预占位会导致后续认为文件已存在
            # 但这是可接受的——导入失败时用户会重试，重试时会跳过（或覆盖）
            if import_mode == 'move':
                # Move 模式：优先使用 rename（同文件系统瞬间完成），失败则退化为 copy+unlink
                try:
                    shutil.move(str(file_path), str(final_dest_path))
                    logger.debug(f"剪切模式：已移动文件 {file_path} -> {final_dest_path}")
                except OSError:
                    # 跨文件系统时 move 内部会自动退化为 copy+unlink，但某些边缘情况可能失败
                    shutil.copy2(str(file_path), str(final_dest_path))
                    file_path.unlink()
                    logger.debug(f"剪切模式：已复制并删除源文件 {file_path}")
            else:
                # Copy 模式：复制文件，保留源文件
                shutil.copy2(str(file_path), str(final_dest_path))

            # 获取文件信息（move 模式下源文件已不存在，使用目标文件）
            file_size = final_dest_path.stat().st_size
            extension = file_path.suffix.lower()
            file_type = 'video' if extension in VIDEO_FORMATS else 'photo'
            
            # 保存到数据库
            db = SessionLocal()
            try:
                # 检查文件是否已经存在于数据库中
                existing_photo = db.query(Photo).filter(Photo.path == str(final_dest_path)).first()
                if not existing_photo:
                    # 创建新的Photo对象
                    photo = Photo(
                        filename=final_dest_path.name,
                        path=str(final_dest_path),
                        size=file_size,
                        md5_hash=src_md5,
                        created_at=datetime.now(),
                        modified_at=datetime.now(),
                        media_date=media_date,
                        file_type=file_type,
                        extension=extension,
                        imported_at=datetime.now()
                    )
                    db.add(photo)
                    db.commit()
                    logger.debug(f"文件信息已保存到数据库: {final_dest_path.name}")
            except Exception as e:
                logger.error(f"保存文件信息到数据库失败: {final_dest_path} - {e}")
                db.rollback()
            finally:
                db.close()
            
            # 记录进度
            progress.add_file(final_dest_path, file_size, conflict, success=True)
            
            logger.debug(f"✓ 导入成功: {file_path.name} -> {final_dest_path.relative_to(target_path)}")
        
        except Exception as e:
            logger.error(f"导入文件失败: {file_path} - {e}")
            try:
                _err_size = file_path.stat().st_size
            except Exception:
                _err_size = 0
            progress.add_file(file_path, _err_size, success=False)
    
    def _get_media_date(self, filepath: Path) -> Optional[datetime]:
        """获取媒体文件的拍摄日期"""
        # 视频文件尝试使用FFmpeg提取创建时间
        if filepath.suffix.lower() in {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'}:
            try:
                # 使用视频处理器提取元数据
                metadata = VideoProcessor.extract_metadata(str(filepath))
                if metadata and "creation_time" in metadata:
                    return metadata["creation_time"]
                # 降级到文件修改时间
                return datetime.fromtimestamp(filepath.stat().st_mtime)
            except Exception as e:
                logger.debug(f"提取视频创建时间失败 {filepath}: {e}")
                try:
                    return datetime.fromtimestamp(filepath.stat().st_mtime)
                except OSError:
                    return None
        
        # 图片文件尝试读取 EXIF
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
        except ImportError:
            return None
        
        try:
            img = Image.open(filepath)
            exif = img._getexif()
            if not exif:
                return None
            
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag in ('DateTimeOriginal', 'DateTime') and isinstance(value, str):
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass
            return None
        except Exception as e:
            logger.debug(f"提取图片EXIF失败 {filepath}: {e}")
            return None
    
    def _compute_md5(self, filepath: Path) -> Optional[str]:
        """计算文件 MD5（委托给 utils.compute_md5）"""
        return compute_md5(filepath)
    
    def _load_target_records(self, target_path: Path) -> Dict:
        """加载目标目录的 MD5 记录（只加载属于本次目标相册的记录）"""
        target_prefix = str(target_path)
        db = SessionLocal()
        try:
            # 只加载路径在 target_path 目录下的照片，防止跨相册误判重复
            photos = db.query(Photo).filter(
                Photo.path.like(target_prefix + '%')
            ).all()
            # md5_hash 不再有 unique 约束（允许 _dup 副本），取最后写入的路径即可
            records = {}
            for photo in photos:
                if photo.md5_hash:
                    records[photo.md5_hash] = photo.path
            logger.info(f"从数据库加载了 {len(records)} 条MD5记录（相册: {target_prefix}）")
            return records
        except Exception as e:
            logger.warning(f"从数据库加载记录失败: {e}")
            # 回退到文件系统记录
            record_file = target_path / RECORD_FILENAME
            if record_file.exists():
                try:
                    with open(record_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if "records" in data:
                        logger.info(f"从文件加载了 {len(data['records'])} 条MD5记录")
                        return data["records"]
                except Exception as e:
                    logger.warning(f"读取记录文件失败: {e}")
        finally:
            db.close()
        
        return {}
    
    def _save_target_records(self, target_path: Path, records: Dict):
        """保存 MD5 记录到目标目录"""
        logger.info(f"_save_target_records 已被调用，但不再需要保存到数据库，记录已在导入时实时更新")
        
        # 保持向后兼容性，仍然保存JSON文件，但只作为备份
        record_file = target_path / RECORD_FILENAME
        data = {
            "version": "1.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "records": records,
            "source_dir": str(target_path),
            "note": "此文件仅作为备份，主要记录存储在SQLite数据库中"
        }
        
        # 重试机制：最多3次，间隔100ms
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(1, max_retries + 1):
            try:
                with open(record_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # Windows 隐藏文件
                if sys.platform == 'win32':
                    try:
                        import ctypes
                        ctypes.windll.kernel32.SetFileAttributesW(str(record_file), 2)
                    except (OSError, AttributeError):
                        pass
                
                logger.debug(f"记录文件已作为备份保存: {record_file}")
                return  # 保存成功，直接返回
            except PermissionError as e:
                if attempt < max_retries:
                    logger.warning(f"保存记录文件失败（尝试 {attempt}/{max_retries}）: {e}，{retry_delay*1000:.0f}ms 后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"保存记录文件失败（已重试 {max_retries} 次）: {e}，跳过此步骤，不影响导入流程")
            except Exception as e:
                # 其他异常不重试，直接记录警告
                logger.warning(f"保存记录文件失败: {e}，跳过此步骤，不影响导入流程")
                return
    
    def _build_dest_filename(
        self,
        media_date: datetime,
        ext: str,
        month_dir: Path,
        is_dup: bool = False
    ) -> Path:
        """生成不冲突的目标路径。

        格式：YYYYMMDD_HHmmss_NNN[_dup].ext，序号从 001 起递增。
        - is_dup=False：20240315_143022_001.jpg
        - is_dup=True ：20240315_143022_001_dup.jpg（MD5 重复文件，仍复制）

        注意：调用者必须持有 file_lock（临界区内调用），确保 TOCTOU 安全。
        """
        base = media_date.strftime('%Y%m%d_%H%M%S')
        dup_suffix = '_dup' if is_dup else ''
        counter = 1
        while True:
            name = f"{base}_{counter:03d}{dup_suffix}{ext}"
            dest = month_dir / name
            if not dest.exists():
                return dest
            counter += 1

    def _resolve_dest_path(self, dest: Path, src_md5: str, target_records: Dict) -> Tuple[Path, str]:
        """解析目标路径，处理文件冲突

        [已废弃] 此方法不再被 _import_file 调用。
        新的命名逻辑由 _build_dest_filename 负责（日期时间 + 序号机制）。
        保留方法体仅防止外部引用报错，请勿在新代码中调用。
        """
        # 检查 MD5 重复
        if src_md5 and src_md5 in target_records:
            conflict = FileConflict.MD5_DUPLICATE.value
        elif dest.exists():
            conflict = FileConflict.NAME_DUPLICATE.value
        else:
            return dest, FileConflict.NONE.value
        
        # 重命名：重复-N_原名.jpg
        counter = 1
        while True:
            new_name = f"重复-{counter}_{dest.name}"
            new_dest = dest.parent / new_name
            if not new_dest.exists():
                return new_dest, conflict
            counter += 1


# ============================================================================
# 全局导入管理器实例
# ============================================================================

_import_manager = None


def get_import_manager() -> ImportManager:
    """获取全局导入管理器实例"""
    global _import_manager
    if _import_manager is None:
        _import_manager = ImportManager()
    return _import_manager
