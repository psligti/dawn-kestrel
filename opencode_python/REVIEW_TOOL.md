# OpenCode Review Agent CLI

Install and run the multi-agent PR review tool as a standalone `uv tool`.

## Installation

Install the tool globally using uv:

```bash
uv tool install opencode-python
```

This will install two commands:
- `opencode-review` - Run multi-agent PR review
- `opencode-review-generate-docs` - Generate documentation for review agents

## Usage

### Running PR Review

```bash
# Review current branch against main (default) - runs all agents
opencode-review

# Run only a specific agent (e.g., security, architecture, linting)
opencode-review --agent security

# Review against a specific base branch
opencode-review --base-ref develop

# Review from base to specific commit
opencode-review --base-ref main --head-ref abc123

# Include optional review agents (diff_scoper, requirements, performance, dependencies, changelog)
opencode-review --include-optional

# Output in JSON format
opencode-review --output json

# Output in Markdown format
opencode-review --output markdown

# Enable verbose logging to see detailed debugging info
opencode-review -v

# Custom timeout (seconds)
opencode-review --timeout 600

# Review a different repository
opencode-review --repo-root /path/to/repo
```

**Available agents:**
- `security` - Security vulnerabilities
- `architecture` - Architectural decisions
- `linting` - Code quality and style
- `documentation` - Documentation coverage
- `telemetry` - Metrics and telemetry
- `unit_tests` - Test coverage
- `diff_scoper` - Diff scoping (optional)
- `requirements` - Requirements review (optional)
- `performance` - Performance analysis (optional)
- `dependencies` - Dependency licensing (optional)
- `changelog` - Release changelog validation (optional)


### Output Formats

**Terminal (default)**
```
[cyan]Starting PR review...[/cyan]
[dim]Repo: /path/to/repo[/dim]
[dim]Refs: main -> HEAD[/dim]
...
[green]Review complete[/green]
[dim]Total findings: 5[/dim]
[dim]Decision: needs_changes[/dim]
```

**JSON**
```json
{
  "merge_decision": {
    "decision": "needs_changes",
    "must_fix": [...],
    "should_fix": [...]
  },
  "findings": [...],
  "tool_plan": {...}
}
```

**Markdown**
```markdown
# PR Review Results

**Decision:** needs_changes
**Total Findings:** 5

## ⚠️ Required Changes
...
```

### Generating Documentation

Generate documentation for review agents:

```bash
# Generate docs for a specific agent
opencode-review-generate-docs --agent security

# Generate docs for all agents
opencode-review-generate-docs --all

# Force regeneration even if hash matches
opencode-review-generate-docs --all --force

# Custom output directory
opencode-review-generate-docs --all --output ./docs

# Verbose mode
opencode-review-generate-docs --all -v
```

## Review Agents

### Core Agents (run by default)
- **Architecture** - Analyzes architectural patterns and design decisions
- **Security** - Checks for security vulnerabilities and issues
- **Documentation** - Ensures proper documentation standards
- **Telemetry** - Reviews telemetry and metrics implementation
- **Linting** - Checks code style and formatting
- **Unit Tests** - Validates test coverage and quality

### Optional Agents (use `--include-optional`)
- **Diff Scoper** - Intelligent context scoping for changes
- **Requirements** - Validates requirement coverage
- **Performance** - Analyzes performance and reliability
- **Dependencies** - Reviews dependency and license compliance
- **Changelog** - Ensures proper changelog entries

## Options

### `opencode-review`
| Option | Description | Default |
|--------|-------------|---------|
| `--repo-root PATH` | Repository root directory | Current directory |
| `--base-ref TEXT` | Base git reference | `main` |
| `--head-ref TEXT` | Head git reference | `HEAD` |
| `--output FORMAT` | Output: json, markdown, terminal | `terminal` |
| `--include-optional` | Include optional review agents | `false` |
| `--timeout SECONDS` | Agent timeout in seconds | `300` |
| `-v, --verbose` | Enable verbose logging | `false` |
| `--help` | Show help message | - |

### `opencode-review-generate-docs`
| Option | Description |
|--------|-------------|
| `--agent TEXT` | Specific agent name (e.g., security, architecture) |
| `--all` | Generate documentation for all reviewers |
| `--force` | Overwrite existing documentation |
| `--output PATH` | Custom output directory |
| `-v, --verbose` | Enable verbose logging |
| `--help` | Show help message |

## Examples

### Review a pull request
```bash
cd /path/to/repo
git checkout feature-branch
opencode-review --base-ref main
```

### Quick check for blocking issues
```bash
opencode-review --output json | jq '.merge_decision.decision'
```

### Review with all agents
```bash
opencode-review --include-optional -v
```

### Generate all documentation
```bash
opencode-review-generate-docs --all --force
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: PR Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v2
      - run: uv tool install opencode-python
      - run: opencode-review --base-ref ${{ github.base_ref }} --output markdown > review.md
      - uses: actions/upload-artifact@v3
        with:
          name: review-results
          path: review.md
```

### GitLab CI Example
```yaml
pr_review:
  stage: test
  script:
    - uv tool install opencode-python
    - opencode-review --base-ref $CI_MERGE_REQUEST_TARGET_BRANCH_NAME --output json > review.json
  artifacts:
    paths:
      - review.json
  only:
    - merge_requests
```

## Development

For development:

```bash
cd /path/to/opencode_python
uv sync
uv run opencode-review --help
```

## Configuration

The review tool requires API credentials. Configure them via `.env` file in either:

1. **Project root** - `.env` file next to `pyproject.toml`
2. **User config** - `~/.config/opencode-python/.env`

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Environment Variables:**

Z.AI (default provider):
```bash
OPENCODE_PYTHON_ZAI_API_KEY=your-zai-api-key
```

Z.AI Coding Plan (FREE for coding tools):
```bash
OPENCODE_PYTHON_ZAI_CODING_PLAN_API_KEY=your-zai-coding-plan-key
```

Other providers:
```bash
OPENCODE_PYTHON_ANTHROPIC_API_KEY=your-anthropic-key
OPENCODE_PYTHON_OPENAI_API_KEY=your-openai-key
```

**Provider Settings:**

```bash
# Default provider
OPENCODE_PYTHON_PROVIDER_DEFAULT=z.ai

# Default model
OPENCODE_PYTHON_MODEL_DEFAULT=glm-4.7
```

## Requirements

- Python >= 3.11
- `uv` tool manager
- Git repository (for git diff operations)
- OpenCode API credentials (configured via environment or settings)

## Troubleshooting

**Tool not found after install:**
```bash
# Add uv tools to PATH (add to your shell profile)
export PATH="$HOME/.local/bin:$PATH"
```

**Import errors:**
Ensure all dependencies are installed:
```bash
uv tool install opencode-python --reinstall
```

**Timeout issues:**
Increase timeout for large reviews:
```bash
opencode-review --timeout 600
```
