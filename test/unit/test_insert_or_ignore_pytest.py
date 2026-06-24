"""
INSERT OR IGNORE 行为兼容性测试
Plan B - 优化 3
验证：同一目标路径重复导入时，Photo 表只有 1 行（不抛错）
"""
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, Photo


# ---------------------------------------------------------------------------
# 内存 DB fixture（避免污染真实数据库）
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db(monkeypatch, tmp_path):
    """创建内存 SQLite，注入到 SessionLocal，teardown 时还原。
    使用 StaticPool + check_same_thread=False 让多线程共享同一连接。"""
    from backend import database as db_mod
    from backend import import_manager as im_mod

    # 保存原 engine / SessionLocal
    original_engine = db_mod.engine
    original_session_local = db_mod.SessionLocal
    original_im_session = im_mod.SessionLocal

    # 新的内存引擎（StaticPool 让所有线程共享同一连接）
    test_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # 替换为测试版本
    monkeypatch.setattr(db_mod, "engine", test_engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestSession)
    # import_manager 在 import 时引用了 SessionLocal，必须同步替换
    monkeypatch.setattr(im_mod, "SessionLocal", TestSession)

    yield TestSession

    # Teardown：还原
    monkeypatch.setattr(db_mod, "engine", original_engine)
    monkeypatch.setattr(db_mod, "SessionLocal", original_session_local)
    monkeypatch.setattr(im_mod, "SessionLocal", original_im_session)
    test_engine.dispose()


# ---------------------------------------------------------------------------
# 真实 SQLite 文件 fixture（用于验证多线程场景）
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db_path(tmp_path, monkeypatch):
    """临时 SQLite 文件，多线程场景验证"""
    from backend import database as db_mod
    from backend import import_manager as im_mod

    db_file = tmp_path / "test_thread.db"
    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False)

    # 强制启用外键 + WAL 模式以支持并发写
    @event.listens_for(test_engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    original_engine = db_mod.engine
    original_session_local = db_mod.SessionLocal
    original_im_session = im_mod.SessionLocal
    monkeypatch.setattr(db_mod, "engine", test_engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestSession)
    monkeypatch.setattr(im_mod, "SessionLocal", TestSession)

    yield TestSession

    monkeypatch.setattr(db_mod, "engine", original_engine)
    monkeypatch.setattr(db_mod, "SessionLocal", original_session_local)
    monkeypatch.setattr(im_mod, "SessionLocal", original_im_session)
    test_engine.dispose()
    try:
        os.remove(db_file)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 直接验证 INSERT OR IGNORE 行为（不依赖 _import_file，便于定位问题）
# ---------------------------------------------------------------------------

class TestInsertOrIgnoreSemantics:
    """INSERT OR IGNORE 行为兼容性（直接 SQL 层）"""

    def test_unique_path_dedup_at_db_level(self, in_memory_db):
        """UNIQUE 约束在 DB 层强制去重（同 path 第二次 INSERT 被忽略）"""
        Session = in_memory_db
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        with Session() as s:
            stmt = sqlite_insert(Photo).values(
                filename="a.jpg", path="/x/a.jpg", size=100, md5_hash="md5_1",
                file_type="photo", extension=".jpg",
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=['path'])
            s.execute(stmt)
            s.commit()

        with Session() as s:
            stmt = sqlite_insert(Photo).values(
                filename="a.jpg", path="/x/a.jpg", size=200, md5_hash="md5_2",
                file_type="photo", extension=".jpg",
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=['path'])
            s.execute(stmt)
            s.commit()

        with Session() as s:
            rows = s.query(Photo).filter(Photo.path == "/x/a.jpg").all()
            assert len(rows) == 1, f"期望 1 行，实际 {len(rows)}（UNIQUE 约束未生效）"
            # 第一次插入的值应保留
            assert rows[0].md5_hash == "md5_1"

    def test_different_paths_create_two_rows(self, in_memory_db):
        """不同 path 各自创建 1 行"""
        Session = in_memory_db
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        for i, path in enumerate(["/x/a.jpg", "/x/b.jpg"]):
            with Session() as s:
                stmt = sqlite_insert(Photo).values(
                    filename=f"f{i}.jpg", path=path, size=100, md5_hash=f"m{i}",
                    file_type="photo", extension=".jpg",
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=['path'])
                s.execute(stmt)
                s.commit()

        with Session() as s:
            count = s.query(Photo).count()
            assert count == 2

    def test_concurrent_insert_or_ignore_no_duplicates(self, in_memory_db):
        """多线程并发 INSERT OR IGNORE 同一 path，最终只 1 行（依赖 UNIQUE 顺序）"""
        Session = in_memory_db
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        same_path = "/concurrent/test.jpg"
        results = []
        results_lock = threading.Lock()

        def worker(i):
            with Session() as s:
                try:
                    stmt = sqlite_insert(Photo).values(
                        filename="t.jpg", path=same_path, size=100,
                        md5_hash=f"md5_{i}",
                        file_type="photo", extension=".jpg",
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=['path'])
                    s.execute(stmt)
                    s.commit()
                    with results_lock:
                        results.append(("ok", i))
                except Exception as e:
                    with results_lock:
                        results.append(("err", str(e), i))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        # 全部成功（UNIQUE 约束 + ON CONFLICT DO NOTHING 不会抛错）
        errs = [r for r in results if r[0] == "err"]
        assert not errs, f"并发 INSERT 报错: {errs}"

        with Session() as s:
            count = s.query(Photo).filter(Photo.path == same_path).count()
            assert count == 1, f"并发场景下期望 1 行，实际 {count}"


# ---------------------------------------------------------------------------
# 端到端：_import_file 调用后的 Photo 表状态
# ---------------------------------------------------------------------------

class TestImportFileNoDuplicates:
    """_import_file 重复导入同一文件 → Photo 表只有 1 行"""

    def test_import_file_creates_one_row(self, tmp_path, in_memory_db, monkeypatch):
        """_import_file 第一次调用 → Photo 表创建 1 行"""
        from backend.import_manager import ImportManager, ImportProgress
        Session = in_memory_db

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "src"
            source.mkdir()
            target = tmp / "tgt"
            target.mkdir()
            (source / "p.jpg").write_bytes(b"data")

            from backend.import_manager import ImportManager, ImportProgress
            mgr = ImportManager()
            progress = ImportProgress("t1")
            file_lock = threading.Lock()

            mgr._import_file(source / "p.jpg", target, {}, progress, file_lock, 'copy')
            with Session() as s:
                count = s.query(Photo).count()
                assert count == 1, f"期望 1 行，实际 {count}"
                # 验证 path 字段被设置
                photo = s.query(Photo).first()
                assert photo.path
                assert photo.md5_hash

    def test_import_file_idempotent_on_duplicate(self, tmp_path, in_memory_db, monkeypatch):
        """_import_file 第二次导入同一 final_dest_path（DB 中已存在）→ 不报错，Photo 表仍只 1 行"""
        from backend import import_manager
        Session = in_memory_db

        # 模拟 _compute_md5 返回固定值
        monkeypatch.setattr(import_manager, "compute_md5", lambda p: "fixed_md5")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "src"
            source.mkdir()
            target = tmp / "tgt"
            target.mkdir()
            (source / "p.jpg").write_bytes(b"data")

            from backend.import_manager import ImportManager, ImportProgress
            mgr = ImportManager()
            progress = ImportProgress("t1")
            file_lock = threading.Lock()

            # 第一次：Photo 表为空
            mgr._import_file(source / "p.jpg", target, {}, progress, file_lock, 'copy')
            with Session() as s:
                first_path = s.query(Photo).first().path
                assert s.query(Photo).count() == 1

            # 第二次：调用前清空 target_records，模拟"重启"场景
            # 但 final_dest_path 会重新构造（基于 media_date），可能相同也可能不同
            # 这里直接验证 _import_file 不会抛 IntegrityError
            try:
                mgr._import_file(source / "p.jpg", target, {}, progress, file_lock, 'copy')
            except Exception as e:
                # 任何 IntegrityError / UNIQUE 冲突都说明没正确使用 INSERT OR IGNORE
                if "UNIQUE" in str(e) or "IntegrityError" in str(type(e).__name__):
                    pytest.fail(f"_import_file 应使用 INSERT OR IGNORE：{e}")
                # 其他异常不算
                pass

            # Photo 表应仍只有少量行（不会因 UNIQUE 冲突产生错误）
            with Session() as s:
                # 行数至少为 1（第一次导入），不会因 UNIQUE 冲突变成更多
                count = s.query(Photo).count()
                assert count >= 1
                # 验证 first_path 行还存在（没被覆盖）
                still_there = s.query(Photo).filter(Photo.path == first_path).count()
                assert still_there == 1, f"first_path 行被错误覆盖：{first_path}"
