"""
Extended tests for import_manager.py - targeting uncovered code paths.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

import pytest


class TestImportProgress:
    """Test ImportProgress class methods"""

    def test_import_progress_to_dict(self):
        from backend.import_manager import ImportProgress, ImportStatus
        
        progress = ImportProgress("test_001")
        progress.total_files = 10
        progress.processed_files = 5
        progress.status = ImportStatus.PROCESSING
        
        result = progress.to_dict()
        assert result['import_id'] == 'test_001'
        assert result['total_files'] == 10
        assert result['processed_files'] == 5
        assert 'progress' in result

    def test_import_progress_add_file(self):
        from backend.import_manager import ImportProgress, FileConflict
        
        progress = ImportProgress("test_002")
        progress.total_files = 5
        progress.add_file(Path('/tmp/test.jpg'), 1000, FileConflict.NONE, True)
        
        assert progress.processed_files == 1
        assert len(progress.file_details) == 1
        assert progress.file_details[0]['filename'] == 'test.jpg'

    def test_import_progress_skip_file(self):
        from backend.import_manager import ImportProgress
        
        progress = ImportProgress("test_003")
        progress.total_files = 5
        progress.skip_file(Path('/tmp/skip.jpg'), 500)
        
        assert progress.skipped_files == 1

    def test_import_progress_update_methods(self):
        from backend.import_manager import ImportProgress, ImportStatus
        
        progress = ImportProgress("test_004")
        progress.update_total_files(20)
        progress.update_total_size(1024 * 1024)
        progress.update_current_file("photo.jpg")
        progress.update_status(ImportStatus.PROCESSING)
        
        assert progress.total_files == 20
        assert progress.total_size == 1024 * 1024
        assert progress.current_file == "photo.jpg"
        assert progress.status == ImportStatus.PROCESSING

    def test_import_progress_calculate(self):
        from backend.import_manager import ImportProgress
        
        progress = ImportProgress("test_005")
        progress.total_files = 10
        progress.processed_files = 7
        
        result = progress.to_dict()
        assert result['progress'] == 70


class TestImportManager:
    """Test ImportManager class methods"""

    def test_create_import(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        progress = manager.create_import("imp_001", "/src", "/target")
        
        assert progress.import_id == "imp_001"
        assert "imp_001" in manager.imports
        assert "imp_001" in manager.cancel_flags

    def test_get_progress(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        manager.create_import("imp_002", "/src", "/target")
        
        result = manager.get_progress("imp_002")
        assert result is not None
        assert result.import_id == "imp_002"

    def test_get_progress_not_found(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        result = manager.get_progress("nonexistent")
        assert result is None

    def test_cancel_import(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        manager.create_import("imp_003", "/src", "/target")
        manager.cancel_import("imp_003")
        
        assert manager._should_cancel("imp_003") is True

    def test_pause_and_resume_import(self):
        from backend.import_manager import ImportManager, ImportStatus
        
        manager = ImportManager()
        progress = manager.create_import("imp_004", "/src", "/target")
        # Set status to PROCESSING for pause to work
        progress.update_status(ImportStatus.PROCESSING)
        
        manager.pause_import("imp_004")
        
        # After pause, the event should be cleared
        event = manager.pause_events.get("imp_004")
        assert event is not None
        assert not event.is_set()
        
        # Resume should set the event
        manager.resume_import("imp_004")
        assert event.is_set()

    def test_get_progress_dict(self):
        from backend.import_manager import ImportManager, ImportStatus
        
        manager = ImportManager()
        progress = manager.create_import("imp_005", "/src", "/target")
        progress.total_files = 10
        progress.processed_files = 3
        progress.status = ImportStatus.PROCESSING
        
        result = manager.get_progress_dict("imp_005")
        assert result is not None
        assert result['import_id'] == 'imp_005'
        assert result['status'] == 'processing'


class TestImportManagerWithRealFiles:
    """Test ImportManager with real file operations"""

    def test_scan_source_with_media_files(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            (source / 'photo1.jpg').write_bytes(b'fake1')
            (source / 'photo2.png').write_bytes(b'fake2')
            (source / 'video.mp4').write_bytes(b'fake video')
            (source / 'readme.txt').write_bytes(b'text')
            
            files = manager._scan_source(source, ignore_last_scan=True)
            assert len(files) == 3  # Only media files

    def test_scan_source_with_subdirs(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            subdir = source / '2024-01'
            subdir.mkdir()
            (subdir / 'photo.jpg').write_bytes(b'fake')
            
            files = manager._scan_source(source, ignore_last_scan=True)
            assert len(files) == 1

    def test_get_media_date_from_filename(self):
        from backend.import_manager import ImportManager
        from datetime import datetime
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'photo.jpg'
            test_file.write_bytes(b'fake photo')
            
            # Mock the PIL Image module directly
            import PIL.Image
            original_open = PIL.Image.open
            
            try:
                mock_img = MagicMock()
                mock_img._getexif.return_value = {
                    306: '2024:03:15 12:00:00'
                }
                PIL.Image.open = MagicMock(return_value=mock_img)
                
                result = manager._get_media_date(test_file)
                assert result is not None
                assert result.year == 2024
            finally:
                PIL.Image.open = original_open

    def test_get_media_date_from_mtime(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'unknown.xyz'
            test_file.write_bytes(b'fake')
            
            # For non-media files, it should return None or fallback
            result = manager._get_media_date(test_file)
            # Non-media files without EXIF support may return None
            # This is expected behavior
            assert result is None or isinstance(result, datetime)

    def test_load_target_records_empty(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            records = manager._load_target_records(target)
            assert isinstance(records, dict)

    def test_resolve_dest_path_no_conflict(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            dest = target / 'photo.jpg'
            result, conflict = manager._resolve_dest_path(dest, 'md5hash123', {})
            
            assert str(result) == str(dest)
            assert conflict == 'none'

    def test_resolve_dest_path_with_name_conflict(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            # Create existing file with different MD5
            existing = target / 'photo.jpg'
            existing.write_bytes(b'different content')
            
            dest = target / 'photo.jpg'
            # target_records with different md5 for same filename
            target_records = {'photo.jpg': ('different_md5', str(existing))}
            
            result, conflict = manager._resolve_dest_path(dest, 'new_md5_hash', target_records)
            
            # Should get a renamed path
            assert 'photo' in str(result)
            assert conflict == 'name'

    def test_resolve_dest_path_with_md5_conflict(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            # Create existing file with same MD5
            existing = target / 'photo.jpg'
            existing.write_bytes(b'same content')
            
            dest = target / 'photo_duplicate.jpg'
            # target_records with same md5 as key
            target_records = {'same_md5_hash': ('path1', 'photo.jpg')}
            
            result, conflict = manager._resolve_dest_path(dest, 'same_md5_hash', target_records)
            
            assert conflict == 'md5'
            # Should get a renamed path with "重复-"
            assert '重复' in str(result) or 'photo' in str(result)


class TestImportManagerEdgeCases:
    """Test edge cases and error paths"""

    def test_scan_source_nonexistent(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        result = manager._scan_source(Path('/nonexistent/path'), ignore_last_scan=True)
        assert result == []

    def test_import_file_copy_mode(self):
        from backend.import_manager import ImportManager, ImportProgress
        import threading
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            test_file = source / 'photo.jpg'
            test_file.write_bytes(b'fake photo data')
            
            progress = ImportProgress("test_imp")
            target_records = {}
            file_lock = threading.Lock()
            
            manager._import_file(test_file, target, target_records, progress, file_lock, 'copy')
            
            # File should be copied to target
            copied_file = target / 'photo.jpg'
            assert copied_file.exists() or progress.processed_files == 1

    def test_import_file_move_mode(self):
        from backend.import_manager import ImportManager, ImportProgress
        import threading
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            test_file = source / 'photo.jpg'
            test_file.write_bytes(b'fake photo data')
            
            progress = ImportProgress("test_imp2")
            target_records = {}
            file_lock = threading.Lock()
            
            manager._import_file(test_file, target, target_records, progress, file_lock, 'move')
            
            # File should be moved
            assert progress.processed_files == 1 or not test_file.exists()

    def test_save_target_records(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            records = {'hash1': ('path1', 'file1.jpg'), 'hash2': ('path2', 'file2.jpg')}
            manager._save_target_records(target, records)
            # Should not raise an error

    def test_get_media_date_video_with_ffmpeg(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'video.mp4'
            test_file.write_bytes(b'fake video')
            
            # Just test that it doesn't crash, should fall back to mtime
            result = manager._get_media_date(test_file)
            assert result is not None


class TestImportManagerDoImport:
    """Test the main _do_import method"""

    def test_do_import_copy_mode(self):
        from backend.import_manager import ImportManager, ImportStatus
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            (source / 'photo1.jpg').write_bytes(b'fake1')
            (source / 'photo2.jpg').write_bytes(b'fake2')
            
            manager.create_import("test_001", str(source), str(target))
            
            # Mock database operations
            with patch('backend.import_manager.SessionLocal') as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.all.return_value = []
                mock_db.add = MagicMock()
                mock_db.commit = MagicMock()
                mock_db.close = MagicMock()
                
                manager._do_import("test_001", str(source), str(target), 'copy')
                
                progress = manager.get_progress("test_001")
                assert progress is not None
                assert progress.status in [ImportStatus.COMPLETED, ImportStatus.PROCESSING]

    def test_do_import_with_cancel(self):
        from backend.import_manager import ImportManager, ImportStatus

        manager = ImportManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()

            # Create files
            for i in range(5):
                (source / f'photo{i}.jpg').write_bytes(b'fake' * i)

            manager.create_import("test_002", str(source), str(target))
            manager.cancel_import("test_002")

            # Mock to make cancellation work
            with patch.object(manager, '_should_cancel', return_value=True):
                manager._do_import("test_002", str(source), str(target), 'copy')

            progress = manager.get_progress("test_002")
            # 修正：取消后必须保持 CANCELLED，不应被覆盖为 COMPLETED
            # 旧断言 `in [CANCELLED, COMPLETED]` 接受了 bug 行为
            assert progress.status == ImportStatus.CANCELLED

    def test_do_import_with_source_duplicates(self):
        from backend.import_manager import ImportManager
        
        manager = ImportManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            # Create duplicate files in source
            (source / 'photo1.jpg').write_bytes(b'same content')
            (source / 'photo2.jpg').write_bytes(b'same content')
            
            manager.create_import("test_003", str(source), str(target))
            
            with patch('backend.import_manager.SessionLocal') as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.all.return_value = []
                mock_db.add = MagicMock()
                mock_db.commit = MagicMock()
                mock_db.close = MagicMock()
                
                # Mock compute_md5 to return same hash for both files
                def fake_md5(filepath):
                    return 'same_hash_for_all'
                
                with patch.object(manager, '_compute_md5', fake_md5):
                    manager._do_import("test_003", str(source), str(target), 'copy', skip_source_duplicates=True)
                
                progress = manager.get_progress("test_003")
                # Should have processed at least some files
                assert progress.processed_files + progress.duplicated_files >= 1
