# 2026-06-22 — dev-start 加热更新运行（hot reload）选项

## 背景
之前 `dev-start.bat` 的 [3]/[7] 选项走的是"build APK + adb install"路径，
每次改一行代码都要全量构建并重装 APK，迭代效率低。

Flutter 官方提供 `flutter run -d <device>` 模式，启动后会和设备保持长连接，
源码变更后按 `r` 即可秒级热更新（hot reload）。

## 改动
[scripts/dev-start.bat](../../scripts/dev-start.bat)

### 1. 菜单新增 2 个选项

| 选项 | 说明 |
|------|------|
| `[9] Hot run phone emulator` | **自动启动 PC 端**（前端构建 + BlurArc.py）+ 手机 AVD + flutter run 热更新 |
| `[10] Hot run tablet emulator` | **自动启动 PC 端** + 平板 AVD + flutter run 热更新 |
| `[11] Exit` | 原本 `[9]` |

### 2. 抽离 `:run_pc_app_core`

原 `:run_pc_app` 包含 `pause` 提示，无法在 hot run 流程中复用。
拆出 `:run_pc_app_core`（仅做核心步骤，失败 `exit /b 1`）：
- Step 1：`cd frontend && npm run build`
- Step 2：`start "BlurArc" python BlurArc.py`

`:run_pc_app` 改为调用 `:run_pc_app_core` + pause（菜单 [8] 行为不变）。

### 3. `:hotrun_emulator` / `:hotrun_tablet_emulator` 改为多步

```
call :run_pc_app_core      # 先跑 PC 端
  ↓ 失败 → 中止（提示"PC 端启动失败"）
set DEPLOY_* 环境变量
  ↓
call :deploy_avd_common    # 启动 AVD + 等待开机
  ↓ DEPLOY_HOT=1 → hotrun_branch
flutter run                # 长连接
```

PC 端启动后会自动拉起：
- Flask 后端（5000）
- PyWebView 桌面端（BlurArc UI）
- mDNS 广播（`mobile_access_server.start()`，自动发现）
- 移动接入服务（`MobileAccessServer`）

### 4. `:deploy_avd_common` 加 `DEPLOY_HOT` 模式分支

调用前可设置：
- `DEPLOY_HOT=1` → 进入 `:hotrun_branch`（仅 `flutter run`，跳过 build/install）
- 其他 → 原有 `:install_branch`（build APK + install + launch）

两个新入口：
- `:hotrun_emulator` — 手机 AVD（`AVD_NAME=BlurArc_Test`，无 skin）
- `:hotrun_tablet_emulator` — 平板 AVD（`AVD_TABLET_NAME=BlurArc_Tablet`，skin=1280x800）

两者都先复用了 AVD 检查/启动/等待开机的逻辑（避免重复代码），然后切到 hot 分支。

### 5. 热更新提示

```
============================================================
Hot run Flutter on phone emulator (auto-detect device)
============================================================
Tips: Press  r  = hot reload  (preserve state, ~1-2s)
      Press  R  = hot restart (reset state,    ~5s)
      Press  q  = quit
      Press  h  = help (more commands)
Note : Modify .dart code in IDE and save, then press r.
       First run takes longer (build & install on device).
============================================================
```

## 使用流程
1. 在 IDE 编辑 `.dart` 文件
2. 终端运行 `dev-start.bat`
3. 选 `9`（手机）或 `10`（平板）
4. 自动启动 PC 端（构建前端 + 启动 BlurArc.py，含 mDNS/移动接入）
5. 启动 AVD（若未运行），等待开机完成
6. `flutter run` 接上长连接，等待首次 build + install（首次约 30-60s）
7. 改代码 → 保存 → 在此终端按 `r` → 1-2s 后设备自动刷新
8. 按 `q` 退出 flutter run，但 PC 端继续运行

如果只想启动 PC 端（不连模拟器），用 [8] Run PC app。

## 限制
- `pubspec.yaml` 依赖变更、native plugin 改动、AndroidManifest 改动
  不能 hot reload，需要按 `R` 热重启或重新走 `[3]/[7]` 完整安装
- `flutter run` 阻塞当前终端（这是 Flutter 工具本身的限制）：
  用户在 IDE 编辑代码后切回此终端按 `r` 即可，dev-start 菜单重新进入会
  提示 cmd 已运行
