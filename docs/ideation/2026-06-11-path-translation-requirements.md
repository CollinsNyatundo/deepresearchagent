---
date: 2026-06-11
topic: path-translation-shims
---

# Ideation Requirements: Unified OS-Agnostic Path Translation & Shim Layer

## Summary
POSIX-relative path normalization in the GitNexus/Graphify JSON payload (backend-to-frontend), combined with a separate setup CLI command to generate Windows `.cmd` shims and WSL bash wrappers for core tools (`gitnexus`, `ast-grep`) in user-space directories.

---

## Problem Frame
When developers run this project in a mixed Windows/WSL host environment, files and directories are indexed differently across the host boundary. 
The GitNexus index contains absolute or relative paths with mixed separators (Windows backslashes vs. WSL forward slashes), causing two main failures:
1. Graph visualization breaks: The React/G6 frontend fails to open files or highlight nodes because it cannot resolve file paths split using hardcoded slashes.
2. CLI tools fail: Subprocesses executing tools like `ast-grep` or `gitnexus` fail to resolve the command name because path mappings do not cross the boundary without manual symlinks/shims.

---

## Key Decisions
* **POSIX Graph Payload Normalization:** Normalize all file paths to POSIX-style relative paths from the repository root (e.g., `research_engine/api.py`) inside the Graphify/GitNexus JSON payloads.
* **Separated Setup CLI Utility:** Decouple shim generation from server startup, running it once during initial setup or environment configuration.
* **User-Space Installation:** Write `.cmd` shims to `%USERPROFILE%\.bin` and WSL bash wrappers to `$HOME/.local/bin` to prevent system administrator/root permission requirements.

---

## Requirements

### Path Normalization
- R1. Node and edge file paths served in the Graphify payload must be converted to POSIX-style relative paths from the repository root.
- R2. Path separators in payload file paths must be normalized to forward slashes `/`, regardless of whether the backend is running on Windows or WSL.
- R3. The backend `/api/open-file` API endpoint must receive POSIX-relative paths and translate them back to host-native absolute paths before invoking the local code editor.

### Shim & Wrapper Setup
- R4. An offline CLI setup script must detect the runtime OS environment (Windows or WSL) to write host-appropriate wrappers.
- R5. For Windows hosts, the script must generate `.cmd` text wrappers in `%USERPROFILE%\.bin` for `gitnexus` and `ast-grep` that execute the respective underlying commands.
- R6. For WSL environments, the script must write bash wrappers in `$HOME/.local/bin` pointing to the correct execution path.

---

## Scope Boundaries
* **PATH Variable Updates:** The tool will output instructions for adding the target directory to the system/shell `PATH` variable, but will not modify environment variables directly.
* **Core Tools Only:** Only `gitnexus` and `ast-grep` will have shims generated. Secondary or visual tools (like `vhs` or `silicon`) are excluded from the setup generator.
* **Subprocess Path Translation:** Arbitrary arguments passed to shell commands by the backend are not dynamically translated or rewritten by this layer.

---

## Acceptance Examples

### AE1. Graph Payload Separation
* **Given:** A node with a Windows path: `research_engine\knowledge_graph\gitnexus_bridge.py`
* **When:** The GitNexus graph bridge serializes nodes for the frontend
* **Then:** The `filePath` attribute in the returned JSON must be: `research_engine/knowledge_graph/gitnexus_bridge.py`

### AE2. File Opening Resolution
* **Given:** The frontend requests to open path `research_engine/api.py` on a Windows host
* **When:** The `/api/open-file` endpoint receives the request
* **Then:** The backend translates the path to `d:\Projects\ai-ml\DeepResearchAgent\research_engine\api.py` (or local workspace absolute path) before launching the editor.

---

## Sources / Research
* **Path split issue:** [gitnexus_bridge.py L411-412](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/knowledge_graph/gitnexus_bridge.py#L411-L412) splits by `/` directly:
  `src_node.file_path.split("/")[0]`
* **Command shims:** Reference wrappers established during the [ce-setup script](file:///C:/Users/COLLINS/.gemini/config/plugins/compound-engineering/skills/ce-setup/scripts/check-health).
