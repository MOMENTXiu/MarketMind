# Admin Console UX Audit

> 对比 MarketMind 主用户端 (ProjectList / DataProcessing / Settings) 与 Admin 面板的风格一致性问题。

## 1. 设计令牌 (Design Tokens) — 严重

Admin 四个页面全部使用 hardcoded 颜色值，完全不引用 `main.css` 中已定义好的 CSS 自定义属性。这导致两个面板在不同页面上看起来像两套系统。

| 位置 | Admin 当前值 | 主端 CSS 变量 | 含义 |
|------|-------------|--------------|------|
| 卡片背景 | `#fff` / `#1a1a20(dark)` | `var(--color-surface)` = `#FFFFFF` / `#1A1A1A` | 暗色模式下色调偏蓝 |
| 页面背景 | `#f8fafc` / `#0f0f14(dark)` | `var(--color-bg-base)` = `#F7F7F8` / `#0A0A0A` | 主端更浅/更深 |
| 主文字 | `#111827` / `#f1f5f9(dark)` | `var(--text-primary)` = `#1A1A1C` / `#EDEDF0` | 色调不一致 |
| 次文字 | `#475569` / `#94a3b8(dark)` | `var(--text-secondary)` = `#5F5F63` / `#A1A1A6` | Admin 偏蓝灰 |
| 边框 | `rgba(15,23,42,0.06)` | `var(--border-subtle)` = `rgba(0,0,0,0.04)` | Admin 边框更明显 |
| 品牌色 | `#6366f1` (各处分写) | `--color-accent` = `#5E6AD2` | Admin 用蓝紫，主端用紫蓝 |

## 2. 卡片布局与圆角 — 严重

| 属性 | Admin 面板 | 主端 (ProjectList) | 差距 |
|------|-----------|-------------------|------|
| 卡片圆角 | 12-14px | 28px | 差距 2x |
| 卡片内边距 | 16-20px | 28px | 更拥挤 |
| 卡片阴影 | `0 1px 3px` / 无 | `0 12px 32px rgba(15,23,42,0.03)` | Admin 无浮起感 |
| 卡片 hover | `0 4px 16px rgba(0,0,0,0.06)` | `translateY(-2px) + border-color accent` | 交互模式不同 |

## 3. 按钮样式 — 中等

| 属性 | Admin 测试按钮 | 主端 btn-create |
|------|---------------|----------------|
| 圆角 | 8px | 20px |
| 高度 | fit-content | 48px |
| 颜色 | `#6366f1` (直接写) | `#6366F1` (应该用 `var(--color-accent)`) |
| hover | 仅变深 | `translateY(-1px)` + 阴影扩散 |
| Box Shadow | 无 | `0 10px 24px rgba(99,102,241,0.22)` |

## 4. 页面标题/Typography — 中等

| 属性 | Admin | 主端 `.page-title` |
|------|-------|-------------------|
| 字号 | 1.5rem | 1.75rem |
| 字重 | 700 | 800 |
| 页副标题 | 无 | `.page-sub` 0.9rem, `var(--text-tertiary)` |

## 5. 表格样式 — 中等

Admin 表格完全自建 scoped style，与主端 Element Plus 表格风格不一致。主端 DataProcessing 等页面使用 `<el-table>`。

## 6. 搜索/筛选栏 — 中等

| 属性 | Admin (Users) | 主端 `.search-box` |
|------|--------------|-------------------|
| 圆角 | 10px | 20px |
| 边框 | 硬编码 | `var(--border-subtle)` |
| 阴影 | 无 | `0 8px 24px rgba(15,23,42,0.03)` |
| 容器高度 | fit-content | 48px |

## 7. 状态 Badge — 低

| 属性 | Admin | 主端 `.status-badge` |
|------|-------|---------------------|
| 圆角 | 6px | 999px (pill) |
| 高度 | fit-content | 28px |
| 内边距 | 3px 10px | 0 12px |

## 8. 暗色模式背景色差 — 严重

Admin 侧边栏: `#1a1a20`，内容区: `#0f0f14`
主端卡片: `#1A1A1A`，页面: `#0A0A0A`

Admin 的暗色调整体偏紫蓝灰 (#1a1a**20**, #0f0f**14**)，主端是纯中性灰 (#1A1A**1A**, #0A0A**0A**)，两者放在一起视觉不统一。

## 9. Icon 使用 — 低

- Admin 使用 `:size="14/16/18/20"` (lucide prop)
- 主端统一使用 `class="h-3.5 w-3.5"` (Tailwind classes)

## 10. Sidebar 导航 — 无对等物

Admin 独有的 sidebar 布局主端没有对等物。样式上有以下问题：
- Sidebar item 圆角 10px，与主端 20px nav-item 不匹配
- Sidebar active 背景色硬编码，不用 `var(--color-accent-soft)`

## 修复优先级

| 优先级 | 问题 | 影响 |
|--------|------|------|
| P0 | 设计令牌替换 (全部 hardcode → CSS vars) | 全局 |
| P0 | 暗色模式色差 | 全局 |
| P1 | 卡片圆角/内边距/阴影统一 | Status/Settings/Logs/Users |
| P1 | 按钮样式统一 | Settings |
| P2 | 页面标题/副标题 | 全部 |
| P2 | Badge pill 化 | Users/Logs |
| P2 | 搜索框统一 | Users/Logs |
| P3 | Icon 尺寸统一 | 全部 |
