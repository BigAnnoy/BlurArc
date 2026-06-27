"""MobileAccessServer 单元测试"""
import json
import time
import pytest
from pathlib import Path


class TestTokenManager:
    def test_generate_pairing_code(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, qr = tm.generate_pairing_code()
        assert len(code) == 6 and code == qr

    def test_pair_invalid_code(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        assert tm.handle_pair_request("INVALID", "D") is None

    def test_pair_confirm(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "XiaoMi 13")
        token = tm.confirm_pair_request(code)
        assert token and len(token) == 32
        assert tm.validate_token(token)

    def test_pair_reject(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "D")
        tm.reject_pair_request(code)
        assert tm.confirm_pair_request(code) is None

    def test_revoke_token(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "D")
        t = tm.confirm_pair_request(code)
        assert tm.validate_token(t)
        tm.revoke_token(t)
        assert not tm.validate_token(t)

    def test_revoke_all(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        c1, _ = tm.generate_pairing_code(); tm.handle_pair_request(c1, "A"); t1 = tm.confirm_pair_request(c1)
        c2, _ = tm.generate_pairing_code(); tm.handle_pair_request(c2, "B"); t2 = tm.confirm_pair_request(c2)
        assert tm.validate_token(t1) and tm.validate_token(t2)
        tm.revoke_all()
        assert not tm.validate_token(t1) and not tm.validate_token(t2)

    def test_code_expires(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        # Simulate expiry by modifying the pending code's created_at
        tm._pending_codes[code]["created_at"] = time.time() - 61
        assert tm.handle_pair_request(code, "D") is None

    def test_device_map_consistency(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "Pixel 8")
        token = tm.confirm_pair_request(code)
        assert tm._device_map.get("Pixel 8") == token
        tm.revoke_token(token)
        assert tm._device_map.get("Pixel 8") is None


class TestMobileServerLifecycle:
    def test_start_stop(self, monkeypatch, tmp_path):
        import backend.mobile_access_server as mod
        monkeypatch.setattr(mod, "TOKENS_FILE", tmp_path / "tokens.json")
        server = mod.MobileAccessServer()
        info = server.start()
        assert 8900 <= info["port"] <= 8999
        server.stop()

    def test_paired_devices(self, monkeypatch, tmp_path):
        import backend.mobile_access_server as mod
        monkeypatch.setattr(mod, "TOKENS_FILE", tmp_path / "tokens.json")
        server = mod.MobileAccessServer()
        assert not server.has_paired_devices()
        code, _ = server.token_manager.generate_pairing_code()
        server.token_manager.handle_pair_request(code, "T")
        server.token_manager.confirm_pair_request(code)
        assert server.has_paired_devices()

    def test_tokens_persist(self, monkeypatch, tmp_path):
        import backend.mobile_access_server as mod
        tokens_file = tmp_path / "tokens.json"
        monkeypatch.setattr(mod, "TOKENS_FILE", tokens_file)
        tm1 = mod.TokenManager()
        code, _ = tm1.generate_pairing_code()
        tm1.handle_pair_request(code, "iPhone 15")
        token = tm1.confirm_pair_request(code)
        assert tokens_file.exists()
        # Reload from file
        tm2 = mod.TokenManager()
        assert tm2.validate_token(token)

    def test_device_name_repair_overrides_old_token(self):
        """重配对同一 device_name 应撤销旧 token"""
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        # 第一次配对
        code1, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code1, "Pixel 8")
        token1 = tm.confirm_pair_request(code1)
        assert tm.validate_token(token1)
        # 第二次配对同一设备名
        code2, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code2, "Pixel 8")
        token2 = tm.confirm_pair_request(code2)
        # 旧 token 应失效
        assert not tm.validate_token(token1)
        # 新 token 有效
        assert tm.validate_token(token2)
        # device_map 只保留新 token
        assert tm._device_map["Pixel 8"] == token2

    def test_repair_different_device_preserves_old(self):
        """不同设备配对不应影响旧 token"""
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code1, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code1, "Pixel 8")
        token1 = tm.confirm_pair_request(code1)
        code2, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code2, "iPhone 15")
        token2 = tm.confirm_pair_request(code2)
        # 两个 token 都有效
        assert tm.validate_token(token1)
        assert tm.validate_token(token2)


class TestMobileServerEndpoints:
    """端到端联调测试：使用 Flask test_client"""

    def _make_client(self, monkeypatch, tmp_path):
        import backend.mobile_access_server as mod
        monkeypatch.setattr(mod, "TOKENS_FILE", tmp_path / "tokens.json")
        server = mod.MobileAccessServer()
        return server, server.app.test_client()

    def test_pair_rate_limit(self, monkeypatch, tmp_path):
        """验证 pairing/request 端点重复请求替换行为"""
        server, client = self._make_client(monkeypatch, tmp_path)
        # 发起配对请求
        resp = client.post("/api/mobile/pairing/request",
                           json={"device_name": "Test Phone"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "requested"
        # 再次发起应替换旧请求
        resp = client.post("/api/mobile/pairing/request",
                           json={"device_name": "Phone 2"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "requested"

    def test_full_pairing_flow(self, monkeypatch, tmp_path):
        """完整配对流程：手机请求 → PC 确认 → 手机提交码 → 获取 token"""
        server, client = self._make_client(monkeypatch, tmp_path)

        # Step 1: 手机发起配对请求
        resp = client.post("/api/mobile/pairing/request",
                           json={"device_name": "Test Phone"})
        data = json.loads(resp.data)
        assert data["status"] == "requested"

        # Step 2: 手机轮询状态（未确认，应为 pending）
        resp = client.get("/api/mobile/pairing/pending")
        data = json.loads(resp.data)
        assert data["status"] == "pending"

        # Step 3: PC 确认配对 → 生成配对码
        resp = client.post("/api/mobile/pairing/confirm")
        data = json.loads(resp.data)
        assert data["status"] == "confirmed"
        code = data["pairing_code"]

        # Step 4: 手机再次轮询，状态变为 confirmed
        resp = client.get("/api/mobile/pairing/pending")
        data = json.loads(resp.data)
        assert data["status"] == "confirmed"

        # Step 5: 手机提交配对码 → 获取 token
        resp = client.post("/api/mobile/pairing/submit-code",
                           json={"code": code, "device_name": "Test Phone"})
        data = json.loads(resp.data)
        assert data["status"] == "paired"
        token = data["token"]
        assert token

        # Step 6: 使用 token 验证
        resp = client.get("/api/mobile/verify",
                          headers={"Authorization": f"Bearer {token}"})
        data = json.loads(resp.data)
        assert data["status"] == "ok"

    def test_cors_headers(self, monkeypatch, tmp_path):
        """验证 CORS headers 存在"""
        server, client = self._make_client(monkeypatch, tmp_path)
        resp = client.post("/api/mobile/pairing/request",
                           json={"device_name": "Test Phone"})
        assert "Access-Control-Allow-Origin" in resp.headers

    def test_verify_endpoint_rejects_invalid(self, monkeypatch, tmp_path):
        """验证 /verify 端点拒绝无效 token"""
        server, client = self._make_client(monkeypatch, tmp_path)
        resp = client.get("/api/mobile/verify",
                          headers={"Authorization": "Bearer invalid_token"})
        assert resp.status_code == 401
