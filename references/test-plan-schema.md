# meta.yaml — 通用配置格式

```yaml
uuid: string
title: string
url: string
started_at: string

# 🔴 设计来源（report.py 渲染来源卡片用）
sources:
  figma: "https://www.figma.com/design/xxx"  # Figma 设计稿链接
  document: "https://docs.xxx.com/xxx"        # 需求文档链接（任意平台）

# 🔴 系统列表（report.py 渲染平台卡片用，支持任意数量）
systems:
  - name: 运营后台               # 系统名称
    url: https://admin.example.com
    account: admin@example.com
    color: "#6366f1"            # 可选，平台主色；不填自动分配
  - name: 用户端
    url: https://app.example.com
    account: user@example.com
    # color 缺省 → 自动从调色板分配

# 🔴 模块定义（report.py 用例分类依据，完全配置驱动）
modules:
  - key: enterprise              # 模块 key（用于 test-plan 和 results 关联）
    label: 企业管理               # 模块显示名
    icon: "🏢"                   # emoji 图标
    system: 运营后台              # 所属系统
    order: 1                     # 显示排序（数字）
    keywords:                    # 关键词匹配（用于未标记 system/module 的旧用例）
      - "企业|开通|禁用|enterprise"
      - "CRUD-0"
    tc_range:                    # TC-ID 号段匹配（用于未标记的旧用例）
      - [1, 26]
  - key: team
    label: 团队管理
    icon: "👥"
    system: 用户端
    order: 2
    keywords:
      - "团队|成员|member|邀请"
    tc_range:
      - [27, 40]

# 🔴 安全配置（可选）
safety:
  skip_keywords:                # 测试中禁止点击的按钮关键词
    - "退出登录"
    - "注销"
    - "delete"
    - "remove"
    - "禁用"
    - "封禁"

# 兼容旧格式：accounts 数组也支持
accounts:
  - system: 运营后台
    url: https://admin.example.com
    email: admin@example.com
    password: xxx
```

# test-plan.yaml — 通用测试计划

```yaml
uuid: string
title: string
url: string
flows:
  - name: 企业管理-开通企业
    system: 运营后台           # 🔴 所属系统（对应 meta.systems[].name）
    module: enterprise         # 🔴 所属模块（对应 meta.modules[].key）
    setup:
      navigate: /enterprise
    cases:
      - id: TC-001
        source: user | ai | document | figma
        system: 运营后台        # 可覆盖 flow 级 system
        module: enterprise      # 可覆盖 flow 级 module
        category: navigation | presence | form | interaction | table | dialog | error | regression
        description: string
        action: click | type | navigate | select | submit_empty | verify_element | verify_nav | check_missing | flow
        target_text: string
        value: string
        expect: string
        status: pending
standalone:
  - id: TC-099
    system: 运营后台
    module: enterprise
    ...
```

# results.yaml — 通用执行结果

```yaml
- id: TC-001
  system: 运营后台            # 🔴 必填！平台名
  module: enterprise          # 🔴 推荐填写（否则 report.py 用关键词/TD-ID 匹配）
  source: user | ai | document | figma
  status: pass | fail | skip | error
  duration_ms: int
  note: string
  screenshots:
    before: screenshots/TC-001_before.png
    after: screenshots/TC-001_after.png
  snapshot_before: string
  snapshot_after: string
  assertion:
    expected: string
    actual: string
```

# Case generation patterns

从 snapshot aria 文本中识别：
- `link` not marked active → navigation case
- `button` without [disabled] → click response case
- `switch` → toggle case
- `textbox` → input case
- `combobox` → select case
- `columnheader button` → sort case
- pagination → pagination case
- tab elements → tab switch case
- form submit/save → submit + empty-submit cases

# Safety filter

安全过滤词从 `meta.yaml` 的 `safety.skip_keywords` 读取；未配置时使用默认列表。测试中遇到匹配的按钮文字时跳过交互。
