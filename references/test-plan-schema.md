# meta.yaml

```yaml
uuid: string
title: string
url: string
started_at: string
# 🔴 设计来源（report.py 渲染来源卡片用）
sources:
  figma: "https://www.figma.com/design/xxx"
  document: "https://docs.popo.netease.com/xxx"
# 🔴 系统列表（report.py 渲染平台卡片用；accounts 数组也兼容）
systems:
  - name: string
    url: string
    account: string
# 兼容格式
accounts:
  - system: string
    url: string
    email: string
    password: string
```

# test-plan.yaml

```yaml
uuid: string
title: string
url: string
flows:
  - name: string
    setup:
      navigate: string    # URL fragment like /members
    cases:
      - id: TC-001
        source: user | ai | document | figma  # 🔴 从需求文档派生的写 document，Figma 派生写 figma
        category: navigation | presence | form | interaction | table | dialog | error | regression
        description: string
        action: click | type | navigate | select | submit_empty | verify_element | verify_nav | check_missing | flow
        target_text: string
        value: string
        expect: string
        status: pending
standalone:
  - id: TC-002
    ...
```

# results.yaml (per case)

```yaml
- id: TC-001
  system: string           # 🔴 必填！平台名（网易运营平台 / 企业运营平台）
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

From snapshot text, identify:
- `link` not marked active → navigation case
- `button` without [disabled] → click response case
- `switch` → toggle case
- `textbox` → input case
- `combobox` → select case
- `columnheader button` → sort case
- pagination number buttons → pagination case
- tab elements → tab switch case
- form submit/save buttons → submit + empty-submit cases

# Safety filter

Skip elements whose visible text contains any of:
退出登录, 登出, 注销, 删除, 移除, 禁用, 封禁, delete, remove, disable, ban
