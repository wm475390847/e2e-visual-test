#!/usr/bin/env python3
"""Generate self-contained HTML report from results.yaml + screenshots."""
import sys, os, base64, yaml, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

def encode_image(path):
    p = Path(path)
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = p.suffix.lower().replace(".", "")
    return f"data:image/{ext};base64,{b64}"

# ── Module classifier ──────────────────────────────────
def classify(case):
    """Return (system, module_key, module_label)"""
    cid = case.get("id", "")
    system = case.get("system", "默认")

    rules = [
        (r"LOGIN", "", "登录"),
        (r"ENT-00[1-5]", "team", "团队管理"),
        (r"ENT-01[0-1]", "sso", "SSO 登录配置"),
        (r"ENT-02", "credits", "积分管理"),
        (r"ENT-03", "layout", "通用布局"),
        (r"OPS-001|OPS-002|OPS-003|CRUD-00[1-3]", "enterprise", "企业账号开通"),
        (r"OPS-01", "credits", "积分管理"),
        (r"OPS-02", "model", "模型配置"),
    ]
    for pat, mod_key, mod_label in rules:
        if re.search(pat, cid):
            return system, mod_key, mod_label
    return system, "other", "其他"

ICONS = {"登录": "🔐", "团队管理": "👥", "SSO 登录配置": "🔑", "积分管理": "💰",
         "通用布局": "🧭", "企业账号开通": "🏢", "模型配置": "⚙️", "其他": "📋"}
SYSTEM_COLORS = {"网易运营平台": ("#6366f1", "#eef2ff"),
                 "企业运营平台": ("#10b981", "#ecfdf5")}

# ── HTML builders ──────────────────────────────────────
def platform_cards(meta):
    systems = meta.get("systems", [])
    if not systems:
        return f"<div>目标: {meta.get('url', '')}</div>"
    colors = ["#6366f1", "#10b981"]
    parts = []
    for i, s in enumerate(systems):
        c = colors[i % len(colors)]
        parts.append(f'''
        <div class="plat-row">
          <span class="plat-dot" style="background:{c}"></span>
          <span class="plat-name">{s["name"]}</span>
          <code class="plat-url">{s.get("url","")}</code>
        </div>
        <div class="plat-acct">👤 {s.get("account","")}</div>''')
    return "".join(parts)

def source_cards(meta):
    sources = meta.get("sources", {})
    parts = []
    if sources.get("figma"):
        parts.append(f'<div class="src-row">📐 <a href="{sources["figma"]}" target="_blank">Figma 设计稿</a></div>')
    if sources.get("document"):
        parts.append(f'<div class="src-row">📄 {sources["document"]}</div>')
    return "".join(parts) if parts else "<div class='src-row'>—</div>"

def case_screenshot(case, run_dir):
    ss = case.get("screenshot") or case.get("screenshots")
    if isinstance(ss, str) and ss:
        data = encode_image(os.path.join(run_dir, ss))
        if data:
            return f'<div class="ss-wrap"><div class="ss-label">📸 截图</div><img src="{data}" loading="lazy"></div>'
    return ""

def case_row(case, run_dir, compact=False):
    cid = case.get("id", "")
    status = case.get("status", "")
    si = {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "⚠️"}.get(status, "❓")
    desc = case.get("description") or case.get("note", "")
    note = case.get("note", "")
    source = case.get("source", "")
    sys_name = case.get("system", "")

    tag = ""
    if source == "document":
        tag = '<span class="tag tag-doc">文档</span>'
    elif source == "figma":
        tag = '<span class="tag tag-figma">Figma</span>'

    row_class = "case-item" if compact else "case-item"
    return f'''<div class="case-item" data-status="{status}">
  <div class="ci-hd" onclick="this.parentElement.classList.toggle('open')">
    <span class="ci-icon">{si}</span>
    <code class="ci-id">{cid}</code>
    <span class="ci-desc">{desc}</span>
    {tag}
    {f'<span class="ci-note">{note}</span>' if note and not compact else ''}
    <span class="ci-chev">▸</span>
  </div>
  <div class="ci-bd">
    <div class="ci-meta">
      <span>{si} {status}</span>
      <span>📋 {sys_name}</span>
      {tag}
    </div>
    {f'<p class="ci-note-text">{note}</p>' if note else ''}
    {case_screenshot(case, run_dir)}
  </div>
</div>'''

# ── Module cards ───────────────────────────────────────
def module_cards(results, run_dir):
    groups = defaultdict(list)
    for r in results:
        system, mod_key, mod_label = classify(r)
        groups[(system, mod_key, mod_label)].append(r)

    # Order
    order = [
        ("企业运营平台", "team", "团队管理"),
        ("企业运营平台", "sso", "SSO 登录配置"),
        ("企业运营平台", "credits", "积分管理"),
        ("企业运营平台", "layout", "通用布局"),
        ("企业运营平台", "", "登录"),
        ("网易运营平台", "enterprise", "企业账号开通"),
        ("网易运营平台", "credits", "积分管理"),
        ("网易运营平台", "model", "模型配置"),
        ("网易运营平台", "", "登录"),
    ]
    seen = set()
    cards = []

    for key in order:
        if key in groups and key not in seen:
            seen.add(key)
            system, mod_key, mod_label = key
            cases = groups[key]
            total = len(cases)
            passed = sum(1 for c in cases if c["status"] == "pass")
            failed = sum(1 for c in cases if c["status"] == "fail")
            skipped = sum(1 for c in cases if c["status"] == "skip")
            pct = round(passed / total * 100) if total > 0 else 0
            pct_class = "good" if pct >= 100 else ("warn" if pct >= 80 else "bad")
            sys_color, sys_bg = SYSTEM_COLORS.get(system, ("#64748b", "#f8fafc"))
            icon = ICONS.get(mod_label, "📋")

            rows = "".join(case_row(c, run_dir, compact=True) for c in cases)

            cards.append(f'''
<div class="mod-card">
  <div class="mc-hd" onclick="this.parentElement.classList.toggle('open')" style="border-left:4px solid {sys_color}">
    <span class="mc-icon">{icon}</span>
    <div class="mc-info">
      <div class="mc-name">{system}<span class="mc-sep">›</span>{mod_label}</div>
      <div class="mc-stats">
        <span>✓ {passed}</span>
        {f'<span class="warn">✗ {failed}</span>' if failed else ''}
        {f'<span class="dim">⊘ {skipped}</span>' if skipped else ''}
        <span>· {total} 用例</span>
      </div>
    </div>
    <div class="mc-bar-bg"><div class="mc-bar-fill {pct_class}" style="width:{pct}%"></div></div>
    <span class="mc-rate {pct_class}">{pct}%</span>
    <span class="mc-chev">▸</span>
  </div>
  <div class="mc-bd">
    {rows}
  </div>
</div>''')

    # Remaining groups
    for key, cases in groups.items():
        if key in seen:
            continue
        seen.add(key)
        system, mod_key, mod_label = key
        total = len(cases)
        passed = sum(1 for c in cases if c["status"] == "pass")
        failed = sum(1 for c in cases if c["status"] == "fail")
        pct = round(passed / total * 100) if total > 0 else 0
        pct_class = "good" if pct >= 100 else ("warn" if pct >= 80 else "bad")
        sys_color, _ = SYSTEM_COLORS.get(system, ("#64748b", "#f8fafc"))
        icon = ICONS.get(mod_label, "📋")
        rows = "".join(case_row(c, run_dir, compact=True) for c in cases)
        cards.append(f'''
<div class="mod-card">
  <div class="mc-hd" onclick="this.parentElement.classList.toggle('open')" style="border-left:4px solid {sys_color}">
    <span class="mc-icon">{icon}</span>
    <div class="mc-info">
      <div class="mc-name">{system}<span class="mc-sep">›</span>{mod_label}</div>
      <div class="mc-stats"><span>✓ {passed}</span><span>· {total} 用例</span></div>
    </div>
    <div class="mc-bar-bg"><div class="mc-bar-fill {pct_class}" style="width:{pct}%"></div></div>
    <span class="mc-rate {pct_class}">{pct}%</span>
    <span class="mc-chev">▸</span>
  </div>
  <div class="mc-bd">{rows}</div>
</div>''')

    return "".join(cards), len(seen)

# ── Main ───────────────────────────────────────────────
def main(run_id: str):
    base = os.path.expanduser("~/.openclaw/workspace/e2e-tests")
    run_dir = os.path.join(base, run_id)

    with open(os.path.join(run_dir, "results.yaml")) as f:
        results = yaml.safe_load(f)

    with open(os.path.join(run_dir, "meta.yaml")) as f:
        meta = yaml.safe_load(f)

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    errors = sum(1 for r in results if r["status"] == "error")
    rate = round(passed / total * 100, 1) if total > 0 else 0
    doc_cases = sum(1 for r in results if r.get("source") == "document")
    figma_cases = sum(1 for r in results if r.get("source") == "figma")

    # Ring: circumference 2*pi*34 ≈ 213.6, dashoffset for remaining
    rate_offset = round(213.6 * (1 - rate / 100), 1)

    tz = timezone(timedelta(hours=8))
    duration = "N/A"
    if meta.get("started_at"):
        start = datetime.fromisoformat(meta["started_at"])
        elapsed = datetime.now(tz) - start
        mins = int(elapsed.total_seconds() // 60)
        secs = int(elapsed.total_seconds() % 60)
        duration = f"{mins}m {secs}s"

    mod_cards_html, module_count = module_cards(results, run_dir)

    with open(os.path.join(os.path.dirname(__file__), "..", "assets", "report-template.html")) as f:
        tpl = f.read()

    html = tpl
    html = html.replace("{{UUID}}", run_id)
    html = html.replace("{{TIMESTAMP}}", meta.get("started_at", ""))
    html = html.replace("{{DURATION}}", duration)
    html = html.replace("{{TOTAL}}", str(total))
    html = html.replace("{{PASSED}}", str(passed))
    html = html.replace("{{FAILED}}", str(failed))
    html = html.replace("{{SKIPPED}}", str(skipped))
    html = html.replace("{{ERRORS}}", str(errors))
    html = html.replace("{{RATE}}", str(rate))
    html = html.replace("{{DOC_COUNT}}", str(doc_cases))
    html = html.replace("{{FIGMA_COUNT}}", str(figma_cases))
    html = html.replace("{{RATE_OFFSET}}", str(rate_offset))
    html = html.replace("{{MODULE_COUNT}}", str(module_count))
    html = html.replace("{{PLATFORM_CARDS}}", platform_cards(meta))
    html = html.replace("{{SOURCE_CARDS}}", source_cards(meta))
    html = html.replace("{{MODULES}}", mod_cards_html)

    out_path = os.path.join(run_dir, "report.html")
    with open(out_path, "w") as f:
        f.write(html)

    print(out_path)

if __name__ == "__main__":
    main(sys.argv[1])
