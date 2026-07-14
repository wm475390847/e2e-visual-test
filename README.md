# E2E Visual Test

> 浏览器快照驱动的端到端可视化测试技能，面向多平台 SaaS 系统的回归测试。

[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://docs.openclaw.ai)

## 概述

E2E Visual Test 是一个基于 **浏览器 ARIA 快照 + Figma 设计稿 + 需求文档** 三源交叉验证的自动化测试技能。它不依赖 Selenium 或 Playwright 脚本编写用例，而是通过 AI 分析页面可访问性文本快照来判断用例通过与否，截图仅用于人工复查。

### 核心理念

- 🤖 **AI 驱动断言**：不写断言代码，由 AI 对比快照文本判断元素存在性、状态变更、文案正确性
- 📐 **Figma 设计验证**：自动对比设计稿与实际页面，发现 UI 回归
- 📝 **需求文档驱动**：从需求文档提取业务流程，自动生成 CRUD 三连用例
- 🔄 **单 Worker 串行**：一个进程严格按顺序执行，无竞态，链路清晰可追溯
- 📊 **HTML 可视化报告**：自包含报告，截图 base64 嵌入，一键分享

## 工作流

```
Phase 1         Phase 2            Phase 3         Phase 4           Phase 5
┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│  Init   │ -> │ 用例生成      │ -> │ 统一登录  │ -> │ Worker执行 │ -> │ 报告生成  │
│         │    │ Figma+需求    │    │ 多平台   │    │ 单Worker   │    │ HTML     │
│ 创建目录 │    │ 纯文档分析    │    │ 认证     │    │ 串行验证   │    │ 可视化   │
└─────────┘    └─────────────┘    └──────────┘    └───────────┘    └──────────┘
  不开浏览器      不碰浏览器                     一个Chrome实例        自包含报告
```

| 阶段 | 脚本 | 说明 |
|------|------|------|
| **Init** | `scripts/init.py` | 生成 UUID，创建测试工作目录 |
| **用例生成** | AI 驱动 | 并行拉取 Figma 设计稿 + 需求文档，交叉对比生成用例 |
| **统一登录** | 浏览器操作 | 一个 Chrome 实例多 tab 登录所有平台 |
| **Worker 执行** | `sessions_spawn` | 单 Worker 严格按 flow 顺序串行执行，实时写入结果 |
| **报告生成** | `scripts/merge.py` + `scripts/report.py` | 合并结果，生成自包含 HTML 报告 |

## 用例来源

```
           ┌──────────┐
           │ 用户指定  │ ← 最高优先级，手动覆盖
           └────┬─────┘
                ▼
        ┌──────────────┐
        │ Figma 设计稿  │ ← 自动发现组件、交互状态、弹窗
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │ 需求文档      │ ← 提取业务流程、字段、校验规则
        └──────────────┘
               │
               ▼
         三源去重合并 → test-plan.yaml
```

### 自动生成的用例类型

- **页面基础**：标题、导航、表头、核心组件存在性
- **交互操作**：按钮点击、表单输入、搜索、下拉选择、标签切换
- **CRUD 三连**：Create → Verify → Cleanup（带 `e2e_` 前缀标识，不污染真实数据）
- **表单校验**：必填字段、格式校验（邮箱、手机号等）
- **状态验证**：启用/禁用态、弹窗文案、开关切换
- **分页功能**：翻页、跳页、每页条数切换
- **跨平台联动**：管理员创建 → 企业端验证

## 目录结构

```
e2e-visual-test/
├── SKILL.md                      # OpenClaw 技能定义（5阶段流程）
├── README.md                     # 本文件
├── scripts/
│   ├── init.py                   # 初始化：生成 UUID，创建测试目录
│   ├── merge.py                  # 合并多个 results-*.yaml
│   └── report.py                 # 生成自包含 HTML 报告
├── references/
│   ├── test-plan-schema.md       # YAML 数据格式规范
│   └── figma-integration.md      # Figma 集成与用例生成策略
└── assets/
    └── report-template.html      # 报告 HTML 模板
```

## 快速开始

### 测试输出示例

```
UUID: 3bbaab69-fe86-449e-858a-3bc724a9d6bf

📋 Phase 1: Init ✅
📐 Phase 2: 用例生成（Figma + 需求文档）→ 34 用例 13 flow ✅
🔐 Phase 3: 统一登录 → 2 平台已认证 ✅
👷 Phase 4: Worker 执行 → 单 Worker 串行 ✅

========================================
  E2E 全量测试报告
========================================
  总计: 34  |  ✅ 通过: 27  |  ❌ 失败: 1  |  ⏭️ 跳过: 6
  通过率: 96.4%
📊 报告: report.html
```

### 输入格式

```
# Token
/e2e https://example.com/login
/e2e https://example.com 1.验证页面标题 2.搜索用户"test" 3.验证搜索结果
/e2e https://example.com --figma=https://figma.com/file/xxx

# 查看报告
/e2e-report {uuid}

# 查看历史
/e2e-list
```

## 配置

在首次使用时通过对话指定：

```yaml
# meta.yaml
admin:
  url: https://admin.example.com
  login_url: https://admin.example.com/login
  email: admin@example.com
  password: your-password

enterprise:
  url: https://enterprise.example.com
  login_url: https://enterprise.example.com/login
  email: user@example.com
  password: your-password
```

## 安全策略

| 允许 ✅ | 禁止 ❌ |
|---------|---------|
| 创建 `e2e_` 前缀测试数据 | 删除/修改非自建数据 |
| 表单提交（测试值） | 保存 SSO/安全配置 |
| 删除 `e2e_` 前缀自建数据 | 操作真实用户账号 |
| 页面快照 + 截图 | 退出登录、重置密码 |

## 为什么是单 Worker 串行

| 维度 | 单 Worker 串行 | 多 Worker 并行 |
|------|---------------|---------------|
| 浏览器状态 | 一个 tab 逐步走，完全可控 | 多 tab 争抢，状态不可预期 |
| Case 间依赖 | 严格顺序，Create→Verify→Cleanup 可靠 | 竞态：B 可能访问 A 尚未创建的数据 |
| 调试效率 | 一条链路清晰可追溯 | 多结果文件分散，难以定位 |
| 实际效率 | ~2 分钟跑完 30+ 用例 | 并行优势有限，引入同步复杂度 |

## 依赖

- **OpenClaw** （Agent 运行时）
- **Chrome/Chromium** （浏览器引擎，CTP 协议）
- **Python 3** （`init.py`, `merge.py`, `report.py`）
- **PyYAML** （Python 脚本依赖）
- 可选：Figma API 访问权限（用于设计稿数据拉取）

## License

MIT
