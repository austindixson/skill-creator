#!/usr/bin/env python3
"""
Quick validation script for skills - supports both Claude Code and OpenClaw formats.
"""

import json
import sys
import os
import re
import yaml
from pathlib import Path

from scripts.utils import detect_skill_type, SKILL_TYPE_OPENCLAW, SKILL_TYPE_CLAUDE_CODE


def validate_openclaw_skill(skill_path):
    """Validate an OpenClaw skill (_meta.json-based)."""
    skill_path = Path(skill_path)
    issues = []
    warnings = []

    # --- Required: _meta.json ---
    meta_file = skill_path / '_meta.json'
    if not meta_file.exists():
        return False, "_meta.json not found"

    try:
        meta = json.loads(meta_file.read_text())
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in _meta.json: {e}"

    if not isinstance(meta, dict):
        return False, "_meta.json must be a JSON object"

    # Required fields
    REQUIRED_FIELDS = ['name', 'version', 'description']
    for field in REQUIRED_FIELDS:
        if field not in meta:
            issues.append(f"Missing required field '{field}' in _meta.json")

    # Validate name
    name = meta.get('name', '')
    if name:
        if not isinstance(name, str):
            issues.append(f"name must be a string, got {type(name).__name__}")
        elif not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
            warnings.append(f"name '{name}' should be kebab-case (lowercase, hyphens)")

    # Validate version (semver)
    version = meta.get('version', '')
    if version and not re.match(r'^\d+\.\d+\.\d+', str(version)):
        warnings.append(f"version '{version}' doesn't follow semver (e.g., 1.0.0)")

    # Validate description
    description = meta.get('description', '')
    if description and not isinstance(description, str):
        issues.append(f"description must be a string, got {type(description).__name__}")

    # Validate schema field
    schema = meta.get('schema', '')
    if schema and not schema.startswith('openclaw.'):
        warnings.append(f"schema '{schema}' doesn't start with 'openclaw.'")

    # Validate platform field
    platform = meta.get('platform', '')
    if platform and platform != 'openclaw':
        warnings.append(f"platform is '{platform}', expected 'openclaw'")

    # Validate tags
    tags = meta.get('tags', [])
    if tags and not isinstance(tags, list):
        issues.append("tags must be an array")

    # --- Optional: SKILL.md ---
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        warnings.append("No SKILL.md found (recommended for documentation)")

    # --- Optional: scripts/ ---
    scripts_dir = skill_path / 'scripts'
    if not scripts_dir.exists() or not scripts_dir.is_dir():
        warnings.append("No scripts/ directory found")
    else:
        py_files = list(scripts_dir.glob('*.py'))
        if not py_files:
            warnings.append("scripts/ directory exists but has no .py files")

    # --- Optional: requirements.txt ---
    deps = meta.get('dependencies', [])
    if 'python' in deps or (scripts_dir.exists() and list(scripts_dir.glob('*.py'))):
        req_file = skill_path / 'requirements.txt'
        if not req_file.exists():
            warnings.append("Python skill without requirements.txt")

    # --- Optional: config.json consistency ---
    config_file = skill_path / 'config.json'
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            if isinstance(config, dict):
                config_version = config.get('version', '')
                if config_version and version and config_version != version:
                    warnings.append(f"Version mismatch: _meta.json={version}, config.json={config_version}")
        except json.JSONDecodeError:
            issues.append("Invalid JSON in config.json")

    # --- Build result ---
    if issues:
        return False, "ERRORS:\n" + "\n".join(f"  - {i}" for i in issues) + (
            "\nWARNINGS:\n" + "\n".join(f"  - {w}" for w in warnings) if warnings else ""
        )

    if warnings:
        return True, "Valid (with warnings):\n" + "\n".join(f"  - {w}" for w in warnings)

    return True, "OpenClaw skill is valid!"


def validate_skill(skill_path):
    """Validate a skill (auto-detects Claude Code vs OpenClaw format)."""
    skill_path = Path(skill_path)

    skill_type = detect_skill_type(skill_path)
    if skill_type == SKILL_TYPE_OPENCLAW:
        return validate_openclaw_skill(skill_path)

    return validate_claude_code_skill(skill_path)


def validate_claude_code_skill(skill_path):
    """Validate a Claude Code skill (SKILL.md frontmatter-based)."""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Define allowed properties
    ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (kebab-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate compatibility field if present (optional)
    compatibility = frontmatter.get('compatibility', '')
    if compatibility:
        if not isinstance(compatibility, str):
            return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
        if len(compatibility) > 500:
            return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."

    return True, "Skill is valid!"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)