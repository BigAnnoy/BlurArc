"""
ConfigManager 单元测试
测试配置管理模块的所有公共 API 方法
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import unittest
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config_manager import ConfigManager
from backend.database import SessionLocal, Setting, Photo, ImportHistory, Base, engine


class TestConfigManager(unittest.TestCase):
    """ConfigManager 单元测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录作为测试配置目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"
        # 确保数据库表已创建（_rebuild_md5_index_for_album 需要访问 photos 等表）
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        """测试后的清理工作"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # 清空数据库中的所有表数据
        db = SessionLocal()
        try:
            # 删除所有数据，按依赖顺序删除
            db.query(ImportHistory).delete()
            db.query(Photo).delete()
            db.query(Setting).delete()
            db.commit()
        except Exception as e:
            print(f"清理测试数据失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _create_config_manager(self):
        """创建一个带有模拟属性的 ConfigManager 实例"""
        # 通过构造参数注入路径，避免测试写入用户真实的 Documents/BlurArc 目录
        return ConfigManager(
            config_dir=Path(self.temp_dir),
            config_file=self.config_file,
        )
    
    def test_initialization(self):
        """测试初始化配置"""
        # 通过构造参数注入路径，避免写入用户真实 Documents/BlurArc 目录
        config_manager = ConfigManager(
            config_dir=Path(self.temp_dir),
            config_file=self.config_file,
        )

        # 重置为默认配置（ConfigManager 为全局单例，可能被其他测试污染）
        config_manager.reset_config()

        # 验证默认配置
        default_config = config_manager._default_config()
        self.assertEqual(config_manager.config, default_config)

        # 验证配置目录被创建
        self.assertTrue(Path(self.temp_dir).exists())

        # 调用一个会保存配置的方法，验证配置文件被创建
        with tempfile.TemporaryDirectory() as temp_album_dir:
            config_manager.set_album_path(temp_album_dir)
            self.assertTrue(self.config_file.exists())
    
    def test_is_first_run(self):
        """测试首次运行检测"""
        config_manager = self._create_config_manager()
        
        # 新创建的配置管理器应该是首次运行
        self.assertTrue(config_manager.is_first_run())
        
        # 设置相册路径后，不再是首次运行
        with tempfile.TemporaryDirectory() as temp_album_dir:
            config_manager.set_album_path(temp_album_dir)
            self.assertFalse(config_manager.is_first_run())
    
    def test_set_album_path_valid(self):
        """测试设置有效的相册路径"""
        config_manager = self._create_config_manager()
        
        with tempfile.TemporaryDirectory() as temp_album_dir:
            # 设置相册路径应该成功
            result = config_manager.set_album_path(temp_album_dir)
            self.assertTrue(result)
            
            # 验证相册路径被正确设置
            expected_path = str(Path(temp_album_dir).absolute())
            self.assertEqual(config_manager.get_album_path(), expected_path)
            
            # 验证 created_at 被设置
            self.assertIsNotNone(config_manager.config.get("created_at"))
    
    def test_set_album_path_invalid_nonexistent(self):
        """测试设置不存在的相册路径"""
        config_manager = self._create_config_manager()
        
        # 设置不存在的路径应该失败
        nonexistent_path = str(Path(self.temp_dir) / "nonexistent")
        result = config_manager.set_album_path(nonexistent_path)
        self.assertFalse(result)
    
    def test_set_album_path_invalid_not_dir(self):
        """测试设置不是目录的相册路径"""
        config_manager = self._create_config_manager()
        
        # 创建一个临时文件（不是目录）
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # 设置文件路径作为相册路径应该失败
            result = config_manager.set_album_path(temp_file_path)
            self.assertFalse(result)
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def test_get_album_path(self):
        """测试获取相册路径"""
        config_manager = self._create_config_manager()
        
        # 初始时相册路径应该为 None
        self.assertIsNone(config_manager.get_album_path())
        
        # 设置相册路径后，应该返回正确的路径
        with tempfile.TemporaryDirectory() as temp_album_dir:
            config_manager.set_album_path(temp_album_dir)
            expected_path = str(Path(temp_album_dir).absolute())
            self.assertEqual(config_manager.get_album_path(), expected_path)
    
    def test_get_album_path_obj(self):
        """测试获取相册路径对象"""
        config_manager = self._create_config_manager()
        
        # 初始时相册路径对象应该为 None
        self.assertIsNone(config_manager.get_album_path_obj())
        
        # 设置相册路径后，应该返回正确的 Path 对象
        with tempfile.TemporaryDirectory() as temp_album_dir:
            config_manager.set_album_path(temp_album_dir)
            album_path_obj = config_manager.get_album_path_obj()
            self.assertIsInstance(album_path_obj, Path)
            self.assertEqual(str(album_path_obj.absolute()), str(Path(temp_album_dir).absolute()))
    
    def test_set_last_import(self):
        """测试更新最后导入时间"""
        config_manager = self._create_config_manager()
        
        # 设置自定义时间戳
        custom_timestamp = "2023-01-01T12:00:00"
        config_manager.set_last_import(custom_timestamp)
        self.assertEqual(config_manager.get_last_import(), custom_timestamp)
        
        # 设置为 None 应该使用当前时间
        config_manager.set_last_import(None)
        last_import = config_manager.get_last_import()
        self.assertIsNotNone(last_import)
        # 验证格式是否为 ISO 格式
        datetime.fromisoformat(last_import)  # 如果格式不正确，会抛出异常
    
    def test_update_setting(self):
        """测试更新应用设置"""
        config_manager = self._create_config_manager()
        
        # 更新一个设置
        config_manager.update_setting("import_mode_default", "move")
        self.assertEqual(config_manager.get_setting("import_mode_default"), "move")
        
        # 更新一个新的设置
        config_manager.update_setting("new_setting", "new_value")
        self.assertEqual(config_manager.get_setting("new_setting"), "new_value")
    
    def test_get_setting(self):
        """测试获取应用设置"""
        config_manager = self._create_config_manager()
        
        # 获取不存在的设置应该返回默认值
        self.assertEqual(config_manager.get_setting("nonexistent_setting", "default_value"), "default_value")
        
        # 获取存在的设置
        config_manager.update_setting("test_setting", "test_value")
        self.assertEqual(config_manager.get_setting("test_setting"), "test_value")
    
    def test_get_all_config(self):
        """测试获取所有配置"""
        config_manager = self._create_config_manager()
        
        # 获取所有配置应该返回配置的副本
        all_config = config_manager.get_all_config()
        self.assertEqual(all_config, config_manager.config)
        
        # 修改返回的配置不应该影响原始配置
        all_config["test_key"] = "test_value"
        self.assertNotIn("test_key", config_manager.config)
    
    def test_reset_config(self):
        """测试重置配置"""
        config_manager = self._create_config_manager()
        
        # 更新一些配置
        with tempfile.TemporaryDirectory() as temp_album_dir:
            config_manager.set_album_path(temp_album_dir)
            config_manager.update_setting("import_mode_default", "move")
            
            # 重置配置
            config_manager.reset_config()
            
            # 验证配置被重置为默认值
            self.assertEqual(config_manager.config, config_manager._default_config())


if __name__ == "__main__":
    unittest.main()
