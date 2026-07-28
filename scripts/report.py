#!/usr/bin/env python3
"""Generate self-contained HTML report from results.yaml + screenshots.
Fully config-driven: systems, modules, classification rules all from meta.yaml.
"""
import sys, os, base64, yaml, re, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# ── Color palette ──────────────────────────────────────
SYSTEM_PALETTE = [
    ("#6366f1", "#eef2ff"), ("#10b981", "#ecfdf5"), ("#f59e0b", "#fffbeb"),
    ("#ef4444", "#fef2f2"), ("#8b5cf6", "#f5f3ff"), ("#06b6d4", "#ecfeff"),
    ("#ec4899", "#fdf2f8"), ("#84cc16", "#f2ffe6"), ("#f97316", "#fff7ed"),
    ("#14b8a6", "#f0fdfa"), ("#3b82f6", "#eff6ff"), ("#a855f7", "#faf5ff"),
]

DEFAULT_SKIP_KEYWORDS = [
    "退出登录", "登出", "注销", "删除", "移除", "禁用", "封禁",
    "logout", "sign out", "delete", "remove", "disable", "ban",
]

# ── Helpers ────────────────────────────────────────────
def _color_for_index(i):
    return SYSTEM_PALETTE[i % len(SYSTEM_PALETTE)]

def _hash_color(name):
    """Deterministic color from system name."""
    h = hashlib.md5(name.encode()).hexdigest()
    idx = int(h[:4], 16) % len(SYSTEM_PALETTE)
    return SYSTEM_PALETTE[idx]

def encode_image(path):
    p = Path(path)
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = p.suffix.lower().replace(".", "")
    return f"data:image/{ext};base64,{b64}"

def _resolve_system_color(system_name, meta):
    """Look up color from meta.systems config, or derive from name."""
    for i, s in enumerate(meta.get("systems", [])):
        if s.get("name") == system_name:
            if s.get("color"):
                return s["color"], SYSTEM_PALETTE[i % len(SYSTEM_PALETTE)][1]
            return _color_for_index(i)
    return _hash_color(system_name)

# ── Safe: no eval / no exec ────────────────────────────
def _match_pattern(value, pattern):
    """Safe pattern matching: supports string, [min,max] range, regex.
    No eval/exec — only safe transformations.
    """
    if isinstance(pattern, str):
        return bool(re.search(pattern, value, re.I))
    if isinstance(pattern, list) and len(pattern) == 2:
        try:
            m = re.match(r'TC-(\d+)', value)
            if m:
                n = int(m.group(1))
                return pattern[0] <= n <= pattern[1]
        except (ValueError, TypeError):
            pass
    return False

# ── Module classification (config-driven) ──────────────
def classify(case, meta):
    """Return (system_name, module_key, module_label, module_icon)
    All rules driven by meta.yaml.modules config.
    """
    cid = case.get("id", "")
    desc = (case.get("description") or "").lower()
    note = (case.get("note") or "").lower()
    desc_text = desc + " " + note

    # 1. Explicit fields take priority
    system = case.get("system", "")
    module_key = case.get("module", "")

    # 2. Resolve from meta.modules config
    modules_config = meta.get("modules", [])
    if not modules_config:
        # Fallback: bare keyword matching
        system = system or _detect_system_fallback(case, meta)
        module_key = module_key or _detect_module_fallback(case, meta)
        return system, module_key, module_key, "📋"

    matched_mod = None
    for mod in modules_config:
        mod_system = mod.get("system", "")
        mod_key = mod.get("key", "")

        # Match by explicit fields
        if system and mod_system and system == mod_system and module_key == mod_key:
            matched_mod = mod
            break
        if module_key and module_key == mod_key:
            matched_mod = mod
            break

        # Match by keyword
        for kw in mod.get("keywords", []):
            if _match_pattern(desc_text, kw) or _match_pattern(cid, kw):
                matched_mod = mod
                break
        if matched_mod:
            break

        # Match by TC-ID range
        for rng in mod.get("tc_range", []):
            if isinstance(rng, list) and len(rng) == 2:
                try:
                    m = re.match(r'(?:TC-)?(\d+)', cid)
                    if m:
                        n = int(m.group(1))
                        if rng[0] <= n <= rng[1]:
                            matched_mod = mod
                            break
                except (ValueError, TypeError):
                    pass
        if matched_mod:
            break

    if matched_mod:
        system = system or matched_mod.get("system", "")
        module_key = module_key or matched_mod.get("key", "")
        module_label = matched_mod.get("label", module_key or "其他")
        module_icon = matched_mod.get("icon", "📋")
    else:
        system = system or _detect_system_fallback(case, meta)
        module_key = module_key or _detect_module_fallback(case, meta)
        module_label = module_key or "其他"
        module_icon = "📋"

    system = system or "默认"
    return system, module_key, module_label, module_icon


def _detect_system_fallback(case, meta):
    """Minimal fallback when no modules config: try case.system, then meta.systems[0]."""
    systems = meta.get("systems", [])
    if systems:
        return systems[0].get("name", "默认")
    return "默认"


def _detect_module_fallback(case, meta):
    """Minimal fallback module key."""
    cid = case.get("id", "")
    desc = (case.get("description") or "").lower()
    # Try to extract from TC-ID prefix (e.g. TC-TM-001 → tm)
    m = re.match(r'TC-(\w+)-', cid)
    if m:
        return m.group(1).lower()
    return "other"

# ── Platform cards ─────────────────────────────────────
def platform_cards(meta):
    systems = meta.get("systems", [])
    if not systems:
        # Legacy accounts / admins fallback
        accounts = meta.get("accounts", [])
        if accounts:
            parts = []
            for i, a in enumerate(accounts):
                c, _ = _color_for_index(i)
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
        # Legacy old format
        for key in ["admin", "enterprise"]:
            if key in meta:
                color, _ = _color_for_index(0 if key == "admin" else 1)
                name = meta[key].get("nickname", "管理员平台" if key == "admin" else "企业平台")
                return f'''
        <div class="plat-row">
          <span class="plat-dot" style="background:{color}"></span>
          <span class="plat-name">{name}</span>
          <code class="plat-url">{meta[key].get("url","")}</code>
        </div>
        <div class="plat-acct">👤 {meta[key].get("email","")}</div>'''
        return f"<div>目标: {meta.get('url', '')}</div>"

    parts = []
    for i, s in enumerate(systems):
        c, _ = _color_for_index(i)
        # Allow per-system color override
        if s.get("color"):
            c = s["color"]
        parts.append(f'''
        <div class="plat-row">
          <span class="plat-dot" style="background:{c}"></span>
          <span class="plat-name">{s["name"]}</span>
          <code class="plat-url">{s.get("url","")}</code>
        </div>
        <div class="plat-acct">👤 {s.get("account", s.get("email",""))}</div>''')
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

# ── Case rendering ─────────────────────────────────────
def case_screenshot(case, run_dir):
    ss = case.get("screenshot") or case.get("screenshots")
    if isinstance(ss, str) and ss:
        data = encode_image(os.path.join(run_dir, ss))
        if data:
            return f'<div class="ss-wrap"><div class="ss-label">📸 截图</div><img src="{data}" loading="lazy"></div>'
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
    sys_name = case.get("system", "")

    tag = ""
    if source == "document":
        tag = '<span class="tag tag-doc">文档</span>'
    elif source == "figma":
        tag = '<span class="tag tag-figma">Figma</span>'

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
      {f'<span>📋 {sys_name}</span>' if sys_name else ''}
      {tag}
    </div>
    {f'<p class="ci-note-text">{note}</p>' if note else ''}
    {case_screenshot(case, run_dir)}
  </div>
</div>'''


# ── Module cards (config-driven) ───────────────────────
def module_cards(results, meta, run_dir):
    groups = defaultdict(list)
    for r in results:
        system, mod_key, mod_label, mod_icon = classify(r, meta)
        groups[(system, mod_key, mod_label, mod_icon)].append(r)

    # Build display order from meta.modules
    modules_config = meta.get("modules", [])
    order_map = {}
    if modules_config:
        for mod in modules_config:
            key_tuple = (
                mod.get("system", ""),
                mod.get("key", ""),
                mod.get("label", mod.get("key", "")),
                mod.get("icon", "📋"),
            )
            order_map[key_tuple] = mod.get("order", 999)

    # Sort: configured order first, then alphabetical
    def sort_key(item):
        key_tuple, _ = item
        return (order_map.get(key_tuple, 999), key_tuple[0], key_tuple[2])

    sorted_groups = sorted(groups.items(), key=sort_key)

    cards = []
    for key, cases in sorted_groups:
        system, mod_key, mod_label, mod_icon = key
        total = len(cases)
        passed = sum(1 for c in cases if c["status"] == "pass")
        failed = sum(1 for c in cases if c["status"] == "fail")
        skipped = sum(1 for c in cases if c["status"] == "skip")
        pct = round(passed / total * 100) if total > 0 else 0
        pct_class = "good" if pct >= 100 else ("warn" if pct >= 80 else "bad")
        sys_color, _ = _resolve_system_color(system, meta)

        rows = "".join(case_row(c, run_dir, compact=True) for c in cases)

        cards.append(f'''
<div class="mod-card">
  <div class="mc-hd" onclick="this.parentElement.classList.toggle('open')" style="border-left:4px solid {sys_color}">
    <span class="mc-icon">{mod_icon}</span>
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

    return "".join(cards), len(groups)


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

    # Source stats from explicit case tags
    doc_cases = sum(1 for r in results if r.get("source") == "document")
    figma_cases = sum(1 for r in results if r.get("source") == "figma")
    if doc_cases == 0 and meta.get("sources", {}).get("document"):
        doc_cases = total
    if figma_cases == 0 and meta.get("sources", {}).get("figma"):
        figma_cases = total

    rate_offset = round(213.6 * (1 - rate / 100), 1)

    tz = timezone(timedelta(hours=8))
    total_ms = sum(r.get("duration_ms", 0) for r in results)
    if total_ms > 0:
        mins = int(total_ms // 60000)
        secs = int((total_ms % 60000) // 1000)
        duration = f"{mins}m {secs}s"
    else:
        duration = "N/A"

    mod_cards_html, module_count = module_cards(results, meta, run_dir)

    with open(os.path.join(os.path.dirname(__file__), "..", "assets", "report-template.html")) as f:
        tpl = f.read()

    html = tpl
    html = html.replace("{{UUID}}", run_id)
    html = html.replace("{{TITLE}}", meta.get("title", ""))
    html = html.replace("{{SUBTITLE}}", "E2E 测试报告")
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
