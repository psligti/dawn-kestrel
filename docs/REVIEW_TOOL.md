# Review Agent CLI

Run multi-agent PR review using the dawn-kestrel CLI.

## Installation

Install as tool globally using uv:

```bash
uv tool install dawn-kestrel
```

This will install the `dawn-kestrel` CLI with review subcommands.

## Usage

### Running PR Review

```bash
# Review current branch against main (default) - runs all agents
dawn-kestrel review

# Run only a specific agent (e.g., security, architecture, linting)
dawn-kestrel review --agent security

# Review against a specific base branch
dawn-kestrel review --base-ref develop

# Review from base to specific commit
dawn-kestrel review --base-ref main --head-ref abc123

# Include optional review agents (diff_scoper, requirements, performance, dependencies, changelog)
dawn-kestrel review --include-optional

# Output in JSON format
dawn-kestrel review --output json

# Output in Markdown format
dawn-kestrel review --output markdown

# Enable verbose logging to see detailed debugging info
dawn-kestrel review -v

# Custom timeout (seconds)
dawn-kestrel review --timeout 600

# Review a different repository
dawn-kestrel review --repo-root /path/to/repo
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
dawn-kestrel docs --agent security

# Generate docs for all agents
dawn-kestrel docs --all

# Force regeneration even if hash matches
dawn-kestrel docs --all --force

# Custom output directory
dawn-kestrel docs --all --output ./docs

# Verbose mode
dawn-kestrel docs --all -v
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

### `dawn-kestrel review`
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

### `dawn-kestrel docs`
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
dawn-kestrel review --base-ref main
```

### Quick check for blocking issues
```bash
dawn-kestrel review --output json | jq '.merge_decision.decision'
```

### Review with all agents
```bash
dawn-kestrel review --include-optional -v
```

### Generate all documentation
```bash
dawn-kestrel docs --all --force
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
      - run: uv tool install dawn-kestrel
      - run: dawn-kestrel review --base-ref ${{ github.base_ref }} --output markdown > review.md
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
    - uv tool install dawn-kestrel
    - dawn-kestrel review --base-ref $CI_MERGE_REQUEST_TARGET_BRANCH_NAME --output json > review.json
  artifacts:
    paths:
      - review.json
  only:
    - merge_requests
```

## Development

For development:

```bash
cd /path/to/repo_root
uv sync
uv run dawn-kestrel --help
```

## Configuration

The review tool requires API credentials. Configure them via `.env` file in either:

1. **Project root** - `.env` file next to `pyproject.toml`
2. **User config** - `~/.config/dawn-kestrel/.env`

**Legacy config locations (still supported for compatibility):**
- `~/.config/opencode-python/.env` (deprecated)
- `~/.config/opencode_python/.env` (deprecated)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Environment Variables:**

Z.AI (default provider):
```bash
DAWN_KESTREL_ZAI_API_KEY=your-zai-api-key
```

Z.AI Coding Plan (FREE for coding tools):
```bash
DAWN_KESTREL_ZAI_CODING_PLAN_API_KEY=your-zai-coding-plan-key
```

Other providers:
```bash
DAWN_KESTREL_ANTHROPIC_API_KEY=your-anthropic-key
DAWN_KESTREL_OPENAI_API_KEY=your-openai-key
```

**Provider Settings:**

```bash
# Default provider
DAWN_KESTREL_PROVIDER_DEFAULT=z.ai

# Default model
DAWN_KESTREL_MODEL_DEFAULT=glm-4.7
```

**Legacy Environment Variables (deprecated, still supported):**
- `OPENCODE_PYTHON_ZAI_API_KEY` (use `DAWN_KESTREL_ZAI_API_KEY`)
- `OPENCODE_PYTHON_PROVIDER_DEFAULT` (use `DAWN_KESTREL_PROVIDER_DEFAULT`)
- Other `OPENCODE_PYTHON_*` variables (use `DAWN_KESTREL_*`)

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
uv tool install dawn-kestrel --reinstall
```

**Timeout issues:**
Increase timeout for large reviews:
```bash
dawn-kestrel review --timeout 600
```
