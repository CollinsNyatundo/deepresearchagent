# ArcKit Investor Report

**Prepared:** 28 April 2026
**Repository:** [tractorjuice/arc-kit](https://github.com/tractorjuice/arc-kit)
**Founder/Maintainer:** Mark Craddock
**Licence:** MIT (open source)

---

## 1. Executive Summary

ArcKit is an open-source **AI-assisted Enterprise Architecture Governance & Vendor Procurement Toolkit**. In ~6.5 months since first publication (14 Oct 2025), it has grown to **1,702 GitHub stars, 201 forks, and is reportedly in use across the UK Government and NHS**. It distributes 68 slash commands across **six** AI assistant ecosystems (Claude Code, Codex CLI, Gemini CLI, OpenCode CLI, GitHub Copilot, plus a Python CLI), reaching architects wherever they already work.

The product converts hours of document drafting (requirements, business cases, risk registers, ADRs, Wardley Maps, RFP packs) into minutes of template-driven, audit-ready output — directly aligned with HM Treasury Green/Orange Book, GDS Service Standard, NCSC CAF, Technology Code of Practice, and G-Cloud/DOS procurement frameworks.

---

## 2. Repository Traction (GitHub)

| Metric | Value |
|---|---|
| **Stars** | **1,702** |
| **Forks** | **201** |
| Open issues | 21 |
| Repository created | 14 Oct 2025 |
| Repository age | ~6.5 months |
| Star velocity | ~260 stars/month average |
| Releases shipped | **100+** (latest: v4.9.4 on 28 Apr 2026) |
| Pull requests opened | **358+** |
| Most recent activity | Same day (28 Apr 2026) |

> Star growth has been steep: external coverage in February 2026 cited "over 580 stars" — the project has nearly **3× ed in two months** to reach 1,702.

---

## 3. Release Cadence & Engineering Velocity

- **100+ tagged releases** in 6 months — a release roughly every **~2 days**.
- Major version progression: **v0.x → v4.9.4** in 6 months, indicating rapid iteration with public versioning discipline.
- Recent milestones in the release stream:
  - v4.9.4 (28 Apr 2026) — current
  - v4.7.1 (19 Apr 2026)
  - v4.6.3 (06 Apr 2026)
  - v2.8.x series (late Feb 2026)
- **Automated multi-target distribution**: a single source command set is converted via `scripts/converter.py` into Claude Code plugin, Codex skills, Gemini extension TOML, OpenCode commands, and Copilot prompts — minimal marginal cost to add new AI ecosystems.

---

## 4. Product Footprint

| Asset | Count |
|---|---|
| Slash commands | **68** |
| Autonomous research agents | **10** (research, datascout, AWS/Azure/GCP, gov-reuse, grants, framework, etc.) |
| Document templates | **70+** |
| Command guides | **110+** |
| Automation hooks | 5 |
| Bundled MCP servers | AWS Knowledge, Microsoft Learn, Google Developer Knowledge, Data Commons, govreposcrape |
| Test/reference projects on GitHub | **22** (NHS, HMRC, MOD, ONS, Cabinet Office, DSTL, Plymouth, Scottish Courts, etc.) |
| Distribution formats | **6** (Claude plugin, Python CLI, Gemini, Codex, OpenCode, Copilot) |

---

## 5. Media & Community Coverage

### Owned channels

- **Medium publication ([medium.com/arckit](https://medium.com/arckit))** — dedicated publication. Notable posts:
  - *Announcing ArcKit: Free Enterprise Architecture Governance with AI*
  - *ArcKit 2.0 — Now a Claude Code Plugin*
  - *ArcKit v1.2.0: Autonomous Agents for Architecture Research*
  - *ArcKit v4: First-Class Codex and Gemini Support with Hooks, MCP Servers, and Native Policies*
  - *ArcKit v4.3.0: A Complete Wardley Mapping Suite for AI-Assisted Strategic Architecture*
  - *Claude Code Tips & Tricks*
- **arckit.org** — marketing site with getting-started, command reference, use cases, and guides.
- **LinkedIn group** for announcements and case studies (referenced from official site).

### Third-party coverage

- **Medevel.com** — feature article: *"ArcKit: Open-Source Enterprise Architecture Governance Toolkit for AI-Assisted Workflow, Compliance, and Healthcare IT"* (notes use across UK Government and NHS).
- **PyShine** — feature article: *"ArcKit: Enterprise Architecture Governance and Vendor Procurement Toolkit"*.
- **github/spec-kit Discussions #887** — listed in GitHub's Spec Kit "Show and tell" gallery (positions ArcKit as the architecture-governance counterpart to GitHub's Spec Kit lineage).
- **Independent Medium piece** by David R Oliver (Feb 2026): *"ArcKit — AI Toolkit for Solution & Enterprise Architects"* — first independent practitioner write-up.

### Mintlify-hosted documentation

- A separate hosted docs site at `tractorjuice-arc-kit-19.mintlify.app` is being trialled, suggesting investment in formal product documentation infrastructure.

---

## 6. Market Positioning

- **Adjacent to**, and explicitly inspired by, GitHub's **Spec Kit** — but targeting architects rather than developers.
- Multi-platform strategy hedges against any single AI vendor; ArcKit ships first-class for **all five mainstream AI coding assistants**.
- UK public-sector specialism is a **defensible niche**: built-in mappings to GDS Service Standard, TCoP, NCSC CAF, Orange/Green Book, G-Cloud and DOS — frameworks competitors have not codified.
- Reported usage across **UK Government and NHS** (per Medevel coverage) — a credibility signal worth validating with named case studies.

---

## 7. Risks & Watch-Items for Investors

- **Bus factor:** commit history shows **2 unique authors** in the local clone — concentration risk around founder Mark Craddock. Hiring or community-PR conversion is the obvious next step (358 PRs is healthy inbound signal).
- **Monetisation:** repo and toolkit are MIT-licensed and free; revenue model (hosted/enterprise/support/training/consulting) is not yet visible publicly.
- **Engagement depth:** the original Spec Kit "Show and tell" post received only 1 upvote and 0 replies — early traction has clearly come from elsewhere (Medium, LinkedIn, word-of-mouth in UK Gov circles).
- **Verification gap:** "used across UK Government and NHS" is third-party reported; named reference customers and case studies would materially strengthen the story.

---

## 8. Headline Numbers for a One-Pager

> **1,702 stars · 201 forks · 100+ releases · 358+ PRs · 68 commands · 10 agents · 6 AI platforms · ~6 months old · MIT.**

---

## Sources

- [GitHub repo: tractorjuice/arc-kit](https://github.com/tractorjuice/arc-kit)
- [arckit.org](https://arckit.org/)
- [ArcKit Medium publication](https://medium.com/arckit)
- [Announcing ArcKit (Medium)](https://medium.com/arckit/announcing-arckit-free-enterprise-architecture-governance-with-ai-131a63d7d391)
- [ArcKit 2.0 — Claude Code Plugin (Medium)](https://medium.com/arckit/arckit-2-0-now-a-claude-code-plugin-18a55f46828a)
- [ArcKit v0.9.1 — Complete AI Toolkit (Medium)](https://medium.com/arckit/arckit-v0-9-1-the-complete-ai-toolkit-for-enterprise-architects-6ad6227087e0)
- [ArcKit v1.2.0 Autonomous Agents (Medium)](https://medium.com/arckit/arckit-v1-2-0-autonomous-agents-for-architecture-research-355967dd8bd9)
- [ArcKit v4 — Codex & Gemini support (Medium)](https://medium.com/arckit/arckit-v4-first-class-codex-and-gemini-support-with-hooks-mcp-servers-and-native-policies-abdf9569e00e)
- [ArcKit v4.3.0 Wardley Mapping Suite (Medium)](https://medium.com/arckit/arckit-v4-3-0-a-complete-wardley-mapping-suite-for-ai-assisted-strategic-architecture-5848b36c0567)
- [Medevel feature article](https://medevel.com/arckit/)
- [PyShine feature article](https://pyshine.com/ArcKit-Enterprise-Architecture-Governance/)
- [github/spec-kit Discussion #887](https://github.com/github/spec-kit/discussions/887)
- [David R Oliver — independent review (Medium)](https://medium.com/@davidroliver/arckit-ai-toolkit-for-solution-enterprise-architects-528fa51c7c72)
