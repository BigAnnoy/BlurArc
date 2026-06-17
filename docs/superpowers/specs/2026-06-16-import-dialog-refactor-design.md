# 导入弹窗重构设计文档

## 概述

重构 `ImportDialog` 组件，补全相比老前端缺失的所有功能。

## 设计决策

### 组件结构：模块化拆分

将 `ImportDialog.tsx` 拆分为文件夹结构：

```
frontend/src/components/dialogs/ImportDialog/
├── index.ts                    # 导出
├── ImportDialog.tsx            # 主组件（状态管理、步骤切换）
├── types.ts                    # 类型定义
├── Step1Select.tsx             # 步骤1：选择源路径 + 检查
├── Step2Preview.tsx            # 步骤2：预览文件
├── Step3Importing.tsx          # 步骤3：导入进度
├── StatsCards.tsx              # 统计卡片
├── TimelineTab.tsx             # 时间线标签页
├── TargetDuplicatesTab.tsx     # 相册重复标签页
├── SourceDuplicatesTab.tsx     # 源重复标签页
└── PhotoPreviewModal.tsx       # 照片预览弹窗
```

## 架构设计

### 状态管理

主组件 `ImportDialog` 管理所有状态，通过 props 传递给子组件：

```typescript
interface ImportDialogState {
  // 步骤控制
  step: 'select' | 'checking' | 'preview' | 'importing';

  // 步骤1：选择
  sourcePath: string;
  mode: 'copy' | 'move';
  isChecking: boolean;
  checkProgress: CheckProgress;

  // 步骤2：预览
  previewData: PreviewData | null;
  selectedPhotos: Set<string>;        // 时间线选中
  selectedTargetDup: Set<string>;     // 相册重复选中
  selectedSourceDup: Set<string>;     // 源重复选中
  skipTargetDuplicates: boolean;
  skipSourceDuplicates: boolean;

  // 步骤3：导入
  importId: string | null;
  importProgress: ImportProgress;
  isPaused: boolean;

  // 照片预览
  previewPhoto: Photo | null;
}
```

### 数据流

```
用户输入源路径
    ↓
[步骤1] 点击确认 → 调用 checkImportPath (异步)
    ↓
显示检查进度 → 完成后获取 previewData
    ↓
[步骤2] 显示预览 → 用户可筛选/选择/删除
    ↓
点击开始导入 → 调用 startImport
    ↓
[步骤3] 显示导入进度 → 支持暂停/取消
    ↓
完成 → 刷新相册
```

### API 调用

| 操作 | API | 说明 |
|------|-----|------|
| 检查源路径 | `POST /api/import/check/start` | 异步，返回 check_id |
| 获取检查进度 | `GET /api/import/check/progress/:id` | 轮询 |
| 开始导入 | `POST /api/import/start` | 支持 skip 参数 |
| 获取导入进度 | `GET /api/import/progress/:id` | 轮询 |
| 暂停导入 | `POST /api/import/pause/:id` | |
| 继续导入 | `POST /api/import/resume/:id` | |
| 取消导入 | `POST /api/import/cancel/:id` | |
| 删除文件 | `POST /api/files/delete` | 删除选中的重复文件 |

## 组件设计

### Step1Select

**职责：** 选择源路径、选择导入模式、触发检查

**功能：**
- 路径输入框 + 浏览按钮
- 复制/移动模式选择卡片
- 确认按钮 → 触发检查
- 检查进度条和状态文本
- 取消检查按钮

### Step2Preview

**职责：** 显示预览数据，处理重复文件

**功能：**
- 统计卡片（媒体数、大小、重复数）
- 标签页导航
- 时间线标签页（日期筛选、照片网格）
- 相册重复标签页（重复组列表、跳过选项）
- 源重复标签页（重复组列表）
- 开始导入按钮

### StatsCards

**职责：** 显示预览统计信息

**Props：**
```typescript
interface StatsCardsProps {
  mediaCount: number;
  totalSizeMB: number;
  targetDupCount: number;
  sourceDupCount: number;
}
```

### TimelineTab

**职责：** 按日期筛选待导入文件

**功能：**
- 左侧：日期列表（YYYY-MM 格式，显示文件数）
- 右侧：照片网格
- 选择模式支持
- 删除所选功能

### TargetDuplicatesTab

**职责：** 处理与相册重复的文件

**功能：**
- 重复文件组列表
- 照片预览面板
- "跳过这些重复文件" checkbox
- 选择/删除重复照片

### SourceDuplicatesTab

**职责：** 处理源文件夹内的重复文件

**功能：**
- 重复文件组列表
- 照片预览面板
- 选择/删除重复照片

### Step3Importing

**职责：** 显示导入进度

**功能：**
- 进度条
- 当前文件名
- 百分比显示
- 暂停/继续按钮
- 取消按钮
- 错误信息显示

### PhotoPreviewModal

**职责：** 大图预览

**功能：**
- 大图显示
- 文件名、大小、路径信息
- 打开文件按钮（调用系统打开）

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 源路径不存在 | Toast 提示 + 不进入下一步 |
| 检查失败 | Toast 提示 + 停留在步骤1 |
| 导入失败 | 显示错误信息 + 停留在步骤3 |
| 网络错误 | Toast 提示 + 允许重试 |
| 空文件夹 | Toast 提示 "没有可导入的媒体文件" |

## 测试策略

**重要：测试全程不操作生产数据！**

### 验证方式

1. **构建验证** - `npm run build` 确保无编译错误
2. **类型检查** - TypeScript 类型正确
3. **UI 审查** - 启动开发服务器，检查组件渲染
4. **Mock 数据测试** - 使用假数据验证 UI 逻辑：
   - Mock 检查结果（不调用真实 API）
   - Mock 导入进度（不执行真实导入）
   - Mock 重复文件数据（不读取真实文件）

### 不执行的操作

- ❌ 不调用真实导入 API
- ❌ 不操作生产相册目录
- ❌ 不执行文件删除
- ❌ 不创建测试文件夹

### 验证清单

- [ ] TypeScript 编译通过
- [ ] 组件正确渲染
- [ ] 步骤切换正常
- [ ] 选择逻辑正确
- [ ] UI 样式正确

## 实现顺序

1. **API 层** - 补全 api.ts 中的方法
2. **类型定义** - 定义所有接口类型
3. **主组件框架** - ImportDialog 状态管理和步骤切换
4. **Step1Select** - 选择和检查功能
5. **StatsCards** - 统计卡片
6. **TimelineTab** - 时间线标签页
7. **TargetDuplicatesTab** - 相册重复标签页
8. **SourceDuplicatesTab** - 源重复标签页
9. **Step2Preview** - 整合预览步骤
10. **Step3Importing** - 导入进度增强
11. **PhotoPreviewModal** - 照片预览弹窗
12. **测试验证** - 使用测试数据验证
