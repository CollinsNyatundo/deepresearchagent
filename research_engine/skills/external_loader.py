#!/usr/bin/env python3
"""External Skill Loader: parses ARC-Kit and PM-Skills repos into bundled skills.

Cloned repos are parsed to extract templates, commands, and skills which are then
registered as dynamic skills in the SkillRegistry.

Usage:
    from research_engine.skills.external_loader import ExternalSkillLoader
    loader = ExternalSkillLoader()
    registry = SkillRegistry()
    loader.register_all(registry, arc_kit_path=Path("external/arc-kit"), pm_path=Path("external/pm-skills"))
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from research_engine.skills.registry import BaseSkill, SkillRegistry
from research_engine.models import ResearchResult

logger = logging.getLogger(__name__)


class ExternalSkillLoader:
    """Loads skills from external repositories (ARC-Kit, PM-Skills)."""

    def load_arc_kit_skills(self, arc_kit_path: Path) -> list[BaseSkill]:
        """Parse ARC-Kit templates and create skills.

        Args:
            arc_kit_path: Path to cloned ARC-Kit repository.

        Returns:
            List of skills derived from ARC-Kit templates.
        """
        templates = self._find_arc_kit_templates(arc_kit_path)
        skills = []

        for template in templates:
            skill = self._template_to_skill(template, "arckit")
            if skill:
                skills.append(skill)

        logger.info(f"Loaded {len(skills)} skills from ARC-Kit")
        return skills

    def load_pm_skills(self, pm_path: Path) -> list[BaseSkill]:
        """Parse PM-Skills commands and create skills.

        Args:
            pm_path: Path to cloned PM-Skills repository.

        Returns:
            List of skills derived from PM-Skills commands.
        """
        commands = self._find_pm_skills(pm_path)
        skills = []

        for cmd in commands:
            skill = self._command_to_skill(cmd)
            if skill:
                skills.append(skill)

        logger.info(f"Loaded {len(skills)} skills from PM-Skills")
        return skills

    def register_all(
        self,
        registry: SkillRegistry,
        arc_kit_path: Path | None = None,
        pm_path: Path | None = None,
    ) -> None:
        """Register all external skills into a SkillRegistry.

        Args:
            registry: The SkillRegistry to register skills into.
            arc_kit_path: Optional path to ARC-Kit repo.
            pm_path: Optional path to PM-Skills repo.
        """
        if arc_kit_path and arc_kit_path.exists():
            for skill in self.load_arc_kit_skills(arc_kit_path):
                registry.register(skill)

        if pm_path and pm_path.exists():
            for skill in self.load_pm_skills(pm_path):
                registry.register(skill)

    def _find_arc_kit_templates(self, arc_kit_path: Path) -> list[dict[str, Any]]:
        """Find all markdown templates in ARC-Kit."""
        templates = []
        templates_dir = arc_kit_path / ".arckit" / "templates"

        if not templates_dir.exists():
            logger.warning(f"ARC-Kit templates directory not found: {templates_dir}")
            return templates

        for template_file in templates_dir.rglob("*.md"):
            name = template_file.stem.replace("-", " ").replace("_", " ").title()
            content = template_file.read_text(encoding="utf-8")[:500]
            templates.append({
                "name": name,
                "file": str(template_file.relative_to(arc_kit_path)),
                "content_preview": content,
            })

        return templates

    def _find_pm_skills(self, pm_path: Path) -> list[dict[str, Any]]:
        """Find all markdown commands in PM-Skills."""
        commands = []

        for plugin_dir in pm_path.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue

            commands_dir = plugin_dir / "commands"
            if commands_dir.exists():
                for cmd_file in commands_dir.rglob("*.md"):
                    name = cmd_file.stem.replace("-", " ").replace("_", " ").title()
                    content = cmd_file.read_text(encoding="utf-8")[:500]
                    commands.append({
                        "name": name,
                        "plugin": plugin_dir.name,
                        "file": str(cmd_file.relative_to(pm_path)),
                        "content_preview": content,
                    })

            skills_dir = plugin_dir / "skills"
            if skills_dir.exists():
                for skill_file in skills_dir.rglob("*.md"):
                    name = skill_file.stem.replace("-", " ").replace("_", " ").title()
                    content = skill_file.read_text(encoding="utf-8")[:500]
                    commands.append({
                        "name": name,
                        "plugin": plugin_dir.name,
                        "file": str(skill_file.relative_to(pm_path)),
                        "content_preview": content,
                    })

        return commands

    def _template_to_skill(self, template: dict, prefix: str) -> BaseSkill | None:
        """Convert an ARC-Kit template to a skill."""
        template_id = template["file"].replace("/", "_").replace(".", "_").lower()
        skill_id = f"{prefix}_{template_id}"

        # Determine audience based on template name
        audiences = ["cto", "architect"]
        if "security" in template_id or "risk" in template_id:
            audiences = ["cto", "architect", "ai_engineer"]
        elif "requirements" in template_id or "traceability" in template_id:
            audiences = ["cto", "architect", "dev"]
        elif "principles" in template_id or "governance" in template_id:
            audiences = ["cto", "executive"]

        class ArcKitSkill(BaseSkill):
            def __init__(self, id, name, description, template_file):
                super().__init__(
                    id=id,
                    name=name,
                    description=description,
                    category="technical",
                    formats=["technical"],
                    audiences=audiences,
                )
                self.template_file = template_file

            def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
                # Load template content and append to report
                try:
                    template_path = Path("external/arc-kit") / self.template_file
                    if template_path.exists():
                        template_content = template_path.read_text(encoding="utf-8")
                        result.report += f"\n\n---\n\n# {self.name}\n\n{template_content[:2000]}...\n"
                except Exception as e:
                    logger.warning(f"Could not load template {self.template_file}: {e}")
                return result

        return ArcKitSkill(
            id=skill_id,
            name=template["name"],
            description=f"ARC-Kit template: {template['name']}. {template['content_preview'][:100]}...",
            template_file=template["file"],
        )

    def _command_to_skill(self, cmd: dict) -> BaseSkill | None:
        """Convert a PM-Skills command to a skill."""
        cmd_id = cmd["file"].replace("/", "_").replace(".", "_").lower()
        skill_id = f"pm_{cmd_id}"

        # Determine audience based on command name
        audiences = ["pm", "founder"]
        if "growth" in cmd_id or "marketing" in cmd_id:
            audiences = ["pm", "growth", "founder"]
        elif "strategy" in cmd_id or "business" in cmd_id:
            audiences = ["pm", "founder", "executive"]
        elif "data" in cmd_id or "analytics" in cmd_id or "test" in cmd_id:
            audiences = ["pm", "analyst", "data_scientist"]
        elif "shipping" in cmd_id or "execution" in cmd_id:
            audiences = ["pm", "dev"]

        class PMSkill(BaseSkill):
            def __init__(self, id, name, description, cmd_file):
                super().__init__(
                    id=id,
                    name=name,
                    description=description,
                    category="product",
                    formats=["product"],
                    audiences=audiences,
                )
                self.cmd_file = cmd_file

            def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
                # Load command content and append to report
                try:
                    cmd_path = Path("external/pm-skills") / self.cmd_file
                    if cmd_path.exists():
                        cmd_content = cmd_path.read_text(encoding="utf-8")
                        result.report += f"\n\n---\n\n# {self.name}\n\n{cmd_content[:2000]}...\n"
                except Exception as e:
                    logger.warning(f"Could not load command {self.cmd_file}: {e}")
                return result

        return PMSkill(
            id=skill_id,
            name=cmd["name"],
            description=f"PM-Skill: {cmd['name']} (from {cmd['plugin']}). {cmd['content_preview'][:100]}...",
            cmd_file=cmd["file"],
        )
