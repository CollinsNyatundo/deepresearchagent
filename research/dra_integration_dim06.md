# Dimension 06: Docker Sandbox Security & Code Execution

## Overview

This dimension investigates the security, infrastructure, and operational implications of adding Docker-based sandboxed code execution to DRA. Based on AI-Researcher's architecture, it covers security models, resource isolation, and alternatives.

---

## Key Findings

### 1. Docker Adds Significant Infrastructure Complexity

**Claim:** Docker requires a daemon running as root, container images, and persistent storage. Adding Docker to DRA's architecture fundamentally changes it from a simple FastAPI app to a container orchestration system.[^1]

**Source:** Docker Documentation

**URL:** https://docs.docker.com/engine/

**Date:** 2026

**Excerpt:**
> "The Docker daemon is the background service running on the host that manages building, running and distributing Docker containers."

**Context:** DRA's current architecture (FastAPI + BackgroundTasks + Supabase) is lightweight and deployable anywhere (Vercel, Railway, Heroku). Adding Docker sandbox execution means:
- Cannot deploy on serverless platforms (Vercel, Netlify Functions)
- Requires a VM or dedicated server with Docker installed
- Needs Docker daemon monitoring (restart on crash, log rotation)
- Adds image storage and build complexity

The DRA plan says Docker is P3 (highest effort), but the infrastructure implications should be acknowledged explicitly.

**Confidence:** High

---

### 2. AI-Researcher's Docker Architecture Has Known Issues

**Claim:** AI-Researcher's GitHub issues show users struggling with Docker setup, container mounting, and script execution paths.[^2]

**Source:** GitHub Issues on HKUDS/AI-Researcher

**URL:** https://github.com/HKUDS/AI-Researcher/issues/21

**Date:** 2025-03-20

**Excerpt:**
> "请问您是将项目clone到app里面去做的吗" / "没有没有，我是在docker挂载了本地的ai-research文件夹到workplace后，运行research_agent文件夹里的run_infer_level_1.sh" / "不需要挂载，pull好docker后直接运行sh脚本就行了呀"

**Context:** Users are confused about whether to mount local directories, clone inside containers, or use pre-built images. This indicates Docker integration is not trivial. DRA's target audience (developers, indie hackers) may not have Docker expertise.

**Confidence:** High

---

**Claim:** AI-Researcher uses a specific base image (`tjbtech1/airesearcher:v1`) and requires GPU configuration, adding further complexity.[^3]

**Source:** AI-Researcher GitHub README

**URL:** https://github.com/HKUDS/AI-Researcher

**Date:** 2025

**Excerpt:**
> "BASE_IMAGES=tjbtech1/airesearcher:v1. GPUS='"device=0"'."

**Context:** GPU passthrough requires nvidia-docker runtime, which is only available on Linux with NVIDIA drivers. Windows and macOS users cannot use GPU features. DRA's sandbox should support CPU-only mode as a fallback.

**Confidence:** High

---

### 3. Sandbox Security is Hard

**Claim:** Docker containers are not true security boundaries. Container escapes are a known class of vulnerabilities, and running arbitrary user code in containers is risky.[^4]

**Source:** NIST Container Security Guide

**URL:** https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf

**Date:** 2026

**Excerpt:**
> "Containers are not a silver bullet for security. They share the host kernel, and a vulnerability in the kernel can lead to container escape."

**Context:** The DRA plan mentions "security.py" with "network isolation, filesystem restrictions, privilege dropping" but these are complex to implement correctly. Even with seccomp, AppArmor, and read-only filesystems, a determined attacker can potentially escape.

For a research platform that may be used by untrusted users, running arbitrary code is a significant risk. DRA should consider:
- gVisor (Google's user-space kernel) for stronger isolation
- Firecracker (AWS microVMs) for VM-level isolation
- WebAssembly (WASM) for lightweight, safe sandboxing
- Or simply not supporting arbitrary code execution

**Confidence:** High

---

**Claim:** Firecracker microVMs provide VM-level isolation in ~125ms startup time, making them suitable for sandboxed code execution.[^5]

**Source:** AWS Firecracker Documentation

**URL:** https://firecracker-microvm.github.io/

**Date:** 2026

**Excerpt:**
> "Firecracker is an open source virtualization technology that is purpose-built for creating and managing secure, multi-tenant container and function-based services."

**Context:** Firecracker is used by AWS Lambda and Fargate. It's more secure than Docker but requires more setup. For DRA's use case (research experiments, not high-frequency function execution), Firecracker may be overkill.

**Confidence:** Medium

---

### 4. Alternatives to Docker Sandbox

**Claim:** WebAssembly (WASM) with wasmtime or wasmer provides near-native performance with strong sandboxing, no Docker daemon, and sub-millisecond startup.[^6]

**Source:** WebAssembly Runtime Documentation

**URL:** https://wasmtime.dev/

**Date:** 2026

**Excerpt:**
> "Wasmtime is a standalone wasm-only optimizing runtime for WebAssembly."

**Context:** WASM is increasingly used for sandboxed code execution (e.g., GitHub Actions, Cloudflare Workers). For DRA's research experiments, Python code could be compiled to WASM (via pyodide or rustpython) and executed safely. However, this limits available libraries and may not support scientific computing (numpy, pandas, matplotlib).

**Confidence:** Medium

---

**Claim:** Restricted Python interpreters (RestrictedPython, PyPy sandbox) can execute Python code with limited builtins and no filesystem/network access.[^7]

**Source:** RestrictedPython Documentation (Zope Foundation)

**URL:** https://restrictedpython.readthedocs.io/en/latest/

**Date:** 2026

**Excerpt:**
> "RestrictedPython is a tool that helps to define a subset of Python which allows to provide a Python input interface but without security issues."

**Context:** RestrictedPython is simpler than Docker but also more limited. It cannot run matplotlib (requires filesystem access for output), pandas (requires file I/O), or network requests. For DRA's research experiments, this may be too restrictive.

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Security vs. Functionality

Docker provides full Linux userspace (Python, R, Julia, matplotlib, numpy) but weak security boundaries. WASM provides strong security but limited library support. RestrictedPython is simple but too limited for research.

**Counter-argument:** For DRA's use case, the best approach may be a **hybrid**:
- **Phase 1:** Don't support arbitrary code execution. Instead, support "static analysis" (code review, syntax check, type inference) without execution.
- **Phase 2:** Add a simple Python sandbox using RestrictedPython for safe code analysis (no execution).
- **Phase 3:** Add optional Docker sandbox for users who need it, with strong warnings about security and infrastructure requirements.

### Tension 2: Infrastructure Cost vs. User Value

Running Docker containers requires:
- A server with Docker installed (not serverless)
- Sufficient RAM for containers (1GB+ per container)
- CPU cores for concurrent experiments
- Disk space for images and artifacts

For a small SaaS, this may cost $50-$200/month in infrastructure. The DRA plan does not mention this cost.

**Counter-argument:** If only 5% of users need sandboxed execution, the infrastructure cost may not be justified. A better model: allow users to download the experiment code and run it locally, then upload results back to DRA.

### Tension 3: AI-Researcher's Scope vs. DRA's Scope

AI-Researcher is a research automation tool that generates and validates novel algorithms. It needs sandboxed execution to run experiments. DRA is a web research tool that synthesizes existing information. It does not generate novel algorithms that need validation.

**Counter-argument:** The DRA plan says sandbox execution is for "experimental validation" but it's unclear what experiments DRA users would run. DRA produces research reports, not executable code. Unless DRA is expanding into algorithm generation (a major scope change), sandboxed execution may not be needed.

---

## Recommendations

### 1. Defer Docker Sandbox Indefinitely

DRA's core value proposition is web research synthesis. Sandboxed code execution is not essential to this. The P3 effort estimate (3-4 weeks) is better spent on:
- Citation verification (P0)
- Export formats (P2)
- Public API integrations (P2)

### 2. If Sandbox is Needed Later, Use WASM

When sandboxed execution is genuinely needed, use WebAssembly (Pyodide for Python in browser, or wasmtime on server) rather than Docker. It provides better security without infrastructure complexity.

### 3. Immediate Alternative: Code Analysis Without Execution

Instead of running code, DRA can:
- Use `py_compile` for syntax checking
- Use `mypy` or `pyright` for type analysis
- Use `ast` module for structural analysis
- Use `bandit` for security scanning

These provide research value without execution risk.

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| Docker adds significant infrastructure complexity | High |
| AI-Researcher has known Docker setup issues | High |
| Docker containers are not true security boundaries | High |
| WASM is a lighter alternative | Medium |
| RestrictedPython is too limited for research | High |
| DRA may not need sandboxed execution at all | High |

---

## Sources

[^1]: Docker Engine Documentation. 2026. https://docs.docker.com/engine/

[^2]: AI-Researcher GitHub Issues. 2025. https://github.com/HKUDS/AI-Researcher/issues/21

[^3]: AI-Researcher README. 2025. https://github.com/HKUDS/AI-Researcher

[^4]: NIST Container Security Guide (SP 800-190). 2026. https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf

[^5]: AWS Firecracker Documentation. 2026. https://firecracker-microvm.github.io/

[^6]: Wasmtime Documentation. 2026. https://wasmtime.dev/

[^7]: RestrictedPython Documentation. 2026. https://restrictedpython.readthedocs.io/en/latest/

