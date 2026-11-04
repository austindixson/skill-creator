# Skill Creator

A Claude Code skill for creating, evaluating, improving, and benchmarking AI skills — with full support for both **Claude Code** and **OpenClaw** skill formats.

Built by [austindixson](https://github.com/austindixson). Powered by Claude.

---

## What It Does

Skill Creator is a meta-skill: it helps you build better skills. It handles the entire lifecycle:

1. **Create** — Interview-driven skill authoring with best practices baked in
2. **Eval** — Parallel test execution with quantitative grading and interactive review
3. **Improve** — Feedback-driven iteration loop with before/after comparison
4. **Benchmark** — Statistical analysis with mean/stddev/delta across configurations
5. **Optimize** — Description triggering optimization with train/test split

It works in Claude Code, Claude.ai, and Cowork environments.

## Quick Start

### Install

```bash
# Clone into your Claude Code skills directory
git clone https://github.com/austindixson/skill-creator.git ~/.claude/skills/skill-creator
```

### Use

In Claude Code, just describe what you want:

```
# Create a new skill
"Create a skill that reviews PRs for security issues"

# Evaluate an existing skill
"Run evals on my pdf skill"

# Improve based on test results
"Improve my deploy skill based on these test cases"

# Benchmark with variance analysis
"Benchmark my skill across 10 runs and show variance"

# Evaluate OpenClaw skills from GitHub
"Eval all my OpenClaw skills on GitHub"
```

Or invoke directly with `/skill-creator`.

---

## Architecture

```
skill-creator/
├── SKILL.md                    # Core instructions (loaded when skill triggers)
├── agents/                     # Specialized subagent prompts
│   ├── grader.md               # Evaluates assertions against outputs
│   ├── comparator.md           # Blind A/B comparison (no bias)
│   └── analyzer.md             # Post-hoc analysis of why winner won
├── scripts/                    # Python automation
│   ├── utils.py                # Shared utilities (parse both formats)
│   ├── quick_validate.py       # Validates skill structure
│   ├── run_eval.py             # Tests description triggering
│   ├── run_loop.py             # Optimization loop (eval → improve → repeat)
│   ├── improve_description.py  # Claude-powered description improvement
│   ├── aggregate_benchmark.py  # Generates benchmark.json with statistics
│   ├── generate_report.py      # HTML report from optimization loop
│   └── package_skill.py        # Creates distributable .skill files
├── eval-viewer/                # Interactive results viewer
│   ├── generate_review.py      # Generates HTML review UI
│   └── viewer.html             # The viewer template
├── references/
│   └── schemas.md              # JSON schemas for all data structures
├── assets/
│   └── eval_review.html        # Template for trigger eval review
└── LICENSE.txt                 # Apache 2.0
```

---

## How It Works

### The Core Loop

```
Draft Skill → Write Test Cases → Spawn Parallel Runs → Grade → Review → Improve → Repeat
                                    ↑                                        |
                                    └────────────────────────────────────────┘
```

1. **Capture intent** — Understands what the skill should do through conversation
2. **Write the skill** — Generates SKILL.md (Claude Code) or `_meta.json` + scripts (OpenClaw)
3. **Create test cases** — 2-3 realistic prompts saved to `evals/evals.json`
4. **Spawn parallel runs** — For each test case, launches TWO subagents simultaneously:
   - **With-skill run** — executes the task with the skill loaded
   - **Baseline run** — same task, no skill (or old version)
5. **Grade results** — Grader agent evaluates each assertion with evidence
6. **Interactive review** — HTML viewer with outputs, benchmarks, and feedback forms
7. **Improve** — Rewrites skill based on user feedback + quantitative data
8. **Repeat** — Until pass rates are satisfactory

### Grading System

Assertions are binary pass/fail with evidence required:

```json
{
  "expectations": [
    {
      "text": "Output includes a summary section",
      "passed": true,
      "evidence": "Found '## Summary' header at line 3 with 4 bullet points"
    }
  ],
  "summary": { "passed": 5, "failed": 1, "total": 6, "pass_rate": 0.83 }
}
```

The grader also critiques the evals themselves — flagging weak assertions and suggesting missing test coverage.

### Benchmarking

Aggregates results across multiple runs with statistical rigor:

```
┌─────────────────┬──────────────────────┬──────────────────────┬─────────┐
│                 │ With Skill           │ Without Skill        │ Delta   │
├─────────────────┼──────────────────────┼──────────────────────┼─────────┤
│ Pass Rate       │ 0.85 ± 0.05         │ 0.35 ± 0.08         │ +0.50   │
│ Time (seconds)  │ 45.0 ± 12.0         │ 32.0 ± 8.0          │ +13.0   │
│ Tokens          │ 3800 ± 400          │ 2100 ± 300          │ +1700   │
└─────────────────┴──────────────────────┴──────────────────────┴─────────┘
```

### Description Optimization

Automatic optimization of skill triggering:

1. Generates 20 eval queries (10 should-trigger, 10 should-not)
2. Splits 60/40 train/test to prevent overfitting
3. Tests each query 3x for reliable trigger rates
4. Calls Claude to improve description based on failures
5. Iterates up to 5 times, selects best by test score

---

## Dual Format Support

### Claude Code Skills

Standard format with YAML frontmatter:

```yaml
---
name: my-skill
description: What it does and when to trigger
---

# My Skill

Instructions here...
```

### OpenClaw Skills

`_meta.json`-based format with auto-detection:

```json
{
  "schema": "openclaw.skill.v1",
  "name": "my-skill",
  "version": "1.0.0",
  "displayName": "My Skill",
  "description": "What it does",
  "author": "YourName",
  "tags": ["utility", "openclaw"],
  "platform": "openclaw"
}
```

**Auto-detection** identifies the format by checking for `_meta.json` with OpenClaw markers or heuristic field patterns. All scripts (`run_eval.py`, `run_loop.py`, `improve_description.py`, `quick_validate.py`) work with both formats transparently.

### Batch GitHub Evaluation

Evaluate entire portfolios of OpenClaw skills:

```
"Eval all my OpenClaw skills on GitHub"
```

This clones all repos, runs validation, generates health scores, produces an interactive HTML report with:
- Per-skill health scores (0-100%)
- Tier rankings (S/A/B/C/D)
- Missing file detection
- Version sync checks
- Security issue scanning
- Auto-fix recommendations

### Format Conversion

Convert between formats in either direction:
- **Claude Code → OpenClaw**: Extracts frontmatter into `_meta.json`, adds schema/platform/version
- **OpenClaw → Claude Code**: Merges `_meta.json` fields into SKILL.md YAML frontmatter

---

## Validation

```bash
# Validate any skill (auto-detects format)
cd ~/.claude/skills/skill-creator
python3 -m scripts.quick_validate /path/to/skill

# Claude Code validation checks:
#   - SKILL.md exists with valid YAML frontmatter
#   - Required fields: name, description
#   - Name is kebab-case, under 64 chars
#   - Description under 1024 chars, no angle brackets
#   - No unexpected frontmatter keys

# OpenClaw validation checks:
#   - _meta.json exists with valid JSON
#   - Required fields: name, version, description
#   - Schema starts with "openclaw."
#   - Platform is "openclaw"
#   - Name is kebab-case
#   - Version follows semver
#   - scripts/ directory with .py files
#   - requirements.txt for Python skills
#   - config.json version synced with _meta.json
```

---

## Eval Viewer

The interactive HTML viewer provides:

- **Outputs tab** — Click through test cases, view rendered outputs, leave feedback
- **Benchmark tab** — Statistical comparison with per-eval breakdowns
- **Navigation** — Arrow keys or prev/next buttons
- **Auto-save** — Feedback saves as you type
- **Export** — "Submit All Reviews" saves `feedback.json`

Works in browser (server mode) or as standalone HTML (headless/Cowork mode via `--static`).

---

## Specialized Agents

### Grader (`agents/grader.md`)
Evaluates assertions against execution transcripts and output files. Provides evidence-based pass/fail judgments and critiques the eval quality itself.

### Blind Comparator (`agents/comparator.md`)
Receives two outputs labeled A and B without knowing which skill produced them. Scores on a rubric (correctness, completeness, accuracy, organization, formatting, usability) and declares a winner. Eliminates bias.

### Post-hoc Analyzer (`agents/analyzer.md`)
After blind comparison, "unblinds" results and analyzes WHY the winner won. Extracts actionable improvement suggestions by examining skill instructions, execution patterns, and output quality.

---

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `utils.py` | Parse both skill formats, auto-detect type | `from scripts.utils import parse_skill_auto` |
| `quick_validate.py` | Validate skill structure | `python3 -m scripts.quick_validate <skill-dir>` |
| `run_eval.py` | Test description triggering | `python3 -m scripts.run_eval --eval-set <json> --skill-path <dir>` |
| `run_loop.py` | Full optimization loop | `python3 -m scripts.run_loop --eval-set <json> --skill-path <dir>` |
| `improve_description.py` | Improve description via Claude | `python3 -m scripts.improve_description --eval-results <json> --skill-path <dir>` |
| `aggregate_benchmark.py` | Generate benchmark statistics | `python3 -m scripts.aggregate_benchmark <workspace> --skill-name <name>` |
| `generate_report.py` | HTML report from loop results | `python3 -m scripts.generate_report <results-dir>` |
| `package_skill.py` | Create distributable .skill file | `python3 -m scripts.package_skill <skill-dir>` |

---

## JSON Schemas

All data structures are documented in `references/schemas.md`:

- `evals.json` — Test case definitions
- `grading.json` — Grader output with evidence
- `benchmark.json` — Aggregated statistics
- `comparison.json` — Blind comparator results
- `analysis.json` — Post-hoc analyzer output
- `timing.json` — Execution timing data
- `metrics.json` — Tool usage metrics
- `_meta.json` — OpenClaw skill metadata

---

## Environment Support

| Environment | Subagents | Browser | Benchmarks | Description Opt |
|-------------|-----------|---------|------------|-----------------|
| Claude Code | Yes | Yes | Yes | Yes |
| Cowork | Yes | Static HTML | Yes | Yes |
| Claude.ai | No | No | Qualitative only | No |

---

## Requirements

- **Claude Code** or **Claude.ai** (for skill execution)
- **Python 3.8+** (for scripts)
- **PyYAML** (for frontmatter parsing)

No API keys needed — scripts use `claude -p` which inherits the session's auth.

---

## License

Apache 2.0 — see [LICENSE.txt](LICENSE.txt).

---

## Credits

Built with Claude by [austindixson](https://github.com/austindixson).

Skill Creator was used to evaluate, auto-fix, and benchmark [37 OpenClaw skills](https://github.com/austindixson) in a single session — applying 132 automated fixes and producing a full portfolio health report with deep functional analysis across every skill.
