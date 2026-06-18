"""PhoneUploadServer 单元测试"""
import json
import time
import pytest
from pathlib import Path
from backend.phone_upload_server import PhoneUploadServer, UploadSession, UPLOAD_ROOT


class TestUploadSession:
    def test_init_creates_unique_id(self):
        s1 = UploadSession()
        s2 = UploadSession()
        assert s1.session_id != s2.session_id

    def test_to_dict_empty(self):
        s = UploadSession()
        d = s.to_dict()
        assert d["total_files"] == 0
        assert d["completed_files"] == 0
        assert d["files"] == []

    def test_to_dict_with_files(self, tmp_path):
        s = UploadSession()
        s.upload_dir = tmp_path
        s.files = [
            __import__("backend.phone_upload_server", fromlist=["UploadedFile"]).UploadedFile(
                original_name="test.jpg", saved_path=str(tmp_path / "test.jpg"),
                size=1000, mime_type="image/jpeg", uploaded_at=time.time(),
            )
        ]
        s.done_count = 1
        d = s.to_dict()
        assert d["total_files"] == 1
        assert d["completed_files"] == 1


class TestPhoneUploadServerLifecycle:
    def test_start_stop(self, monkeypatch, tmp_path):
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")
        server = PhoneUploadServer()
        info = server.start()
        assert "port" in info
        assert "local_ip" in info
        assert "upload_url" in info
        assert info["port"] >= 9800
        assert info["port"] <= 9900
        server.stop()
        assert server._session is not None
        assert not server._session.is_active

    def test_get_qr_png(self, monkeypatch, tmp_path):
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")
        server = PhoneUploadServer()
        server.start()
        png = server.get_qr_png()
        assert isinstance(png, bytes)
        assert len(png) > 0
        # PNG 文件头
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        server.stop()


class TestSessionPersistence:
    def test_write_and_load_sessions(self, monkeypatch, tmp_path):
        """测试 sessions.json 的写入和读取"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        server = PhoneUploadServer()
        server.port = 9800
        server._session = UploadSession("test123")
        server._session.upload_dir = tmp_path / "test_session"
        server._session.upload_dir.mkdir(parents=True, exist_ok=True)
        server._write_sessions_json()

        sessions = server._load_sessions_json()
        assert len(sessions) == 1
        assert sessions[0]["id"] == "test123"

    def test_has_incomplete_session(self, monkeypatch, tmp_path):
        """测试检测未完成会话"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        mod.SESSIONS_FILE.write_text(json.dumps({
            "sessions": [{"id": "abc", "upload_dir": "foo", "created_at": 0,
                          "file_count": 3, "total_bytes": 100, "status": "incomplete"}]
        }), encoding="utf-8")

        server = PhoneUploadServer()
        result = server.has_incomplete_session()
        assert result is not None
        assert result["id"] == "abc"

    def test_no_incomplete_when_all_completed(self, monkeypatch, tmp_path):
        """测试全部完成时不返回 incomplete"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        mod.SESSIONS_FILE.write_text(json.dumps({
            "sessions": [{"id": "abc", "upload_dir": "foo", "created_at": 0,
                          "file_count": 3, "total_bytes": 100, "status": "completed"}]
        }), encoding="utf-8")

        server = PhoneUploadServer()
        result = server.has_incomplete_session()
        assert result is None
