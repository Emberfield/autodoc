"""
SKILL.md generator for context packs.

This module generates SKILL.md files from context packs, making pack knowledge
discoverable by Claude Code, OpenAI Codex, and other AI assistants.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillFormat(Enum):
    """Output format for skill files."""

    CLAUDE = "claude"  # .claude/skills/
    CODEX = "codex"  # ~/.codex/skills/


@dataclass
class SkillConfig:
    """Configuration for skill generation."""

    format: SkillFormat = SkillFormat.CLAUDE
    include_reference: bool = False
    output_dir: Optional[Path] = None
    max_description_length: int = 200

    def get_output_dir(self, project_root: Path) -> Path:
        """Get the output directory for skills."""
        if self.output_dir:
            return self.output_dir

        if self.format == SkillFormat.CLAUDE:
            return project_root / ".claude" / "skills"
        else:  # CODEX
            return Path.home() / ".codex" / "skills"


@dataclass
class GeneratedSkill:
    """Result of skill generation."""

    skill_name: str
    skill_path: Path
    skill_content: str
    reference_files: Dict[str, str] = field(default_factory=dict)


class SkillGenerator:
    """
    Generates SKILL.md files from context packs.

    The SKILL.md format is a shared format used by Claude Code and OpenAI Codex
    for AI-discoverable skills. It consists of YAML frontmatter (name, description)
    followed by Markdown instructions.
    """

    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()

    def generate_skill_name(self, pack_name: str) -> str:
        """
        Normalize pack name to lowercase-hyphenated skill name.

        Examples:
            API_Layer -> api-layer
            AuthenticationSystem -> authentication-system
            my_cool_pack -> my-cool-pack
        """
        # Replace underscores with hyphens
        name = pack_name.replace("_", "-")

        # Insert hyphens before uppercase letters (for camelCase)
        name = re.sub(r"([a-z])([A-Z])", r"\1-\2", name)

        # Convert to lowercase
        name = name.lower()

        # Remove any non-alphanumeric characters except hyphens
        name = re.sub(r"[^a-z0-9-]", "", name)

        # Remove consecutive hyphens
        name = re.sub(r"-+", "-", name)

        # Strip leading/trailing hyphens
        return name.strip("-")

    def generate_description(self, pack_data: Dict[str, Any]) -> str:
        """
        Generate a discoverable description for the SKILL.md frontmatter.

        Combines pack description with use cases and key components for
        better AI discoverability. Falls back to entity data if no LLM summary.
        """
        parts = []

        # Start with pack description
        description = pack_data.get("description", "")
        if description:
            parts.append(description.strip())

        # Add use cases from llm_summary if available
        llm_summary = pack_data.get("llm_summary", {})
        if llm_summary:
            usage_patterns = llm_summary.get("usage_patterns", [])
            if usage_patterns and len(usage_patterns) > 0:
                # Add first usage pattern as use case hint
                first_pattern = usage_patterns[0]
                if isinstance(first_pattern, str):
                    parts.append(f"Use when {first_pattern.lower()}.")

            # Add key components
            key_components = llm_summary.get("key_components", [])
            if key_components:
                component_names = []
                for comp in key_components[:3]:  # Limit to 3
                    if isinstance(comp, dict):
                        component_names.append(comp.get("name", ""))
                    elif isinstance(comp, str):
                        component_names.append(comp)

                component_names = [n for n in component_names if n]
                if component_names:
                    parts.append(f"Key capabilities: {', '.join(component_names)}.")
        else:
            # Fallback: generate description from entities
            entities = pack_data.get("entities", [])
            if entities:
                classes = [e for e in entities if e.get("type") == "class" or e.get("entity_type") == "class"]
                functions = [e for e in entities if e.get("type") == "function" or e.get("entity_type") == "function"]

                entity_summary = []
                if classes:
                    entity_summary.append(f"{len(classes)} classes")
                if functions:
                    entity_summary.append(f"{len(functions)} functions")

                if entity_summary:
                    parts.append(f"Contains {', '.join(entity_summary)}.")

                # Add first few class/function names as hints
                key_names = [c.get("name") for c in classes[:2] if c.get("name")]
                key_names += [f.get("name") for f in functions[:2] if f.get("name") and not f.get("name", "").startswith("_")]
                if key_names:
                    parts.append(f"Includes: {', '.join(key_names[:4])}.")

        # Join and truncate
        full_description = " ".join(parts)

        if len(full_description) > self.config.max_description_length:
            # Truncate at word boundary
            truncated = full_description[: self.config.max_description_length - 3]
            last_space = truncated.rfind(" ")
            if last_space > 0:
                truncated = truncated[:last_space]
            return truncated + "..."

        return full_description

    def generate_skill_content(self, pack_data: Dict[str, Any]) -> str:
        """
        Generate the full SKILL.md content from pack data.

        Returns a Markdown string with YAML frontmatter.
        Works with or without LLM summaries - falls back to entity data.
        """
        skill_name = self.generate_skill_name(pack_data.get("name", "unnamed"))
        description = self.generate_description(pack_data)

        # Build content sections
        sections = []

        # YAML frontmatter
        sections.append("---")
        sections.append(f"name: {skill_name}")
        sections.append(f"description: {description}")
        sections.append("---")
        sections.append("")

        # Title
        display_name = pack_data.get("display_name", pack_data.get("name", "Unnamed Pack"))
        sections.append(f"# {display_name}")
        sections.append("")

        # Instructions section
        llm_summary = pack_data.get("llm_summary", {})
        entities = pack_data.get("entities", [])

        # Architecture/overview
        architecture = llm_summary.get("architecture", "")
        pack_description = pack_data.get("description", "")
        if architecture:
            sections.append("## Overview")
            sections.append("")
            sections.append(architecture)
            sections.append("")
        elif pack_description:
            # Fallback: use pack description
            sections.append("## Overview")
            sections.append("")
            sections.append(pack_description)
            sections.append("")

        # File locations
        files = pack_data.get("files", [])
        if files:
            sections.append("## File Locations")
            sections.append("")
            for file_pattern in files[:10]:  # Limit to 10
                sections.append(f"- `{file_pattern}`")
            if len(files) > 10:
                sections.append(f"- ... and {len(files) - 10} more")
            sections.append("")

        # Usage patterns / How to Use
        usage_patterns = llm_summary.get("usage_patterns", [])
        if usage_patterns:
            sections.append("## How to Use")
            sections.append("")
            for pattern in usage_patterns:
                if isinstance(pattern, str):
                    sections.append(f"- {pattern}")
                elif isinstance(pattern, dict):
                    pattern_desc = pattern.get("description", pattern.get("pattern", ""))
                    if pattern_desc:
                        sections.append(f"- {pattern_desc}")
            sections.append("")

        # Key Components table - use LLM summary or fall back to entities
        key_components = llm_summary.get("key_components", [])
        if key_components:
            sections.append("## Key Components")
            sections.append("")
            sections.append("| Component | Role |")
            sections.append("|-----------|------|")

            for comp in key_components:
                if isinstance(comp, dict):
                    name = comp.get("name", "Unknown")
                    role = comp.get("role", comp.get("description", ""))
                    sections.append(f"| `{name}` | {role} |")
                elif isinstance(comp, str):
                    sections.append(f"| `{comp}` | - |")

            sections.append("")
        elif entities and not llm_summary:
            # Fallback: generate key components from entities
            sections.append("## Key Components")
            sections.append("")
            sections.append("| Component | Type | Description |")
            sections.append("|-----------|------|-------------|")

            # Get classes first, then important functions
            classes = [e for e in entities if e.get("type") == "class" or e.get("entity_type") == "class"]
            functions = [e for e in entities if e.get("type") == "function" or e.get("entity_type") == "function"]

            # Show up to 5 classes and 5 functions
            for entity in classes[:5]:
                name = entity.get("name", "Unknown")
                docstring = entity.get("docstring", "")
                desc = docstring.split("\n")[0][:60] if docstring else "-"
                sections.append(f"| `{name}` | class | {desc} |")

            for entity in functions[:5]:
                name = entity.get("name", "Unknown")
                if name.startswith("_"):  # Skip private functions
                    continue
                docstring = entity.get("docstring", "")
                desc = docstring.split("\n")[0][:60] if docstring else "-"
                sections.append(f"| `{name}` | function | {desc} |")

            sections.append("")

        # Security notes (for critical/high security packs)
        security_level = pack_data.get("security_level", "normal")
        security_notes = llm_summary.get("security_notes", [])

        if security_level in ("critical", "high") and security_notes:
            sections.append("## Security Notes")
            sections.append("")
            for note in security_notes:
                sections.append(f"- {note}")
            sections.append("")
        elif security_level in ("critical", "high"):
            sections.append("## Security Notes")
            sections.append("")
            sections.append(f"- This pack has **{security_level}** security level")
            sections.append("- Review changes carefully before merging")
            sections.append("")

        # Related packs (dependencies)
        dependencies = pack_data.get("dependencies", [])
        if dependencies:
            sections.append("## Related Packs")
            sections.append("")
            for dep in dependencies:
                sections.append(f"- `{dep}`")
            sections.append("")

        return "\n".join(sections)

    def generate_entities_content(self, pack_data: Dict[str, Any]) -> str:
        """Generate ENTITIES.md content with entity reference."""
        sections = []

        pack_name = pack_data.get("display_name", pack_data.get("name", "Unnamed Pack"))
        sections.append(f"# {pack_name} - Entity Reference")
        sections.append("")

        entities = pack_data.get("entities", [])

        if not entities:
            sections.append("No entities found in this pack.")
            return "\n".join(sections)

        # Group entities by type
        functions = [e for e in entities if e.get("type") == "function"]
        classes = [e for e in entities if e.get("type") == "class"]
        others = [e for e in entities if e.get("type") not in ("function", "class")]

        if classes:
            sections.append("## Classes")
            sections.append("")
            for cls in classes:
                name = cls.get("name", "Unknown")
                docstring = cls.get("docstring", "")
                file_path = cls.get("file_path", "")

                sections.append(f"### `{name}`")
                sections.append("")
                if file_path:
                    sections.append(f"**File:** `{file_path}`")
                    sections.append("")
                if docstring:
                    sections.append(docstring.strip())
                    sections.append("")

        if functions:
            sections.append("## Functions")
            sections.append("")
            sections.append("| Function | File | Description |")
            sections.append("|----------|------|-------------|")

            for func in functions:
                name = func.get("name", "Unknown")
                file_path = func.get("file_path", "")
                docstring = func.get("docstring", "")

                # Truncate docstring for table
                desc = docstring.split("\n")[0] if docstring else "-"
                if len(desc) > 60:
                    desc = desc[:57] + "..."

                sections.append(f"| `{name}` | `{file_path}` | {desc} |")

            sections.append("")

        if others:
            sections.append("## Other Entities")
            sections.append("")
            for entity in others:
                name = entity.get("name", "Unknown")
                entity_type = entity.get("type", "unknown")
                sections.append(f"- `{name}` ({entity_type})")
            sections.append("")

        return "\n".join(sections)

    def generate_architecture_content(self, pack_data: Dict[str, Any]) -> str:
        """Generate ARCHITECTURE.md content with detailed architecture info."""
        sections = []

        pack_name = pack_data.get("display_name", pack_data.get("name", "Unnamed Pack"))
        sections.append(f"# {pack_name} - Architecture")
        sections.append("")

        llm_summary = pack_data.get("llm_summary", {})

        # Architecture overview
        architecture = llm_summary.get("architecture", "")
        if architecture:
            sections.append("## Overview")
            sections.append("")
            sections.append(architecture)
            sections.append("")

        # File structure
        files = pack_data.get("files", [])
        if files:
            sections.append("## File Structure")
            sections.append("")
            sections.append("```")
            for f in sorted(files):
                sections.append(f)
            sections.append("```")
            sections.append("")

        # Dependencies graph
        dependencies = pack_data.get("dependencies", [])
        if dependencies:
            sections.append("## Dependencies")
            sections.append("")
            sections.append("This pack depends on:")
            sections.append("")
            for dep in dependencies:
                sections.append(f"- `{dep}`")
            sections.append("")

        # Key components with details
        key_components = llm_summary.get("key_components", [])
        if key_components:
            sections.append("## Component Details")
            sections.append("")

            for comp in key_components:
                if isinstance(comp, dict):
                    name = comp.get("name", "Unknown")
                    role = comp.get("role", comp.get("description", ""))
                    sections.append(f"### {name}")
                    sections.append("")
                    if role:
                        sections.append(role)
                        sections.append("")

        # Security considerations
        security_level = pack_data.get("security_level", "normal")
        security_notes = llm_summary.get("security_notes", [])

        sections.append("## Security Considerations")
        sections.append("")
        sections.append(f"**Security Level:** {security_level}")
        sections.append("")

        if security_notes:
            for note in security_notes:
                sections.append(f"- {note}")
            sections.append("")

        return "\n".join(sections)

    def generate_reference_files(self, pack_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate optional reference files (ENTITIES.md, ARCHITECTURE.md)."""
        return {
            "ENTITIES.md": self.generate_entities_content(pack_data),
            "ARCHITECTURE.md": self.generate_architecture_content(pack_data),
        }

    def generate(
        self,
        pack_data: Dict[str, Any],
        project_root: Path,
    ) -> GeneratedSkill:
        """
        Generate SKILL.md and optional reference files for a pack.

        Args:
            pack_data: The pack data dictionary (from pack build)
            project_root: Root directory of the project

        Returns:
            GeneratedSkill with paths and content
        """
        skill_name = self.generate_skill_name(pack_data.get("name", "unnamed"))
        output_dir = self.config.get_output_dir(project_root) / skill_name

        skill_content = self.generate_skill_content(pack_data)

        reference_files = {}
        if self.config.include_reference:
            reference_files = self.generate_reference_files(pack_data)

        return GeneratedSkill(
            skill_name=skill_name,
            skill_path=output_dir / "SKILL.md",
            skill_content=skill_content,
            reference_files=reference_files,
        )

    def write_skill(
        self,
        skill: GeneratedSkill,
    ) -> List[Path]:
        """
        Write generated skill files to disk.

        Returns list of created file paths.
        """
        created_files = []

        # Ensure directory exists
        skill.skill_path.parent.mkdir(parents=True, exist_ok=True)

        # Write main SKILL.md
        skill.skill_path.write_text(skill.skill_content)
        created_files.append(skill.skill_path)

        # Write reference files
        for filename, content in skill.reference_files.items():
            file_path = skill.skill_path.parent / filename
            file_path.write_text(content)
            created_files.append(file_path)

        return created_files
