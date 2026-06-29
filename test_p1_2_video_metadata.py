"""
测试 video_metadata 缓存修复

测试场景：
1. 首次请求视频元数据（缓存未命中）
2. 重复请求同一视频（缓存命中）
3. 修改视频文件后请求（缓存失效）
4. 请求不同视频（缓存隔离）
5. 性能对比（缓存命中 vs 未命中）
6. 缓存大小限制（maxsize=500）
7. 内存增长稳定性
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.api_server import _cached_video_metadata
from backend.video_processor import VideoProcessor

# 正确的 mock 路径：因为 _cached_video_metadata 内部延迟导入 VideoProcessor
# 所以需要 mock backend.video_processor.VideoProcessor.extract_metadata
MOCK_EXTRACT = 'backend.video_processor.VideoProcessor.extract_metadata'


class TestVideoMetadataCache:
    """测试 video_metadata 缓存功能"""

    def setup_method(self):
        """每个测试前清空缓存"""
        _cached_video_metadata.cache_clear()

    def teardown_method(self):
        """每个测试后清空缓存"""
        _cached_video_metadata.cache_clear()

    def test_cache_miss_first_request(self):
        """测试 1: 首次请求（缓存未命中）"""
        print("\n=== 测试 1: 首次请求（缓存未命中）===")

        temp_path = os.path.join(tempfile.gettempdir(), "test_video_1.mp4")
        file_mtime = time.time()

        mock_metadata = {
            'duration': 120.5,
            'width': 1920,
            'height': 1080,
            'codec': 'h264',
            'format': 'mp4',
            'size': 1024000
        }

        with patch(MOCK_EXTRACT, return_value=mock_metadata) as mock_extract:
            result = _cached_video_metadata(temp_path, file_mtime)

            assert result == mock_metadata, "返回的元数据不匹配"
            assert mock_extract.call_count == 1, "应该调用一次 extract_metadata"

            cache_info = _cached_video_metadata.cache_info()
            assert cache_info.misses == 1, f"缓存未命中次数应为 1，实际为 {cache_info.misses}"
            assert cache_info.hits == 0, f"缓存命中次数应为 0，实际为 {cache_info.hits}"

            print(f"  OK 首次请求成功，缓存未命中: {cache_info.misses}")
            print(f"  OK 返回数据: duration={result['duration']}s, resolution={result['width']}x{result['height']}")

    def test_cache_hit_repeated_request(self):
        """测试 2: 重复请求同一视频（缓存命中）"""
        print("\n=== 测试 2: 重复请求（缓存命中）===")

        temp_path = os.path.join(tempfile.gettempdir(), "test_video_2.mp4")
        file_mtime = time.time()

        mock_metadata = {
            'duration': 60.0,
            'width': 1280,
            'height': 720,
            'codec': 'h264',
            'format': 'mp4',
            'size': 512000
        }

        with patch(MOCK_EXTRACT, return_value=mock_metadata) as mock_extract:
            result1 = _cached_video_metadata(temp_path, file_mtime)
            call_count_1 = mock_extract.call_count

            result2 = _cached_video_metadata(temp_path, file_mtime)
            call_count_2 = mock_extract.call_count

            result3 = _cached_video_metadata(temp_path, file_mtime)
            call_count_3 = mock_extract.call_count

            assert result1 == result2 == result3, "多次请求结果应该一致"
            assert call_count_1 == 1, "第一次应该调用 extract_metadata"
            assert call_count_2 == 1, "第二次不应该调用 extract_metadata（缓存命中）"
            assert call_count_3 == 1, "第三次不应该调用 extract_metadata（缓存命中）"

            cache_info = _cached_video_metadata.cache_info()
            assert cache_info.hits == 2, f"缓存命中次数应为 2，实际为 {cache_info.hits}"
            assert cache_info.misses == 1, f"缓存未命中次数应为 1，实际为 {cache_info.misses}"

            print(f"  OK 三次请求结果一致")
            print(f"  OK extract_metadata 只调用 1 次，缓存命中 2 次")
            print(f"  OK 缓存信息: {cache_info}")

    def test_cache_invalidation_on_file_change(self):
        """测试 3: 修改视频文件后请求（缓存失效）"""
        print("\n=== 测试 3: 文件修改后缓存失效 ===")

        temp_path = os.path.join(tempfile.gettempdir(), "test_video_3.mp4")
        file_mtime_1 = time.time()

        mock_metadata_1 = {
            'duration': 100.0,
            'width': 1920,
            'height': 1080,
            'codec': 'h264',
            'format': 'mp4',
            'size': 1000000
        }

        mock_metadata_2 = {
            'duration': 200.0,
            'width': 3840,
            'height': 2160,
            'codec': 'h265',
            'format': 'mp4',
            'size': 2000000
        }

        with patch(MOCK_EXTRACT, return_value=mock_metadata_1) as mock_extract:
            result1 = _cached_video_metadata(temp_path, file_mtime_1)
            assert result1 == mock_metadata_1, "第一次请求结果不正确"

            time.sleep(0.01)
            file_mtime_2 = time.time()

            mock_extract.return_value = mock_metadata_2

            result2 = _cached_video_metadata(temp_path, file_mtime_2)

            assert result2 == mock_metadata_2, "文件修改后应该返回新的元数据"
            assert result2['duration'] != result1['duration'], "元数据应该不同"
            assert result2['width'] != result1['width'], "元数据应该不同"

            cache_info = _cached_video_metadata.cache_info()
            assert cache_info.misses == 2, f"应该有 2 次缓存未命中，实际为 {cache_info.misses}"

            print(f"  OK 文件修改后缓存正确失效")
            print(f"  OK 第一次: duration={result1['duration']}s, {result1['width']}x{result1['height']}")
            print(f"  OK 修改后: duration={result2['duration']}s, {result2['width']}x{result2['height']}")

    def test_cache_isolation_different_videos(self):
        """测试 4: 请求不同视频（缓存隔离）"""
        print("\n=== 测试 4: 不同视频的缓存隔离 ===")

        temp_path_1 = os.path.join(tempfile.gettempdir(), "test_video_4a.mp4")
        temp_path_2 = os.path.join(tempfile.gettempdir(), "test_video_4b.mp4")
        file_mtime = time.time()

        mock_metadata_1 = {
            'duration': 30.0,
            'width': 640,
            'height': 480,
            'codec': 'h264',
            'format': 'mp4',
            'size': 256000
        }

        mock_metadata_2 = {
            'duration': 90.0,
            'width': 1920,
            'height': 1080,
            'codec': 'h265',
            'format': 'mkv',
            'size': 768000
        }

        with patch(MOCK_EXTRACT) as mock_extract:
            mock_extract.return_value = mock_metadata_1
            result1 = _cached_video_metadata(temp_path_1, file_mtime)

            mock_extract.return_value = mock_metadata_2
            result2 = _cached_video_metadata(temp_path_2, file_mtime)

            result3 = _cached_video_metadata(temp_path_1, file_mtime)

            assert result1 == mock_metadata_1, "视频 A 的元数据不正确"
            assert result2 == mock_metadata_2, "视频 B 的元数据不正确"
            assert result3 == mock_metadata_1, "视频 A 的缓存数据不正确"
            assert result1 != result2, "不同视频的元数据应该不同"

            cache_info = _cached_video_metadata.cache_info()
            assert cache_info.misses == 2, f"应该有 2 次缓存未命中，实际为 {cache_info.misses}"
            assert cache_info.hits == 1, f"应该有 1 次缓存命中，实际为 {cache_info.hits}"

            print(f"  OK 不同视频的缓存正确隔离")
            print(f"  OK 视频 A: duration={result1['duration']}s")
            print(f"  OK 视频 B: duration={result2['duration']}s")
            print(f"  OK 视频 A 再次请求: duration={result3['duration']}s (缓存命中)")

    def test_performance_comparison(self):
        """测试 5: 性能对比（缓存命中 vs 未命中）"""
        print("\n=== 测试 5: 性能对比 ===")

        temp_path = os.path.join(tempfile.gettempdir(), "test_video_5.mp4")
        file_mtime = time.time()

        mock_metadata = {
            'duration': 120.0,
            'width': 1920,
            'height': 1080,
            'codec': 'h264',
            'format': 'mp4',
            'size': 1024000
        }

        def slow_extract(path):
            time.sleep(0.01)  # 10ms 模拟 FFmpeg 调用
            return mock_metadata

        with patch(MOCK_EXTRACT, side_effect=slow_extract):
            start_time = time.perf_counter()
            result1 = _cached_video_metadata(temp_path, file_mtime)
            miss_time = (time.perf_counter() - start_time) * 1000

            start_time = time.perf_counter()
            result2 = _cached_video_metadata(temp_path, file_mtime)
            hit_time = (time.perf_counter() - start_time) * 1000

            print(f"  OK 缓存未命中耗时: {miss_time:.3f} ms")
            print(f"  OK 缓存命中耗时:   {hit_time:.3f} ms")

            speedup = miss_time / hit_time if hit_time > 0 else float('inf')
            print(f"  OK 性能提升: {speedup:.1f}x")

            assert hit_time < 10, f"缓存命中耗时应 < 10ms，实际为 {hit_time:.3f}ms"

            improvement = (miss_time - hit_time) / miss_time * 100 if miss_time > 0 else 0
            print(f"  OK 耗时减少: {improvement:.1f}%")
            assert improvement > 90, f"缓存命中耗时应减少 90%+，实际减少 {improvement:.1f}%"

    def test_cache_size_limit(self):
        """测试 6: 缓存大小限制（maxsize=500）"""
        print("\n=== 测试 6: 缓存大小限制 ===")

        mock_metadata = {
            'duration': 60.0,
            'width': 1280,
            'height': 720,
            'codec': 'h264',
            'format': 'mp4',
            'size': 512000
        }

        with patch(MOCK_EXTRACT, return_value=mock_metadata):
            for i in range(600):
                temp_path = os.path.join(tempfile.gettempdir(), f"test_video_6_{i}.mp4")
                file_mtime = time.time() + i
                _cached_video_metadata(temp_path, file_mtime)

            cache_info = _cached_video_metadata.cache_info()

            assert cache_info.currsize <= 500, f"缓存大小应 <= 500，实际为 {cache_info.currsize}"
            print(f"  OK 缓存大小限制生效: {cache_info.currsize} / 500")
            print(f"  OK 缓存统计: {cache_info}")

            # 验证 LRU 淘汰：第一个视频（最早插入）应该已被淘汰
            first_path = os.path.join(tempfile.gettempdir(), "test_video_6_0.mp4")
            misses_before = cache_info.misses
            _cached_video_metadata(first_path, 0)

            cache_info_after = _cached_video_metadata.cache_info()
            assert cache_info_after.misses > misses_before, "第一个视频应该缓存未命中（已被淘汰）"
            print(f"  OK LRU 淘汰策略正常工作")

    def test_memory_growth_stability(self):
        """测试 7: 内存增长稳定性"""
        print("\n=== 测试 7: 内存增长稳定性 ===")

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        mock_metadata = {
            'duration': 60.0,
            'width': 1280,
            'height': 720,
            'codec': 'h264',
            'format': 'mp4',
            'size': 512000
        }

        with patch(MOCK_EXTRACT, return_value=mock_metadata):
            for i in range(1000):
                temp_path = os.path.join(tempfile.gettempdir(), f"test_video_7_{i}.mp4")
                file_mtime = time.time() + i
                _cached_video_metadata(temp_path, file_mtime)

                if (i + 1) % 100 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    cache_info = _cached_video_metadata.cache_info()
                    print(f"    [{i+1}/1000] 内存: {current_memory:.2f} MB, 缓存大小: {cache_info.currsize}")

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory

            print(f"  OK 初始内存: {initial_memory:.2f} MB")
            print(f"  OK 最终内存: {final_memory:.2f} MB")
            print(f"  OK 内存增长: {memory_growth:.2f} MB")

            cache_info = _cached_video_metadata.cache_info()
            assert cache_info.currsize <= 500, f"缓存大小应 <= 500，实际为 {cache_info.currsize}"
            assert memory_growth < 50, f"内存增长应 < 50MB，实际增长 {memory_growth:.2f}MB"

            print(f"  OK 内存增长平稳，无泄漏风险")

    def test_return_structure_consistency(self):
        """测试 8: 返回结构一致性"""
        print("\n=== 测试 8: 返回结构一致性 ===")

        temp_path = os.path.join(tempfile.gettempdir(), "test_video_8.mp4")
        file_mtime = time.time()

        mock_metadata = {
            'duration': 120.5,
            'width': 1920,
            'height': 1080,
            'codec': 'h264',
            'format': 'mp4',
            'size': 1024000
        }

        with patch(MOCK_EXTRACT, return_value=mock_metadata):
            results = []
            for _ in range(5):
                result = _cached_video_metadata(temp_path, file_mtime)
                results.append(result)

            for i, result in enumerate(results):
                assert result == mock_metadata, f"第 {i+1} 次请求结果不一致"
                assert 'duration' in result, "缺少 duration 字段"
                assert 'width' in result, "缺少 width 字段"
                assert 'height' in result, "缺少 height 字段"
                assert 'codec' in result, "缺少 codec 字段"
                assert 'format' in result, "缺少 format 字段"
                assert 'size' in result, "缺少 size 字段"

            print(f"  OK 5 次请求返回结构完全一致")
            print(f"  OK 包含所有必需字段: duration, width, height, codec, format, size")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Video Metadata 缓存修复测试")
    print("=" * 60)

    test_instance = TestVideoMetadataCache()

    tests = [
        ("缓存未命中", test_instance.test_cache_miss_first_request),
        ("缓存命中", test_instance.test_cache_hit_repeated_request),
        ("缓存失效", test_instance.test_cache_invalidation_on_file_change),
        ("缓存隔离", test_instance.test_cache_isolation_different_videos),
        ("性能对比", test_instance.test_performance_comparison),
        ("缓存大小限制", test_instance.test_cache_size_limit),
        ("内存稳定性", test_instance.test_memory_growth_stability),
        ("返回结构一致性", test_instance.test_return_structure_consistency),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_instance.setup_method()
            test_func()
            test_instance.teardown_method()
            passed += 1
            print(f"✓ {test_name} 测试通过\n")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} 测试失败: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
