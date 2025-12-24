"""Tests for the skill generator module."""

from pathlib import Path
from unittest.mock import patch

from autodoc.skill_generator import (
    GeneratedSkill,
    SkillConfig,
    SkillFormat,
    SkillGenerator,
)


class TestSkillGenerator:
    """Tests for SkillGenerator class."""

    def test_generate_skill_name_lowercase(self):
        """Test that skill names are converted to lowercase."""
        generator = SkillGenerator()
        assert generator.generate_skill_name("Authentication") == "authentication"
        assert generator.generate_skill_name("API_Layer") == "api-layer"

    def test_generate_skill_name_underscores_to_hyphens(self):
        """Test that underscores are converted to hyphens."""
        generator = SkillGenerator()
        assert generator.generate_skill_name("my_cool_pack") == "my-cool-pack"
        assert generator.generate_skill_name("auth_service") == "auth-service"

    def test_generate_skill_name_camelcase(self):
        """Test that camelCase is converted to hyphenated."""
        generator = SkillGenerator()
        assert generator.generate_skill_name("AuthenticationSystem") == "authentication-system"
        assert generator.generate_skill_name("myAwesomePack") == "my-awesome-pack"

    def test_generate_skill_name_special_chars(self):
        """Test that special characters are removed."""
        generator = SkillGenerator()
        assert generator.generate_skill_name("auth@2.0") == "auth20"
        assert generator.generate_skill_name("pack!@#$%") == "pack"

    def test_generate_skill_name_consecutive_hyphens(self):
        """Test that consecutive hyphens are collapsed."""
        generator = SkillGenerator()
        assert generator.generate_skill_name("auth--service") == "auth-service"
        assert generator.generate_skill_name("a__b__c") == "a-b-c"

    def test_generate_description_basic(self):
        """Test basic description generation."""
        generator = SkillGenerator()
        pack_data = {"description": "Handles user authentication."}
        assert generator.generate_description(pack_data) == "Handles user authentication."

    def test_generate_description_with_llm_summary(self):
        """Test description generation with LLM summary data."""
        generator = SkillGenerator()
        pack_data = {
            "description": "Auth module.",
            "llm_summary": {
                "usage_patterns": ["implementing login flows"],
                "key_components": [
                    {"name": "login"},
                    {"name": "verify_token"},
                ],
            },
        }
        desc = generator.generate_description(pack_data)
        assert "Auth module." in desc
        assert "implementing login flows" in desc.lower()
        assert "login" in desc

    def test_generate_description_truncation(self):
        """Test that long descriptions are truncated."""
        config = SkillConfig(max_description_length=50)
        generator = SkillGenerator(config)
        pack_data = {"description": "A" * 100}
        desc = generator.generate_description(pack_data)
        assert len(desc) <= 50
        assert desc.endswith("...")

    def test_generate_skill_content_frontmatter(self):
        """Test that skill content has proper YAML frontmatter."""
        generator = SkillGenerator()
        pack_data = {
            "name": "authentication",
            "display_name": "Authentication System",
            "description": "Handles user auth.",
        }
        content = generator.generate_skill_content(pack_data)

        assert content.startswith("---\n")
        assert "name: authentication" in content
        assert "description: Handles user auth." in content
        # Check for proper frontmatter structure: ---\n...content...\n---\n
        lines = content.split("\n")
        assert lines[0] == "---"
        # Find closing --- (should be after the opening ---)
        closing_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line == "---":
                closing_idx = i
                break
        assert closing_idx is not None, "Missing closing frontmatter delimiter"
        assert closing_idx > 1, "Frontmatter should have content"

    def test_generate_skill_content_title(self):
        """Test that skill content has proper title."""
        generator = SkillGenerator()
        pack_data = {
            "name": "auth",
            "display_name": "Authentication System",
            "description": "Auth module.",
        }
        content = generator.generate_skill_content(pack_data)
        assert "# Authentication System" in content

    def test_generate_skill_content_file_locations(self):
        """Test that file locations are included."""
        generator = SkillGenerator()
        pack_data = {
            "name": "auth",
            "description": "Auth.",
            "files": ["src/auth/**/*.py", "src/middleware/auth.py"],
        }
        content = generator.generate_skill_content(pack_data)
        assert "## File Locations" in content
        assert "`src/auth/**/*.py`" in content
        assert "`src/middleware/auth.py`" in content

    def test_generate_skill_content_security_notes_critical(self):
        """Test that security notes are included for critical packs."""
        generator = SkillGenerator()
        pack_data = {
            "name": "secrets",
            "description": "Secrets management.",
            "security_level": "critical",
            "llm_summary": {"security_notes": ["Never log secrets", "Use encryption"]},
        }
        content = generator.generate_skill_content(pack_data)
        assert "## Security Notes" in content
        assert "Never log secrets" in content
        assert "Use encryption" in content

    def test_generate_skill_content_related_packs(self):
        """Test that dependencies are included as related packs."""
        generator = SkillGenerator()
        pack_data = {
            "name": "api",
            "description": "API layer.",
            "dependencies": ["database", "auth"],
        }
        content = generator.generate_skill_content(pack_data)
        assert "## Related Packs" in content
        assert "`database`" in content
        assert "`auth`" in content

    def test_generate_entities_content(self):
        """Test entities reference generation."""
        generator = SkillGenerator()
        pack_data = {
            "name": "auth",
            "display_name": "Auth",
            "entities": [
                {"type": "function", "name": "login", "docstring": "Login user", "file_path": "auth.py"},
                {"type": "class", "name": "User", "docstring": "User model", "file_path": "models.py"},
            ],
        }
        content = generator.generate_entities_content(pack_data)
        assert "# Auth - Entity Reference" in content
        assert "## Classes" in content
        assert "### `User`" in content
        assert "## Functions" in content
        assert "`login`" in content

    def test_generate_architecture_content(self):
        """Test architecture reference generation."""
        generator = SkillGenerator()
        pack_data = {
            "name": "api",
            "display_name": "API Layer",
            "files": ["src/api/routes.py", "src/api/handlers.py"],
            "security_level": "high",
            "llm_summary": {
                "architecture": "RESTful API with JWT auth.",
                "key_components": [{"name": "router", "role": "Request routing"}],
            },
        }
        content = generator.generate_architecture_content(pack_data)
        assert "# API Layer - Architecture" in content
        assert "## Overview" in content
        assert "RESTful API with JWT auth." in content
        assert "## File Structure" in content
        assert "src/api/routes.py" in content
        assert "**Security Level:** high" in content


class TestSkillConfig:
    """Tests for SkillConfig class."""

    def test_default_format(self):
        """Test default format is Claude."""
        config = SkillConfig()
        assert config.format == SkillFormat.CLAUDE

    def test_get_output_dir_claude(self, tmp_path):
        """Test output dir for Claude format."""
        config = SkillConfig(format=SkillFormat.CLAUDE)
        output_dir = config.get_output_dir(tmp_path)
        assert output_dir == tmp_path / ".claude" / "skills"

    def test_get_output_dir_codex(self, tmp_path):
        """Test output dir for Codex format."""
        config = SkillConfig(format=SkillFormat.CODEX)
        with patch.object(Path, "home", return_value=tmp_path):
            output_dir = config.get_output_dir(tmp_path)
            assert output_dir == tmp_path / ".codex" / "skills"

    def test_get_output_dir_custom(self, tmp_path):
        """Test custom output dir."""
        custom_dir = tmp_path / "custom" / "skills"
        config = SkillConfig(output_dir=custom_dir)
        output_dir = config.get_output_dir(tmp_path)
        assert output_dir == custom_dir


class TestGeneratedSkill:
    """Tests for GeneratedSkill dataclass."""

    def test_generated_skill_creation(self, tmp_path):
        """Test GeneratedSkill creation."""
        skill = GeneratedSkill(
            skill_name="auth",
            skill_path=tmp_path / "SKILL.md",
            skill_content="---\nname: auth\n---\n# Auth",
            reference_files={"ENTITIES.md": "# Entities"},
        )
        assert skill.skill_name == "auth"
        assert skill.skill_path == tmp_path / "SKILL.md"
        assert "# Auth" in skill.skill_content
        assert "ENTITIES.md" in skill.reference_files


class TestSkillGeneratorIntegration:
    """Integration tests for the full skill generation workflow."""

    def test_generate_and_write_skill(self, tmp_path):
        """Test full workflow: generate and write skill files."""
        config = SkillConfig(
            format=SkillFormat.CLAUDE,
            include_reference=True,
            output_dir=tmp_path / "skills",
        )
        generator = SkillGenerator(config)

        pack_data = {
            "name": "authentication",
            "display_name": "Authentication System",
            "description": "Handles user authentication and session management.",
            "files": ["src/auth/**/*.py"],
            "dependencies": ["database"],
            "security_level": "high",
            "llm_summary": {
                "architecture": "OAuth2 with JWT tokens.",
                "key_components": [{"name": "login", "role": "Entry point"}],
                "usage_patterns": ["Call login() to authenticate"],
                "security_notes": ["Tokens expire after 1 hour"],
            },
            "entities": [
                {"type": "function", "name": "login", "docstring": "Login user", "file_path": "auth.py"},
            ],
        }

        skill = generator.generate(pack_data, tmp_path)
        created_files = generator.write_skill(skill)

        # Check files were created
        assert len(created_files) == 3  # SKILL.md, ENTITIES.md, ARCHITECTURE.md

        # Check SKILL.md
        skill_path = tmp_path / "skills" / "authentication" / "SKILL.md"
        assert skill_path.exists()
        skill_content = skill_path.read_text()
        assert "name: authentication" in skill_content
        assert "# Authentication System" in skill_content
        assert "OAuth2 with JWT tokens." in skill_content

        # Check reference files
        entities_path = tmp_path / "skills" / "authentication" / "ENTITIES.md"
        assert entities_path.exists()
        assert "login" in entities_path.read_text()

        arch_path = tmp_path / "skills" / "authentication" / "ARCHITECTURE.md"
        assert arch_path.exists()
        assert "high" in arch_path.read_text()

    def test_generate_minimal_skill(self, tmp_path):
        """Test skill generation with minimal pack data."""
        config = SkillConfig(output_dir=tmp_path / "skills")
        generator = SkillGenerator(config)

        pack_data = {
            "name": "utils",
            "description": "Utility functions.",
        }

        skill = generator.generate(pack_data, tmp_path)
        created_files = generator.write_skill(skill)

        assert len(created_files) == 1  # Only SKILL.md
        skill_path = tmp_path / "skills" / "utils" / "SKILL.md"
        assert skill_path.exists()
        assert "name: utils" in skill_path.read_text()
