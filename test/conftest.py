"""
pytest fixtures - 测试配置和共享fixtures
"""

import importlib.metadata
import werkzeug

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = importlib.metadata.version('werkzeug')

import pytest
import tempfile
import shutil
from pathlib import Path
from backend.database import Base, engine, SessionLocal


@pytest.fixture(scope="function")
def temp_dir():
    """创建临时目录，测试后自动清理"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话，测试后自动回滚"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
        # 清理所有表数据（保留表结构）
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@pytest.fixture
def app():
    """Flask应用测试fixture"""
    from backend.api_server import app as flask_app
    flask_app.config['TESTING'] = True
    yield flask_app


@pytest.fixture
def client(app):
    """Flask测试客户端fixture"""
    return app.test_client()
