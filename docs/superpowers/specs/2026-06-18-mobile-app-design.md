# Blur Arc 移动端 App — 设计文档

> 日期: 2026-06-18 | 状态: 已确认

---

## 1. 概述

### 动机

用户想在安卓手机/平板上通过局域网浏览电脑上的照片相册，同时能从手机推送照片到电脑。

### 方案选型

- **安卓端**: Flutter（Dart 语言），一套代码 AOT 编译为原生，HTTP/图片缓存/文件上传开箱即用
- **电脑端**: 新增移动接入服务（独立端口 Flask 实例），仅暴露只读+上传端点，令牌验证

### 非目标

- 不支持 iOS（后续评估）
- 不做云同步 / 外网穿透

---

## 2. 整体架构

```
┌───────────────────────┐      WiFi LAN       ┌──────────────────────┐
│   Blur Arc (电脑端)     │◄──────────────────►│   Flutter App (安卓)  │
│                       │                     │                      │
│  主 API (127.0.0.1:5000)  桌面 UI 专用       │                      │
│                       │                     │                      │
│  上传服务 (LAN:9800-9900)  浏览器上传专用      │                      │
│                       │                     │                      │
│  ★ 移动接入 (LAN:8900-8999) Flutter App 专用  │                      │
│    · 令牌中间件验证     │  ◄── REST/HTTP ──  │  · 相册浏览           │
│    · 只读 + 上传端点    │                     │  · 照片预览           │
│    · mDNS 广播         │                     │  · 视频播放           │
│                       │                     │  · 推送照片           │
└───────────────────────┘                     └──────────────────────┘
```

---

## 3. 移动接入服务

### 3.1 生命周期

```
Blur Arc 启动
    │
    ├── 读取配置中的 mobile_service_enabled
    │       │
    │       ├── true → 自动启动移动接入服务
    │       │          已配对设备可连接
    │       │
    │       └── false → 不启动
    │

用户点击 Header 中「📱」按钮
    │
    └── 打开管理面板（按钮样式反映服务状态）
              ├── 服务开关（Toggle）→ 状态存配置
              ├── 二维码（服务开启时显示，供新设备配对）
              ├── 已配对设备列表
              ├── 当前连接信息（IP/端口）
              └── mDNS 状态
```

### 3.2 服务特点

- **独立端口**: 8900-8999 范围自动选空闲端口
- **绑定局域网 IP**: 不绑定 `0.0.0.0`，仅局域网可达
- **mDNS 广播**: `_blurarc-mobile._tcp`，Flutter App 可自动发现
- **令牌中间件**: 所有请求（除 `/api/mobile/pair-request` 外）必须携带有效 token
- **端点限制**: 只暴露只读 + 上传，无删除、无设置修改

### 3.3 API 端点

| 方法 | 路径 | 需要令牌 | 说明 |
|------|------|---------|------|
| POST | `/api/mobile/pair-request` | 否 | 发起到配对请求 |
| GET | `/api/mobile/tree` | 是 | 目录树 |
| GET | `/api/mobile/stats` | 是 | 相册统计 |
| GET | `/api/mobile/photos?path=&page=&page_size=` | 是 | 照片列表（分页） |
| GET | `/api/mobile/thumbnail?path=` | 是 | 缩略图 |
| GET | `/api/mobile/preview?path=` | 是 | 预览图 |
| GET | `/api/mobile/file?path=` | 是 | 原图/视频（Range 支持） |
| GET | `/api/mobile/exif?path=` | 是 | EXIF 元数据 |
| POST | `/api/mobile/upload` | 是 | 推送照片（multipart） |

---

## 4. 配对与令牌管理

### 4.1 配对流程

```
1. 电脑端点击「移动设备」→ 启动移动接入服务 → 生成配对码 + 显示二维码
   （二维码内容: http://{LAN_IP}:{port}/pair?code={6位随机码}）

2. Flutter App 扫码
       │
       ▼
   POST /api/mobile/pair-request
   Body: { code: "ABC123", device_name: "XiaoMi 13" }
       │
       ▼
3. 电脑端弹出确认对话框：
   ┌──────────────────────────────┐
   │  允许此设备连接相册？          │
   │                              │
   │  📱 XiaoMi 13                │
   │  请求时间: 14:32              │
   │                              │
   │  [拒绝]         [允许]        │
   └──────────────────────────────┘
       │
       ├── 允许：生成 token（UUID），激活，返回给 App
       │   App 保存 token 到本地存储 + 设备信息
       │
       └── 拒绝：pairing code 废弃，返回拒绝错误
           App 提示「连接被拒绝」

4. 超时：60 秒未操作，code 自动失效，二维码刷新
```

### 4.2 令牌验证

- 令牌格式：UUID v4
- 存储：JSON 文件（`APP_DATA_DIR/.config/mobile_tokens.json`），持久化
- 验证：中间件检查 `Authorization: Bearer <token>` 是否在已激活 token 列表中
- 无有效期，除非用户主动撤销
- 每个 token 绑定设备名和配对时间

### 4.3 管理界面

- 已配对设备列表：设备名 + 配对时间
- 每个设备旁有「撤销」按钮
- 「撤销全部」按钮
- 被撤销的设备下次请求返回 401 → App 提示重新连接

### 4.4 传输安全

- 文件传输走 HTTP（局域网内明文可接受）
- 令牌防止未授权连接
- 电脑端确认防止恶意配对

---

## 5. Flutter App 设计

### 5.1 页面结构

```
App
├── 导航栏（底部或侧边）
│   ├── 📷 相册
│   ├── 📤 推送
│   └── ⚙️ 设置
│
├── 相册浏览
│   ├── 年份列表 → 展开月份
│   ├── 照片网格（GridView）
│   ├── 全屏预览（左右滑动）
│   └── 视频播放
│
└── 推送照片
    ├── 手机相册选择（多选）
    ├── 上传进度展示
    └── 上传完成提示
```

### 5.2 连接流程

```
App 启动
    │
    ├── 检查本地 token 是否存在
    │       │
    │       ├── 有 token → 尝试 mDNS 自动发现
    │       │       ├── 发现成功 → 用 token 请求 /api/mobile/stats 验证
    │       │       │   ├── 200 → 正常进入
    │       │       │   └── 401 → token 被撤销，提示重新连接
    │       │       └── 发现失败 → 提示输入 IP
    │       │
    │       └── 无 token → 显示扫码连接页
    │
    └── 扫码连接页
        ├── QR 扫描控件
        ├── 手动输入 IP 入口
        └── 连接状态提示
```

### 5.3 关键 Flutter 库

| 功能 | 推荐库 |
|------|--------|
| HTTP 请求 | `dio`（支持拦截器、token 注入） |
| 图片缓存/加载 | `cached_network_image` |
| 视频播放 | `video_player` |
| QR 码扫描 | `qr_code_scanner` 或 `mobile_scanner` |
| mDNS 发现 | `multicast_dns` |

---

## 6. 推送照片后的导入流程

**推送开始时即时提示**，避免用户操作别的走开：

```
App 开始推送第一张照片
    │
    ▼
上传服务接收到第一个文件后，通过主 API 触发 Toast 通知
「📱 XXX 设备正在推送照片...」
    │
    ▼
用户在电脑前看到提示，可以留在电脑前等待
    │
    ▼
App 推送完成
    │
    ▼
通知升级为确认弹窗：
「📱 XXX 设备已推送 N 张照片，是否导入相册？」
    │
    ├── 确定 → 走现有流程：预检 → 去重 → 预览 → 导入
    │
    └── 稍后 → 临时文件保留，可手动导入
```

---

## 7. 电脑端 UI 改动

### 7.1 移动设备入口

在 Header 组件中，设置按钮旁边增加「📱」移动设备按钮，样式反映服务状态：

| 服务状态 | 按钮样式 |
|---------|---------|
| 关闭 | 灰色轮廓图标 |
| 运行中 | 品牌色（primary）填充图标 |

点击按钮 → 始终打开移动设备管理面板，不直接切换服务状态。

移动接入服务的开关状态通过 `ConfigManager.update_setting('mobile_service_enabled', true/false)` 持久化到配置中。启动时读取此配置决定是否自动启动服务。

### 7.2 管理面板

新增组件 `MobileDeviceManager.tsx`：

```
┌────────────────────────────────────────┐
│  📱 移动设备访问                        │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  移动接入服务        [● ● ● ● ●] │  │  ← Toggle 开关
│  │  状态: 运行中 | 已停止            │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ── 连接信息 ──                         │
│  IP: 192.168.1.5                       │
│  端口: 8912                            │
│                                        │
│  ── 新设备配对 ──                       │
│  ┌──────────────────────┐              │
│  │  ██████████████████  │              │  ← 二维码（服务开启时显示）
│  │  ██ QR CODE ███████  │              │
│  │  ██████████████████  │              │
│  └──────────────────────┘              │
│                                        │
│  ── 已配对设备 ──                       │
│  📱 XiaoMi 13    2026-06-18  [撤销]    │
│  📱 iPad mini    2026-06-17  [撤销]    │
│                           [撤销全部]    │
└────────────────────────────────────────┘
```

---

## 8. 文件结构变更

### 电脑端

```
后端新增:
  backend/mobile_access_server.py    # 移动接入服务（独立 Flask 实例）

后端修改:
  backend/api_server.py              # 新增 /api/mobile/* 桥接端点

前端新增:
  frontend/src/components/dialogs/MobileDeviceManager.tsx  # 管理面板

前端修改:
  frontend/src/components/layout/Header.tsx    # 增加📱入口按钮
  frontend/src/components/dialogs/ImportDialog/ImportDialog.tsx
                                              # 处理推送照片导入提示
```

### Flutter App（全新仓库）

```
blurarc_app/
├── lib/
│   ├── main.dart                    # 入口
│   ├── services/
│   │   ├── api_client.dart          # Dio HTTP 客户端（token 注入）
│   │   └── mdns_discovery.dart      # mDNS 自动发现
│   ├── screens/
│   │   ├── connect_screen.dart      # 扫码连接页
│   │   ├── album_screen.dart        # 相册浏览首页
│   │   ├── photo_grid.dart          # 照片网格
│   │   ├── photo_preview.dart       # 全屏预览
│   │   ├── video_player.dart        # 视频播放
│   │   └── upload_screen.dart       # 推送照片
│   ├── models/
│   │   └── photo.dart               # 数据模型
│   └── widgets/
│       ├── year_list.dart           # 年份列表
│       └── upload_progress.dart     # 上传进度
├── pubspec.yaml
└── ...
```

---

## 9. 实现阶段

| 阶段 | 内容 | 说明 |
|------|------|------|
| **Phase 1** | `mobile_access_server.py` | 核心服务 + 令牌管理 + 所有端点 |
| **Phase 2** | 主 API 桥接端点 + 前端管理面板 | UI 控制和服务联调 |
| **Phase 3** | mDNS 广播 + 发现 | 自动连接 |
| **Phase 4** | Flutter App 框架 + 连接 | 扫码、配对流、token 管理 |
| **Phase 5** | Flutter App 相册浏览 | 目录树、网格、预览、视频 |
| **Phase 6** | Flutter App 推送照片 | 选照片、上传、进度 |
| **Phase 7** | 联调 + 测试 | 端到端测试 |
