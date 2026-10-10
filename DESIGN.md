# Design — TDLauncher

<!-- impeccable:design-schema 1 -->

视觉世界：**深夜示波器**（2026-10-10 经 impeccable 决策页选定，seed 370da70f，model-pick 方向，code-led 构建）。
界面是一台在暗室里持续描记下载信号的仪器：暖黑机箱、黄绿磷光描迹。串行（tdl session 锁的硬约束）被转译成扫描节奏——一次一条链接，每条完整描记。

## Palette

| Token | Value | 用途 |
|---|---|---|
| `BG` | `#141B14` | 暖黑地面 |
| `PANEL` | `#101710` | 面板（方角 3px、平面、发丝线描边，**不用圆角卡片/渐变**） |
| `PANEL2` | `#18211A` | 抬升层（hover / 弹出 / 按下） |
| `WELL` | `#0C120C` | 输入井 |
| `LINE` / `LINE2` | `#2A3628` / `#3A4A34` | 发丝线描边 / hover 描边 |
| `INK` | `#E7EFE4` | 主文字（磷光白） |
| `DIM` | `#7E8F7A` | 次文字（刻度灰绿） |
| `FAINT` | `#4E5C4B` | 占位 / 禁用 |
| `ACC` | `#B7E34A` | **唯一强调色**：磷光黄绿（运行 / 进度 / 焦点 / 主按钮） |
| `ACC_HI` / `ACC_LINE` | `#D4F27A` / `#5A7038` | 磷光亮端 / 磷光描边 |
| `ACC_BG` / `ACC_BG_ROW` | `rgba(183,227,74,0.08)` / `0.06` | 磷光底 / 选中行底 |
| `ON` | `#141B14` | 磷光上的文字 |
| `DONE` | `#5A8A44` | 完成（低饱和绿，不与 ACC 争辉） |
| `WARN` / `FAIL` | `#E5B567` / `#F87171` | 仅表状态 |

纪律：ACC 只出现在运行、进度、焦点、主按钮上；其它一切中性。辉光只属于两个元素——大百分比数字（QGraphicsDropShadowEffect, blur 28, alpha 70）与 CellsBar 点亮格（alpha 60 的外扩 halo）。

## Type

- 正文/控件：`Microsoft YaHei UI / Segoe UI`，13px。
- 数据层一律等宽：`Consolas / Cascadia Mono`——链接、文件名、百分比、速度、ETA、日志、顶栏路径、芯片。
- 大百分比：`Bahnschrift` 54px Bold，磷光色 + 辉光，固定 104px 栏（防换行挤压迹线）。
- 眉题（SecTitle）：11px Bold，字距 2；FieldLabel 11px。

## Signature moves

1. **扫描迹线**：24 格 CellsBar，点亮格发光、空白格 `#1E291C`；最后一个部分点亮格是**扫描亮头**（ACC_HI 色 + alpha 110 大光晕），模拟电子束前沿。动画 240ms OutCubic。
2. **时基扫描**：根画布 `ScanlineRoot` 自带 CRT 扫描线（alpha 14 黑线每 4px）与边缘暗角；下载中一条磷光带以 ~45px/s 自上而下扫过全屏（33ms 定时器，仅 running 时激活）。
3. **LED 队列**：StatusMark 16px——queued 空灯位圆环（#2A3628），running 实心 LED + 7px 光晕，done 低饱和绿实心，failed 红实心，stopped 灰环。
4. **顶栏芯片**：运行时显示 `ROW xx/yy`（等宽、磷光描边）= 当前扫描行；TAKEOUT 开启时显示 `TAKEOUT`（刻度灰）。
5. **扫描游标**：活动队列行左侧 3px 磷光竖条（QVariantAnimation 160ms 淡入）。
6. **发光元素**：品牌标（alpha 90）、大百分比（blur 28, alpha 70）、开始按钮（alpha 80）、迹线点亮格与亮头。其余元素不发光。

## Components

- 控件统一高 34px、圆角 6px、井底 `#0C120C`；hover 描边 LINE2、focus 描边 ACC。
- 按钮：幽灵风（透明底 + LINE 描边）；`#Primary` 实心磷光渐变（**不带辉光**）；`#Stop` 琥珀警示；`#Toggle` 选中 = ACC 文字 + ACC_LINE 描边 + ACC_BG 底。
- 徽标 Badge：11px Bold 字距 1；running = ACC/ACC_LINE/ACC_BG + 1.6s 呼吸（QGraphicsOpacityEffect，仅 running 启用）。
- ComboBox 箭头槽自绘：PANEL2 槽底、磷光 chevron、hover 提亮。
- 进度条：chunk 为 ACC→ACC_HI 水平渐变；done = DONE；failed = FAIL。
- QMenu/QToolTip/TipLabel：PANEL2 底、ACC_LINE 描边、圆角 6。

## Layout

固定 1280×720 画布等比缩放。根 margin (14,12)、模块间距 10。
顶栏紧凑（内边距 (14,6)）→ 左链接栏（stretch 5，内边距 (14,12,14,10)）→ 右栏（stretch 14）：参数（内边距 (14,10)、控件高 27、Toggle 高 27、字段标签 10px——**刻意压缩，把高度让给内容区**）→ 工作区（队列 stretch 5 : 进度 stretch 12，内边距 (14,12)）。
进度区：标题行 → amount 行（大百分比固定 104px 栏 + 迹线 13px + meta）→ 逐文件列表 → 日志（96px 可折叠，文字 `#9DCB6A` 仪器绿）+ 按钮列。

字阶：SecTitle 10px / FieldLabel 10px / 正文 13px / 控件 12px / MetaVal 13px Bold 磷光 / 大百分比 54px Bahnschrift。

## Hard rules（此世界内）

- 面板方角（≤3px）、平面、发丝线——不回到圆角渐变卡片。
- 辉光只给大百分比与迹线点亮格；按钮、面板、文字不发光。
- 状态图标一律自绘矢量（LED / StatusMark），不用 Unicode 符号或 emoji。
- 数据永远等宽体；大数字永远 Bahnschrift。
