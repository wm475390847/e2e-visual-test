---
name: "e2e-visual-test"
description: "浏览器快照驱动E2E测试：snapshot+Figma→用例→登录→串行执行→截图→报告→自动关浏览器。CRUD三连+页面级截图。"
---

# Visual E2E Test

Snapshot-based E2E testing engine. AI judges via aria text snapshots; screenshots are for human review only. Supports Figma design comparison for presence/regression checks.

## Trigger

- User sends a URL + testing intent
- User mentions `/e2e`, "测试这个页面", "跑 E2E", "回归测试"
- `/e2e {url}` — AI-only exploration
- `/e2e {url} 1.case1 2.case2` — user cases + AI supplement
- `/e2e {url} --figma={url}` — Figma-augmented
- `/e2e-review {url}` — generate cases for review before execution
- `/e2e-report {uuid}` — view HTML report
- `/e2e-list` — list past runs

## Workflow

### Phase 1: Init
- Run `python3 scripts/init.py {url}` → get UUID, creates `workspace/e2e-tests/{uuid}/`
- 仅创建目录，**不打开浏览器**，暂时不做任何页面操作

### Phase 2: 用例生成（Figma 设计稿 + 需求文档）
**纯文档分析，不打开浏览器。**

- 从用户输入中提取 Figma 链接、需求文档链接、平台地址
- 并行拉取 Figma 结构 + 需求文档内容
- Figma：调用 `figma__get_figma_data` 获取设计稿节点树 → 识别页面布局、组件、交互状态（对话框、开关、弹窗等）
- 需求文档：提取功能模块、业务流程、表单字段、校验规则
- 交叉对比 Figma 设计 + 需求文档 → 生成覆盖用例：
  - **页面基础用例**：每个页面/标签页的元素存在性、核心组件
  - **流程用例**：文档中描述的业务操作流程（开通企业、搜索筛选、禁用等）
  - **CRUD 三连**：文档中涉及创建/删除的功能 → 自动生成 Create→Verify→Cleanup
  - **校验用例**：文档中提到的必填字段、格式校验规则
  - **交互状态用例**：Figma 中有但文档未提及的弹窗、开关、禁用态等
- If user gave cases: merge with AI cases, user cases take priority
- Deduplicate: same target_text + same action → keep highest-priority source (user > figma > ai)
- Write `meta.yaml`（平台地址+账号+设计来源）和 `test-plan.yaml`

#### 🔴 meta.yaml 必需字段

```yaml
uuid: string
title: string
url: string
started_at: string
# 设计稿与需求文档来源（report.py 渲染平台卡片/来源卡片用）
sources:
  figma: "https://www.figma.com/design/xxx"   # Figma 设计稿链接
  document: "https://docs.popo.netease.com/xxx" # 需求文档链接（POPO/Notion/语雀等）
# 系统列表（report.py 渲染平台卡片用）
systems:
  - name: 网易运营平台
    url: https://neteasecc.codewave-test.163yun.com
    account: admin@codechat.netease.com
  - name: 企业运营平台
    url: https://codechat.codewave-test.163yun.com
    account: wangmin18@corp.netease.com
# 兼容格式：accounts 数组也支持（report.py 有 fallback）
accounts:
  - system: 网易运营平台
    url: https://xxx
    email: admin@xxx
    password: xxx
```

#### 🔴 test-plan.yaml 中 case 的 source 字段

每个 case 必须正确设置 `source`，report.py 据此统计需求文档/Figma 覆盖数：

```yaml
cases:
  - id: TC-001
    source: document  # 从需求文档派生的用例 → "document"
  - id: TC-005
    source: figma     # 从 Figma 设计稿识别的用例 → "figma"
  - id: TC-010
    source: ai        # AI 补充的用例 → "ai"
```

**用例排序原则**（test-plan.yaml 中 flow 的 cases 必须按前后依赖关系排列）：
- 先页面基础（页面加载、元素存在性）→ 再交互操作（点击、输入、搜索）→ 最后副作用验证（对话框、状态变更）
- CRUD 三连严格排序：Create → Verify → Cleanup（中间不能插入其他 flow）
- 同一 flow 内，前置 case 的状态变更（如创建了一条数据）供后续 case 使用
- 跨平台 flow：先管理员平台 → 再企业平台（管理员创建的数据供企业平台验证）
- Display brief plan summary, then auto-proceed to Phase 3 without waiting for user confirmation

### Phase 3: Unified Login（统一登录）
**用例确认后，主 session 统一登录所有平台，全程一个 Chrome 实例。**

- 从 `meta.yaml` 读取所有系统的账号/密码
- 按系统逐个登录，每个系统开一个浏览器 tab
- 不同系统使用不同子域名 → cookie 不冲突 → 可同时登录多系统
- **同一域名不同账号**（同平台不同角色）→ 先退出再登另一个
- 登录完成后浏览器全部 tab 处于已认证状态

### Phase 4: Worker 执行（默认单 Worker 串行）
**默认模式：1 个 Worker，严格按 test-plan.yaml 中 flow 和 cases 的顺序串行执行。**

为什么用单 Worker 串行而不是多 Worker 并行：

| 维度 | 单 Worker 串行 | 多 Worker 并行 |
|------|---------------|---------------|
| 浏览器状态 | 一个 tab 逐步走，状态完全可控 | 多个 tab 争抢窗口，状态不可预期 |
| Case 间依赖 | 严格顺序，创建→验证→清理步骤可靠 | 竞态：B 可能访问 A 尚未创建的数据 |
| 主 session | 一个 Worker 完成直接拿结果 | 需等全部 Worker 回来才能汇总 |
| 调试效率 | 一条链路清晰可追溯，case 逐行排列 | 多个结果文件分散，难以定位问题 |
| 实际效率 | 串行速度已经够快（~2 分钟 30+ 用例） | 并行优势有限，反而引入同步复杂度 |

**执行规则**：
- ✅ 所有用例由 **1 个** `sessions_spawn` 子 agent 执行
- ✅ Worker 严格按照 test-plan.yaml 中 **flow 顺序 + flow 内 case 顺序** 逐步执行
- ✅ 先执行 Flow 1 全部 case → 再执行 Flow 2 全部 case → ... → 最后 standalone
- ✅ 每个 flow 执行前先 `navigate` 到 `setup.navigate` 指定的页面
- ✅ 每个 case 完成后立即写入 `results-0.yaml`（不积攒内存）
- ✅ Worker 直接 `navigate` 到目标页面 URL，**不执行 login**
- ✅ Worker 开始时 snapshot 确认已登录（检查 header/导航栏有无用户名）
- ✅ 多平台切换时：navigate 到对应平台的 URL 即可（cookie 已认证）

**Worker task 编写要点**：
- task 中按 flow 分节（===== 第1部分: xxx =====），每个 flow 内 case 按编号排序
- 明确标注 case 间的前后关系："同页面继续"、"先清空搜索"、"切换到XX平台"
- 创建类 case 的最后一个 case 做 Verify，确保创建结果可被后续 case 依赖
- **🔴 每个 case 必须包含完整的 browser screenshot + browser snapshot + 写入 results 三步**
- **🔴 截图保存流程**: browser screenshot → `exec mv` 到 `screenshots/{TC-ID}.png`
- **🔴 snapshot 保存流程**: browser snapshot → `exec write` /tmp/snap.txt → `exec cat` 读回写入 results.yaml
- **🔴 snapshot_before / snapshot_after 必须保存完整原文，严禁用文字摘要代替**
- **所有用例执行完成后**，调用 `browser action=stop` 关闭浏览器释放资源

**可选的并行模式**（仅 `--parallel` 显式指定时启用）：
- 按 flow 拆分，每个 flow 一个 Worker
- 仅当用户明确要求、且 flow 之间无数据依赖时才使用
- Worker task 同上：跳过 login，直接 navigate

- 使用 `sessions_yield` 等待 worker 完成

### Phase 5: Report
- `python3 scripts/merge.py {uuid}` → merge results
- `python3 scripts/report.py {uuid}` → self-contained HTML with base64 screenshots
- Output report path to user

## Per-case execution（🔴 强制，每个验证点不可跳过）

每个 case 执行必须包含完整的截图 + snapshot 原文，生成可审计证据链。**禁止只写文字总结而不保存截图和 snapshot。**

1. Check precondition: if wrong page, navigate to setup URL or flow's previous state
2. `browser snapshot` → **用 `exec` 将 aria 文本写入 `/tmp/snap_before.txt`，再 `exec cat` 读回保存到 results**
3. `browser screenshot` → **用 `exec mv` 将截图保存到 `screenshots/{TC-ID}.png`（必须实际写入文件）**
4. Execute action via browser act (use aria ref from snapshot)
5. Wait 1-2s
6. `browser snapshot` → **用 `exec` 将 aria 文本写入 `/tmp/snap_after.txt`，再 `exec cat` 读回保存到 results**
7. `browser screenshot` → **用 `exec mv` 将截图保存到 `screenshots/{TC-ID}_after.png`（必须实际写入文件）**
8. Compare snapshots textually: URL change, element presence/absence, [disabled]/[active] state, toast messages, list changes
9. Write result to `results-{n}.yaml` immediately (don't batch in memory)

### results.yaml 必须字段

```yaml
- id: TC-XXX
  system: <平台名>   # 🔴 必填！网易运营平台 / 企业运营平台（report.py detect_system() 作为 fallback）
  source: ai | document | figma  # 🔴 从 test-plan 继承，不可全部填 ai
  status: pass | fail | skip
  duration_ms: <数字>
  note: <说明>
  screenshots:
    before: screenshots/TC-XXX.png
    after: screenshots/TC-XXX_after.png
  snapshot_before: |
    <完整的 browser snapshot aria 原始文本，不可省略不可摘要>
  snapshot_after: |
    <完整的 browser snapshot aria 原始文本，不可省略不可摘要>
  assertion:
    expected: <预期>
    actual: <实际>
```

⚠️ `system` 和 `source` 字段缺失会导致 report.py 的模块分类、来源统计不准确（虽有 fallback，但不如显式传入精确）。

### 🔴 审计证据链

每个 case 必须产生 3 类可审计证据：
1. **截图（before + after）** → 人眼审查用，文件必须在 screenshots/ 目录下可见
2. **snapshot 原文（before + after）** → 写入 results.yaml，不得省略、不得摘要
3. **断言（expected + actual）** → 基于 snapshot 对比得出的判断

缺失任一证据的 case 视为无效，需重新执行。

## Flow handling

- Same-flow cases run in sequential order within the single worker
- Between cases: if current page doesn't match next case's expected page, auto-navigate via flow's setup or previous case's result
- Each flow has a `setup.navigate` that runs before first case

## Safety

### 允许操作
- **自建数据 CRUD 完整流程**: Create（创建测试数据）→ Read（验证创建结果）→ Update（修改测试数据）→ Delete（清理测试数据）全程开放
- **测试数据命名规范**: 所有测试创建的数据必须使用 `e2e_` 或 `test_` 前缀标识
- **表单提交**: 允许提交表单来测试创建/修改流程，字段使用明确的测试值（如 `e2e_test_enterprise`、`test_user_001`）
- **删除操作**: 仅允许删除带有 `e2e_` / `test_` 前缀的自建测试数据，禁止删除系统预置数据或其他用户数据

### CRUD 三连模式
每个 Create 用例必须配对 Cleanup 用例，在 flow 末尾执行：
1. TC-Create: 创建 `e2e_xxx` → snapshot 验证创建成功
2. TC-Verify: 检查列表/详情页出现 `e2e_xxx` → 验证数据正确
3. TC-Cleanup: 删除 `e2e_xxx` → snapshot 验证删除成功且列表恢复

### 禁止操作
- ❌ **禁止操作非自建数据**: 不得删除/修改/禁用非 `e2e_`/`test_` 前缀的数据
- ❌ **禁止保存 SSO/安全配置**: SSO 配置、密码修改、安全设置只做存在性验证，不提交
- ❌ **禁止操作真实用户账号**: 不改真实用户的密码、角色、状态
- ❌ **禁止点击**: 退出登录、注销账号、重置密码（这些会打断测试流程）

## Screenshot Strategy

### 页面级截图
**每个页面一张代表截图**，同一页面所有用例共享：
- 用例进入 page → `navigate` → 等待渲染 → `screenshot` → `{page-name}.png`
- 后续同页面用例引用同一张 screenshot
- 弹窗/下拉等交互状态单独截图：`{page-name}-{dialog-name}.png`

### 文件命名
- 页面：`ent-login.png`, `ent-members.png`, `ops-credits.png`
- 弹窗：`ent-members-edit-role.png`, `ops-system-config.png`
- 状态：`ops-crud.png`, `ops-disable-confirm.png`

## Scripts

- `scripts/init.py {url}` — UUID + directory
- `scripts/merge.py {uuid}` — merge results-*.yaml
- `scripts/report.py {uuid}` — generate HTML

See `references/test-plan-schema.md` for YAML format and case structure.
See `references/figma-integration.md` for Figma analysis strategy.
