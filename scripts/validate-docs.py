#!/usr/bin/env python3
"""Validate reviewer entry point documentation.

This script validates YAML frontmatter in docs/reviewers/*.md files to ensure
they follow the required schema for PR review entry points.

Usage:
    scripts/validate-docs.py

Exit codes:
    0: All validations pass
    1: Validation fails
"""

import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple


def parse_frontmatter(content: str) -> Tuple[str, Dict[str, Any]]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: File content as string

    Returns:
        Tuple of (frontmatter_yaml, frontmatter_dict)

    Raises:
        ValueError: If frontmatter is missing or invalid
    """
    frontmatter_pattern = r'^---\n(.*?)\n---'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        raise ValueError("Missing YAML frontmatter (must start with ---)")

    yaml_content = match.group(1)

    # Parse YAML (simple key-value pairs and multi-line arrays)
    frontmatter = {}
    lines = yaml_content.split('\n')
    current_key = None
    in_array = False
    current_item_lines = []

    for line in lines:
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue

        # Check for array item start (indented with "- ")
        if in_array and re.match(r'^\s+-\s+', line):
            # Start of new array item
            if current_item_lines:
                array_values.append('\n'.join(current_item_lines))
            # Remove the "- " prefix
            item_line = re.sub(r'^-\s+', '', line.lstrip())
            current_item_lines = [item_line]
            continue
        elif in_array and line.startswith(' '):
            # Continuation of current array item
            if current_item_lines:
                current_item_lines.append(line.lstrip())
            continue
        elif in_array:
            # End of array (no longer indented)
            if current_item_lines:
                array_values.append('\n'.join(current_item_lines))
                current_item_lines = []
            frontmatter[current_key] = array_values
            in_array = False

        # Check for key-value pair
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Check if this is the start of an array
            if value == '':
                current_key = key
                in_array = True
                array_values = []
            else:
                # Remove quotes if present
                value = value.strip('"\'')
                frontmatter[key] = value

    # Handle case where file ends with array
    if in_array:
        if current_item_lines:
            array_values.append('\n'.join(current_item_lines))
        frontmatter[current_key] = array_values

    return yaml_content, frontmatter


def validate_patterns(patterns: List[str]) -> List[str]:
    """Validate pattern list structure.

    Args:
        patterns: List of pattern YAML strings

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not isinstance(patterns, list):
        return ["'patterns' must be a list"]

    if len(patterns) < 3:
        errors.append(f"'patterns' must have at least 3 entries (found {len(patterns)})")

    for i, pattern_yaml in enumerate(patterns):
        # Parse individual pattern
        pattern = {}
        for line in pattern_yaml.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                pattern[key.strip()] = value.strip()

        # Check required fields
        if 'type' not in pattern:
            errors.append(f"Pattern {i+1}: missing 'type' field")
        elif pattern['type'] not in ['ast', 'file_path', 'content']:
            errors.append(f"Pattern {i+1}: 'type' must be 'ast', 'file_path', or 'content' (found '{pattern['type']}')")

        if 'pattern' not in pattern:
            errors.append(f"Pattern {i+1}: missing 'pattern' field")

        if 'weight' not in pattern:
            errors.append(f"Pattern {i+1}: missing 'weight' field")
        else:
            try:
                weight = float(pattern['weight'])
                if not (0.0 <= weight <= 1.0):
                    errors.append(f"Pattern {i+1}: 'weight' must be between 0.0 and 1.0 (found {weight})")
            except ValueError:
                errors.append(f"Pattern {i+1}: 'weight' must be a number (found '{pattern['weight']}')")

        # For ast and content types, 'language' is required
        if 'type' in pattern and pattern['type'] in ['ast', 'content']:
            if 'language' not in pattern:
                errors.append(f"Pattern {i+1}: 'language' field required for type '{pattern['type']}'")

    return errors


def validate_frontmatter(file_path: Path, frontmatter: Dict[str, Any]) -> List[str]:
    """Validate frontmatter structure and required fields.

    Args:
        file_path: Path to the file being validated
        frontmatter: Parsed frontmatter dictionary

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check required fields
    required_fields = ['agent', 'agent_type', 'patterns', 'heuristics']
    for field in required_fields:
        if field not in frontmatter:
            errors.append(f"Missing required field: '{field}'")

    # Validate agent_type
    if 'agent_type' in frontmatter:
        valid_types = ['required', 'optional']
        if frontmatter['agent_type'] not in valid_types:
            errors.append(f"'agent_type' must be one of {valid_types} (found '{frontmatter['agent_type']}')")

    # Validate patterns
    if 'patterns' in frontmatter:
        pattern_errors = validate_patterns(frontmatter['patterns'])
        errors.extend(pattern_errors)

    # Validate heuristics
    if 'heuristics' in frontmatter:
        if not isinstance(frontmatter['heuristics'], list):
            errors.append("'heuristics' must be a list")
        elif len(frontmatter['heuristics']) == 0:
            errors.append("'heuristics' must have at least 1 entry")

    return errors


def validate_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Validate a single reviewer documentation file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (is_valid, error_messages)
    """
    try:
        content = file_path.read_text()

        # Parse frontmatter
        yaml_content, frontmatter = parse_frontmatter(content)

        # Validate structure
        errors = validate_frontmatter(file_path, frontmatter)

        if errors:
            return False, errors

        return True, []

    except ValueError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Unexpected error: {str(e)}"]


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("Validating reviewer entry point documentation...")
    print()

    # Find all markdown files in docs/reviewers/
    reviewers_dir = Path("docs/reviewers")

    if not reviewers_dir.exists():
        print(f"✗ Error: Directory '{reviewers_dir}' not found")
        return 1

    md_files = list(reviewers_dir.glob("*.md"))

    if not md_files:
        print(f"✗ Error: No markdown files found in '{reviewers_dir}'")
        return 1

    print(f"Found {len(md_files)} reviewer documentation file(s)")
    print()

    # Validate each file
    all_valid = True
    file_errors: Dict[Path, List[str]] = {}

    for file_path in sorted(md_files):
        is_valid, errors = validate_file(file_path)

        if is_valid:
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path}")
            file_errors[file_path] = errors
            all_valid = False

    # Print errors if any
    if file_errors:
        print()
        print("Validation errors:")
        print()

        for file_path, errors in sorted(file_errors.items()):
            print(f"{file_path}:")
            for error in errors:
                print(f"  - {error}")
            print()

    if all_valid:
        print()
        print("✓ All validations passed!")
        return 0
    else:
        print()
        print(f"✗ Validation failed for {len(file_errors)} file(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
