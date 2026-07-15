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
def detect_system(case):
    """Detect platform system from case fields."""
    # Explicit field takes priority
    system = case.get("system", "")
    if system:
        return system
    # Detect from description + note + flow context
    desc = (case.get("description") or "") + " " + (case.get("note") or "")
    if re.search(r'运营平台|admin|ops|opera|管理员平台', desc, re.I):
        return "网易运营平台"
    if re.search(r'企业平台|enterprise|member|wangmin|团队管理|企业运营', desc, re.I):
        return "企业运营平台"
    # Detect from TC-ID range (TC-001-TC-026 → 运营平台, TC-027-TC-040 → 企业平台)
    m = re.match(r'TC-(\d+)', case.get("id", ""))
    if m:
        n = int(m.group(1))
        if n <= 26:
            return "网易运营平台"
        elif n <= 40:
            return "企业运营平台"
    return "默认"


def classify(case):
    """Return (system, module_key, module_label)"""
    cid = case.get("id", "")
    desc = (case.get("description") or "").lower()
    note = (case.get("note") or "").lower()
    system = detect_system(case)

    rules = [
        # Legacy patterns
        (r"LOGIN", "", "登录"),
        (r"ENT-00[1-5]", "team", "团队管理"),
        (r"ENT-01[0-1]", "sso", "SSO 登录配置"),
        (r"ENT-02", "credits", "积分管理"),
        (r"ENT-03", "layout", "通用布局"),
        (r"OPS-001|OPS-002|OPS-003|CRUD-00[1-3]", "enterprise", "企业账号开通"),
        (r"OPS-01", "credits", "积分管理"),
        (r"OPS-02", "model", "模型配置"),
        # TC-* patterns (from Figma + document generated plans)
        (r"TC-TM-", "enterprise", "企业管理"),
        (r"TC-SR-", "enterprise", "搜索筛选"),
        (r"TC-CR-", "enterprise", "开通企业"),
        (r"TC-PG-", "enterprise", "分页"),
        (r"TC-DD-", "enterprise", "禁用企业"),
        (r"TC-NV-", "credits", "运营平台"),
        (r"TC-ET-", "team", "团队管理"),
        (r"TC-SSO-", "sso", "SSO 登录配置"),
        (r"TC-XP-", "enterprise", "跨平台验证"),
    ]
    for pat, mod_key, mod_label in rules:
        if re.search(pat, cid):
            return system, mod_key, mod_label

    # Fallback: keyword matching on description + note for simple TC-IDs
    desc_text = desc + " " + note
    keywords = [
        (r"登录|login", "", "登录"),
        (r"团队|成员|member|邀请|审核|已拒绝|编辑角色", "team", "团队管理"),
        (r"sso|单点", "sso", "SSO 登录配置"),
        (r"积分|credits|消耗|充值|系数|调用次数|日期汇总|用户汇总", "credits", "积分管理"),
        (r"模型|model", "model", "模型配置"),
        (r"企业|开通|禁用|启用|c.r.u.d|重置密码|清理|cleanup|e2e_", "enterprise", "企业账号开通"),
        (r"导航|首页|侧边|导航栏", "layout", "通用布局"),
    ]
    for pat, mod_key, mod_label in keywords:
        if re.search(pat, desc_text):
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
        # Try legacy accounts format
        accounts = meta.get("accounts", [])
        if accounts:
            colors = ["#6366f1", "#10b981"]
            parts = []
            for i, a in enumerate(accounts):
                c = colors[i % len(colors)]
                sys_name = a.get("system", a.get("nickname", f"系统{i+1}"))
                url = a.get("url", a.get("login_url", ""))
                parts.append(f'''
        <div class="plat-row">
          <span class="plat-dot" style="background:{c}"></span>
          <span class="plat-name">{sys_name}</span>
          <code class="plat-url">{url}</code>
        </div>
        <div class="plat-acct">👤 {a.get("email","")}</div>''')
            return "".join(parts)
        # Legacy fallback for old meta format
        for key in ["admin", "enterprise"]:
            if key in meta:
                color = "#6366f1" if key == "admin" else "#10b981"
                name = "网易运营平台" if key == "admin" else "企业运营平台"
                return f'''
        <div class="plat-row">
          <span class="plat-dot" style="background:{color}"></span>
          <span class="plat-name">{name}</span>
          <code class="plat-url">{meta[key].get("url","")}</code>
        </div>
        <div class="plat-acct">👤 {meta[key].get("email","")}</div>'''
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
        parts.append(f'<div class="src-row">\U0001f3a8 <a href="{sources["figma"]}" target="_blank">Figma \u8bbe\u8ba1\u7a3f</a></div>')
    if sources.get("document"):
        parts.append(f'<div class="src-row">\U0001f4c4 <a href="{sources["document"]}" target="_blank">\u9700\u6c42\u6587\u6863</a></div>')
    if not parts:
        return "<div class='src-row' style='color:var(--text3); font-style:italic'>\u672a\u63d0\u4f9b\u8bbe\u8ba1\u7a3f/\u9700\u6c42\u6587\u6863\u94fe\u63a5\uff08\u8bf7\u5728 meta.yaml \u4e2d\u6dfb\u52a0 sources \u5b57\u6bb5\uff09</div>"
    return "".join(parts)

def case_screenshot(case, run_dir):
    ss = case.get("screenshot") or case.get("screenshots")
    # Handle string path
    if isinstance(ss, str) and ss:
        data = encode_image(os.path.join(run_dir, ss))
        if data:
            return f'<div class="ss-wrap"><div class="ss-label">📸 截图</div><img src="{data}" loading="lazy"></div>'
    # Handle dict with before/after (worker output format)
    if isinstance(ss, dict):
        parts = []
        for label, path in [("操作前", ss.get("before")), ("操作后", ss.get("after"))]:
            if path:
                data = encode_image(os.path.join(run_dir, path))
                if data:
                    parts.append(f'<div class="ss-wrap"><div class="ss-label">📸 {label}</div><img src="{data}" loading="lazy"></div>')
        return "".join(parts)
    return ""

def case_row(case, run_dir, compact=False):
    cid = case.get("id", "")
    status = case.get("status", "")
    si = {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "⚠️"}.get(status, "❓")
    desc = case.get("description") or case.get("name") or case.get("note", "")
    note = case.get("note", "")
    source = case.get("source", "")
    sys_name = case.get("system", "") or detect_system(case)

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
    # Fallback: if meta has sources but no cases tagged, use total as count
    if doc_cases == 0 and meta.get("sources", {}).get("document"):
        doc_cases = total
    if figma_cases == 0 and meta.get("sources", {}).get("figma"):
        figma_cases = total

    # Ring: circumference 2*pi*34 ≈ 213.6, dashoffset for remaining
    rate_offset = round(213.6 * (1 - rate / 100), 1)

    tz = timezone(timedelta(hours=8))
    # Use sum of case durations (accurate) instead of wall-clock gap
    total_ms = sum(r.get("duration_ms", 0) for r in results)
    if total_ms > 0:
        mins = int(total_ms // 60000)
        secs = int((total_ms % 60000) // 1000)
        duration = f"{mins}m {secs}s"
    else:
        duration = "N/A"

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
