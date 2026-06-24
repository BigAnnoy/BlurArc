"""
移动接入 API 端点测试

实际 api_server.py 实现：
- GET  /api/mobile/status                 移动服务状态
- POST /api/mobile/enable                 启动移动服务
- POST /api/mobile/disable                停止移动服务
- GET  /api/mobile/qr                     配对二维码
- GET  /api/mobile/pending-request        待配对请求
- POST /api/mobile/confirm-pairing        确认/拒绝配对
- GET  /api/mobile/devices                已配对设备列表
- POST /api/mobile/revoke                 撤销设备 token
- POST /api/mobile/revoke-all             撤销所有 token
- GET  /api/mobile/pending-flutter-uploads        Flutter 上传通知
- POST /api/mobile/pending-flutter-uploads/clear  清除上传通知
- POST /api/mobile/pairing/{start,stop,...}       配对模式

注意：plan 中的 /api/mobile/pair、/api/mobile/upload、/api/mobile/photos 端点不存在。
"""
from unittest.mock import patch, MagicMock
import pytest


class TestMobileStatusEndpoint:
    """GET /api/mobile/status"""

    def test_status_not_running(self, client):
        """服务未启动时的状态"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.port = None
            mock_server._local_ip = None
            mock_server.token_manager = MagicMock(get_paired_devices=MagicMock(return_value=[]))
            mock_gms.return_value = mock_server

            with patch("backend.api_server.get_config_manager") as mock_gcm:
                mock_cfg = MagicMock()
                mock_cfg.get_setting.return_value = False
                mock_gcm.return_value = mock_cfg

                resp = client.get("/api/mobile/status")
        assert resp.status_code == 200
        body = resp.json
        assert "enabled" in body
        assert "running" in body

    def test_status_running(self, client):
        """服务运行时状态"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.port = 8900
            mock_server._local_ip = "192.168.1.10"
            mock_server.token_manager = MagicMock(get_paired_devices=MagicMock(return_value=[{"device_name": "iPhone", "token": "abc123", "paired_at": "2024-01-01"}]))
            mock_gms.return_value = mock_server

            with patch("backend.api_server.get_config_manager") as mock_gcm:
                mock_cfg = MagicMock()
                mock_cfg.get_setting.return_value = True
                mock_gcm.return_value = mock_cfg

                resp = client.get("/api/mobile/status")
        assert resp.status_code == 200
        body = resp.json
        assert body["enabled"] is True
        assert body["running"] is True
        assert body["port"] == 8900
        assert body["paired_count"] == 1


class TestMobileEnableDisableEndpoint:
    """POST /api/mobile/{enable,disable}"""

    def test_enable(self, client):
        """启动移动服务"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.start.return_value = {
                "port": 8900,
                "ip": "192.168.1.10",
                "qr_data": "test_qr_data",
            }
            mock_gms.return_value = mock_server

            with patch("backend.api_server.get_config_manager") as mock_gcm:
                mock_gcm.return_value = MagicMock()

                resp = client.post("/api/mobile/enable")
        assert resp.status_code == 200
        body = resp.json
        assert body["status"] == "enabled"
        assert "port" in body

    def test_disable(self, client):
        """停止移动服务"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_gms.return_value = mock_server

            with patch("backend.api_server.get_config_manager") as mock_gcm:
                mock_gcm.return_value = MagicMock()

                resp = client.post("/api/mobile/disable")
        assert resp.status_code == 200
        assert resp.json["status"] == "disabled"


class TestMobilePairingEndpoints:
    """配对相关端点"""

    def test_pending_request_none(self, client):
        """无待配对请求"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.get_pending_pair_code.return_value = None
            mock_gms.return_value = mock_server
            resp = client.get("/api/mobile/pending-request")
        assert resp.status_code == 200
        assert resp.json["hasPending"] is False

    def test_pending_request_with_code(self, client):
        """有待配对请求"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.get_pending_pair_code.return_value = "1234"
            mock_server.token_manager.get_pending_device_name.return_value = "iPhone-Test"
            mock_gms.return_value = mock_server
            resp = client.get("/api/mobile/pending-request")
        assert resp.status_code == 200
        body = resp.json
        assert body["hasPending"] is True
        assert body["pairing_code"] == "1234"
        assert body["device_name"] == "iPhone-Test"

    def test_confirm_pairing_accept(self, client):
        """确认配对 accept"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.confirm_pair_request.return_value = "device_token_xyz"
            mock_gms.return_value = mock_server
            resp = client.post(
                "/api/mobile/confirm-pairing",
                json={"pairing_code": "1234", "action": "accept"},
            )
        assert resp.status_code == 200
        assert resp.json["status"] == "accepted"

    def test_confirm_pairing_reject(self, client):
        """拒绝配对 reject"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_gms.return_value = mock_server
            resp = client.post(
                "/api/mobile/confirm-pairing",
                json={"pairing_code": "1234", "action": "reject"},
            )
        assert resp.status_code == 200
        assert resp.json["status"] == "rejected"

    def test_confirm_pairing_invalid_code(self, client):
        """无效配对码"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.confirm_pair_request.return_value = None
            mock_gms.return_value = mock_server
            resp = client.post(
                "/api/mobile/confirm-pairing",
                json={"pairing_code": "9999", "action": "accept"},
            )
        assert resp.status_code == 400


class TestMobileDevicesEndpoint:
    """GET /api/mobile/devices + revoke"""

    def test_list_devices(self, client):
        """获取已配对设备列表"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.get_paired_devices.return_value = [
                {"device_name": "iPhone-1", "paired_at": "2024-01-01", "token": "tok_aaaa1111"},
            ]
            mock_gms.return_value = mock_server
            resp = client.get("/api/mobile/devices")
        assert resp.status_code == 200
        body = resp.json
        assert "devices" in body
        assert len(body["devices"]) == 1
        assert body["devices"][0]["device_name"] == "iPhone-1"

    def test_revoke_device(self, client):
        """撤销单个设备"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.revoke_token.return_value = True
            mock_gms.return_value = mock_server
            resp = client.post(
                "/api/mobile/revoke",
                json={"token": "tok_aaaa1111"},
            )
        assert resp.status_code == 200
        assert resp.json["status"] == "revoked"

    def test_revoke_missing_token(self, client):
        """缺 token 应返回 400"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_gms.return_value = MagicMock()
            resp = client.post("/api/mobile/revoke", json={})
        assert resp.status_code == 400

    def test_revoke_nonexistent_token(self, client):
        """撤销不存在的 token"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.token_manager.revoke_token.return_value = False
            mock_gms.return_value = mock_server
            resp = client.post(
                "/api/mobile/revoke",
                json={"token": "tok_does_not_exist"},
            )
        assert resp.status_code == 404

    def test_revoke_all(self, client):
        """撤销所有设备"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_gms.return_value = mock_server
            resp = client.post("/api/mobile/revoke-all")
        assert resp.status_code == 200
        assert resp.json["status"] == "revoked_all"


class TestFlutterUploadsEndpoints:
    """GET /api/mobile/pending-flutter-uploads + clear"""

    def test_list_pending_uploads_empty(self, client):
        """无 Flutter 上传通知"""
        resp = client.get("/api/mobile/pending-flutter-uploads")
        assert resp.status_code == 200
        assert resp.json == {"sessions": []}

    def test_clear_pending_upload(self, client):
        """清除指定的 Flutter 上传通知"""
        resp = client.post(
            "/api/mobile/pending-flutter-uploads/clear",
            json={"upload_dir": "session_xyz"},
        )
        assert resp.status_code == 200
        assert resp.json["status"] == "cleared"


class TestMobilePairingModeEndpoints:
    """POST /api/mobile/pairing/{start,stop,cancel}"""

    def test_pairing_start(self, client):
        """开启配对模式"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server.start_pairing_mode.return_value = {
                "status": "started",
                "pairing_code": "5678",
                "expires_in": 120,
            }
            mock_gms.return_value = mock_server
            resp = client.post("/api/mobile/pairing/start")
        assert resp.status_code == 200
        body = resp.json
        assert body["status"] == "started"
        assert "pairing_code" in body

    def test_pairing_stop(self, client):
        """停止配对模式"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_gms.return_value = mock_server
            resp = client.post("/api/mobile/pairing/stop")
        assert resp.status_code == 200
        assert resp.json["status"] == "stopped"

    def test_pairing_pending_none(self, client):
        """无待配对请求"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_server._pairing.get_pending.return_value = None
            mock_gms.return_value = mock_server
            resp = client.get("/api/mobile/pairing/pending")
        assert resp.status_code == 200
        assert resp.json["status"] == "none"

    def test_pairing_pending_exists(self, client):
        """有待配对请求"""
        with patch("backend.api_server._get_mobile_server") as mock_gms:
            mock_server = MagicMock()
            mock_pending = MagicMock()
            mock_pending.device_name = "iPhone-2"
            mock_pending.requested_at = "2024-01-01T00:00:00"
            mock_server._pairing.get_pending.return_value = mock_pending
            mock_gms.return_value = mock_server
            resp = client.get("/api/mobile/pairing/pending")
        assert resp.status_code == 200
        body = resp.json
        assert body["status"] == "pending"
        assert body["device_name"] == "iPhone-2"
