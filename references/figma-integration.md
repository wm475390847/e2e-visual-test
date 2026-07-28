# Figma Integration

## Input formats
- Figma share URL: `https://www.figma.com/file/{key}/...` or `https://www.figma.com/design/{key}/...`
- Figma file key directly
- Exported design screenshots (fallback)

## 🔴 Figma API 使用规范（强制）

### 数据获取策略：一次拉全，禁止并发

**核心原则**：Figma Viewer 席位 API 配额极低（约 60 次/小时），必须用最少的调用获取完整数据。

#### 1. 单次调用获取完整节点树

```
figma__get_figma_data(fileKey, nodeId, depth=6)
```

- **depth 必须设为 6 或更高**，确保一次性拿到完整节点树，避免因截断而需要额外调用
- **禁止**使用默认 depth（可能返回不完整数据导致需要补拉）
- 当用户提供的 Figma 链接包含 `node-id` 参数时，必须将其作为 `nodeId` 传入，精准定位模块
- 当用户未指定 `node-id` 且 Figma 文件包含多个模块时，先用 depth=1 拉取顶层 Frame 列表，让用户选择模块，再对选中模块做 depth=6 深入拉取

#### 2. 禁止并发 Figma 调用

- **绝对禁止**同时发起多个 `figma__get_figma_data` 调用
- Figma API 按调用次数限流，并发 4 个请求 = 瞬间消耗 4 次配额
- 所有 Figma API 调用必须**串行**，每次调用间隔至少 2 秒

#### 3. Rate Limit 处理

```
Figma API rate limit hit (429). Retry after N seconds.
```

- 收到 429 后：**必须等待 `Retry after` 指定的秒数**，不要提前重试
- 如果等待后仍然 429：使用 `cron` 设置一个 `at` 类型定时任务，在冷却结束后自动重试
- 在冷却期间：**禁止**向用户索要设计细节来替代 Figma 数据——这是设计稿就有的信息，应该从 Figma 获取
- 如果同一 session 内多次 429：向用户说明 Figma Viewer 配额问题，建议用户升级到 Editor 席位或提供设计截图作为补充

#### 4. 数据完整性校验

在生成用例前，必须确认已获取的数据覆盖了所有子页面：

- 从顶层节点树中提取所有子页面/Frame 名称
- 从详细节点树中验证每个子页面的交互组件都被捕获
- 如果有子页面数据不完整（截断或缺失），在重试后仍无法获取时，在用例中标注 `source: ai` 并加注 `# TODO: Figma数据缺失，需人工补充`
- **禁止**在数据不完整时假装完整生成用例，更禁止让用户逐一提供设计细节

### 数据提取 Checklist

获取 Figma 数据后，按以下清单逐一提取，确保无遗漏：

- [ ] **页面列表**：所有 Frame/Page 名称 → 一个 Frame 对应一个 Flow
- [ ] **布局组件**：Header、Sidebar、TabBar、StatusBar、面板标题栏
- [ ] **输入组件**：输入框（含 placeholder）、选择器、开关、上传区域
- [ ] **展示组件**：卡片、列表项、表格、代码块、Markdown 区域
- [ ] **交互组件**：按钮（主要/次要/禁用）、下拉菜单、弹窗/对话框
- [ ] **状态变化**：loading、empty、error、disabled、active、hover、展开/收起
- [ ] **业务流程**：页面间跳转关系、操作前后的状态变化
- [ ] **边界场景**：空状态、超长文本、最小宽度、滚动行为

## Parsing

Use `figma__get_figma_data` to extract:
- Page/frame structure → 每个顶层 Frame 对应一个测试 Flow
- Component tree (buttons, forms, tables, nav, dialogs) → 生成 presence + interaction cases
- User flow connections (page-to-page navigation in prototypes) → 生成 flow cases
- Interactive states (hover, focus, active, disabled, expanded/collapsed) → 生成状态 cases

## Case generation from Figma

Three types:

### Presence cases
For each component found in Figma, check if it exists in the page snapshot:
- Found in both → generate interaction case (verify it works)
- In Figma but missing in page → regression case (component absent)
- In page but not in Figma → note as possible unplanned feature

### Interaction cases
For each interactive component in Figma that also exists in page:
- Generate click/type/select case matching the component's intended behavior

### Flow cases
If Figma has prototype links between frames:
- Generate sequential flow case following the designed user path
- Steps: navigate start → perform each interaction → verify destination

## Three-source merge

Priority: user-specified > figma-generated > ai-exploration

Deduplication: same target_text + same action in different sources → keep highest priority only
Figma presence cases are NOT duplicated by AI exploration cases for the same elements

## Fallback

If Figma fetch fails or returns inaccessible after all retries:
- 在用例中显式标注 `source: ai` 和 `# TODO: Figma数据缺失`
- 从用户提供的其他材料（截图、需求文档）中提取可用信息
- 在 `meta.yaml` 的 `notes` 中明确记录哪些模块的 Figma 数据未成功获取
- Do not block the test run
