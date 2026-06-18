"""PhoneUploadServer 单元测试"""
import json
import os
import struct
import time
import pytest
from pathlib import Path
from backend.phone_upload_server import (
    PhoneUploadServer, UploadSession, UPLOAD_ROOT,
    MAGIC_BYTES_WHITELIST, PIN_LENGTH,
)


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
        # PIN 码应在返回中
        assert "pin" in info
        assert len(info["pin"]) == PIN_LENGTH
        assert info["pin"].isdigit()
        # URL 应包含 PIN 参数
        assert "pin=" in info["upload_url"]
        server.stop()
        assert server._session is not None
        assert not server._session.is_active
        # 停止后 PIN 应被清除
        assert server._pin is None

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

    def test_pin_generated_on_start(self, monkeypatch, tmp_path):
        """每次启动生成 PIN 码"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")
        server = PhoneUploadServer()
        assert server._pin is None
        info1 = server.start()
        assert server._pin is not None
        assert server._pin == info1["pin"]
        server.stop()
        assert server._pin is None
        # 再次启动生成新 PIN
        info2 = server.start()
        assert server._pin is not None
        assert server._pin == info2["pin"]
        server.stop()

    def test_pin_cleared_on_stop(self, monkeypatch, tmp_path):
        """停止后 PIN 被清除，防止 reuse"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")
        server = PhoneUploadServer()
        server.start()
        assert server._pin is not None
        server.stop()
        assert server._pin is None


class TestMagicBytesValidation:
    """测试文件 magic bytes 校验"""

    def test_jpeg_magic_bytes(self, tmp_path):
        """JPEG 文件头部 \xff\xd8\xff 应被识别"""
        f = tmp_path / "test.jpg"
        f.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)
        assert PhoneUploadServer._validate_magic_bytes(f) is True

    def test_png_magic_bytes(self, tmp_path):
        """PNG 文件头部应被识别"""
        f = tmp_path / "test.png"
        f.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        assert PhoneUploadServer._validate_magic_bytes(f) is True

    def test_mp4_ftyp_magic_bytes(self, tmp_path):
        """MP4 ftyp 在 offset 4 应被识别"""
        f = tmp_path / "test.mp4"
        # MP4: 4-byte size + "ftyp" + brand
        f.write_bytes(struct.pack('>I', 32) + b'ftypisom' + b'\x00' * 100)
        assert PhoneUploadServer._validate_magic_bytes(f) is True

    def test_invalid_file_rejected(self, tmp_path):
        """恶意伪装文件（.jpg.exe）应被拒绝"""
        f = tmp_path / "malware.jpg"
        f.write_bytes(b'MZ\x90\x00' + b'\x00' * 100)  # PE executable header
        assert PhoneUploadServer._validate_magic_bytes(f) is False

    def test_empty_file_rejected(self, tmp_path):
        """空文件应被拒绝"""
        f = tmp_path / "empty.jpg"
        f.write_bytes(b'')
        assert PhoneUploadServer._validate_magic_bytes(f) is False

    def test_gif_magic_bytes(self, tmp_path):
        """GIF 文件头部应被识别"""
        f = tmp_path / "test.gif"
        f.write_bytes(b'GIF89a' + b'\x00' * 100)
        assert PhoneUploadServer._validate_magic_bytes(f) is True

    def test_webm_magic_bytes(self, tmp_path):
        """MKV/WebM 文件头部应被识别"""
        f = tmp_path / "test.webm"
        f.write_bytes(b'\x1a\x45\xdf\xa3' + b'\x00' * 100)
        assert PhoneUploadServer._validate_magic_bytes(f) is True


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

    def test_has_incomplete_ignores_zero_files(self, monkeypatch, tmp_path):
        """测试 0 文件的 incomplete 会话不被视为可恢复"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        mod.SESSIONS_FILE.write_text(json.dumps({
            "sessions": [{"id": "abc", "upload_dir": "foo", "created_at": 0,
                          "file_count": 0, "total_bytes": 0, "status": "incomplete"}]
        }), encoding="utf-8")

        server = PhoneUploadServer()
        result = server.has_incomplete_session()
        assert result is None
