"""Shared utilities for skill-creator scripts."""

import json
from pathlib import Path


SKILL_TYPE_CLAUDE_CODE = "claude-code"
SKILL_TYPE_OPENCLAW = "openclaw"


def detect_skill_type(skill_path: Path) -> str:
    """Detect whether a skill is Claude Code or OpenClaw format.

    Detection priority:
    1. Explicit OpenClaw markers in _meta.json (schema/platform)
    2. _meta.json with OpenClaw-style fields (tags, version, slug/tools/author)
    3. SKILL.md frontmatter with OpenClaw fields (displayName, version)
    4. Default: Claude Code
    """
    meta_file = skill_path / "_meta.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            # Explicit OpenClaw markers
            if (
                meta.get("schema", "").startswith("openclaw.")
                or meta.get("platform") == "openclaw"
            ):
                return SKILL_TYPE_OPENCLAW
            # Heuristic: _meta.json with common OpenClaw fields
            openclaw_indicators = sum([
                isinstance(meta.get("tags"), list),
                isinstance(meta.get("version"), str),
                "slug" in meta,
                isinstance(meta.get("tools"), list),
                "author" in meta,
                "displayName" in meta,
                "dependencies" in meta,
            ])
            # If _meta.json has 2+ OpenClaw-style fields, it's OpenClaw
            if openclaw_indicators >= 2:
                return SKILL_TYPE_OPENCLAW
        except (json.JSONDecodeError, OSError):
            pass

    # Check if SKILL.md frontmatter has OpenClaw-specific fields
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        try:
            content = skill_md.read_text()
            if content.startswith("---"):
                # Look for OpenClaw frontmatter fields
                end = content.find("---", 3)
                if end > 0:
                    frontmatter = content[3:end]
                    has_display_name = "displayName:" in frontmatter
                    has_version = "version:" in frontmatter
                    has_homepage = "homepage:" in frontmatter
                    if has_display_name or (has_version and has_homepage):
                        return SKILL_TYPE_OPENCLAW
        except OSError:
            pass

    return SKILL_TYPE_CLAUDE_CODE


def parse_openclaw_meta(skill_path: Path) -> tuple[str, str, str]:
    """Parse an OpenClaw skill, returning (name, description, full_content).

    Reads from _meta.json if available, falls back to SKILL.md frontmatter.
    full_content is the SKILL.md body if it exists, otherwise the JSON content.
    """
    meta_file = skill_path / "_meta.json"
    skill_md = skill_path / "SKILL.md"

    name = ""
    description = ""

    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            name = meta.get("name", "")
            description = meta.get("description", "")
        except (json.JSONDecodeError, OSError):
            pass

    # If no _meta.json or missing fields, try SKILL.md frontmatter
    if (not name or not description) and skill_md.exists():
        try:
            import yaml
            content = skill_md.read_text()
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    fm = yaml.safe_load(content[3:end])
                    if isinstance(fm, dict):
                        name = name or fm.get("name", "")
                        description = description or fm.get("description", "")
        except Exception:
            pass

    if skill_md.exists():
        full_content = skill_md.read_text()
    elif meta_file.exists():
        full_content = meta_file.read_text()
    else:
        full_content = ""

    return name, description, full_content


def parse_skill_auto(skill_path: Path) -> tuple[str, str, str, str]:
    """Auto-detect skill type and parse accordingly.

    Returns (name, description, full_content, skill_type).
    """
    skill_type = detect_skill_type(skill_path)
    if skill_type == SKILL_TYPE_OPENCLAW:
        name, description, content = parse_openclaw_meta(skill_path)
    else:
        name, description, content = parse_skill_md(skill_path)
    return name, description, content, skill_type


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    content = (skill_path / "SKILL.md").read_text()
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:"):].strip()
            # Handle YAML multiline indicators (>, |, >-, |-)
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (frontmatter_lines[i].startswith("  ") or frontmatter_lines[i].startswith("\t")):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation_lines)
                continue
            else:
                description = value.strip('"').strip("'")
        i += 1

    return name, description, content
