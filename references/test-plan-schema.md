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
        source: user | ai | figma
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
  source: user | ai | figma
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
