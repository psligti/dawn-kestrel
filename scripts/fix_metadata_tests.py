#!/usr/bin/env python3
"""Fix metadata tests in review agent test files."""

files = [
    ("test_diff_scoper_reviewer.py", "diff_scoper", "Diff Scoper Subagent", ["**/*"]),
    (
        "test_documentation_reviewer.py",
        "documentation",
        "Documentation Review Subagent",
        ["**/*.py", "README*", "docs/**", "*.md", "pyproject.toml", "setup.cfg", ".env.example"],
    ),
    (
        "test_performance_reviewer.py",
        "performance",
        "Performance & Reliability Review Subagent",
        [
            "**/*.py",
            "**/*.rs",
            "**/*.go",
            "**/*.js",
            "**/*.ts",
            "**/*.tsx",
            "**/config/**",
            "**/database/**",
            "**/db/**",
            "**/network/**",
            "**/api/**",
            "**/services/**",
        ],
    ),
    (
        "test_release_changelog_reviewer.py",
        "release_changelog",
        "Release & Changelog Review Subagent",
        [
            "CHANGELOG*",
            "CHANGES*",
            "HISTORY*",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "**/__init__.py",
            "**/*.py",
        ],
    ),
    ("test_requirements_reviewer.py", "requirements", "Requirements Review Subagent", ["**/*"]),
    (
        "test_telemetry_reviewer.py",
        "telemetry",
        "Telemetry & Metrics Review Subagent",
        [
            "**/*.py",
            "**/logging/**",
            "**/observability/**",
            "**/metrics/**",
            "**/tracing/**",
            "**/monitoring/**",
        ],
    ),
]

for filename, agent_name, prompt_check, pattern in files:
    print(f"Processing {filename}...")
    filepath = f"/Users/parkersligting/develop/pt/agentic_coding/.worktrees/harness-agent-rework/tests/review/agents/{filename}"
    with open(filepath, "r") as f:
        content = f.read()

    # Check if metadata test already exists
    if f"def test_{agent_name}_reviewer_metadata_helpers(" in content:
        print(f"  Metadata test already exists, skipping")
        continue

    # Add metadata test after the last test method
    metadata_test = f"""    @pytest.mark.asyncio
    async def test_{agent_name}_reviewer_metadata_helpers(self, reviewer):
        \"\"\"Test that {prompt_check.split()[0]} metadata helpers work correctly.\"\"\"
        assert reviewer.get_agent_name() == \"{agent_name}\"
        assert \"{prompt_check}\" in reviewer.get_system_prompt()
        assert reviewer.get_relevant_file_patterns() == {pattern}

"""

    # Find position of last test method
    lines = content.split("\n")
    last_def_idx = len(lines) - 1
    while last_def_idx >= 0:
        line = lines[last_def_idx]
        if "def test_" in line and "async def" in line:
            break
        last_def_idx -= 1

    if last_def_idx >= 0:
        # Insert after last test method
        new_content = (
            "\n".join(lines[: last_def_idx + 1])
            + "\n"
            + metadata_test
            + "\n".join(lines[last_def_idx + 1 :])
        )

        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"  Updated {filename}")
    else:
        print(f"  Warning: No test method found in {filename}")

print("Done!")
