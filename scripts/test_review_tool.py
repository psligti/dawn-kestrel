#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path


def test_cli_import():
    try:
        from dawn_kestrel.agents.review.cli import review, generate_docs

        print("✓ CLI commands imported successfully")
        print(f"  - review command name: {review.name}")
        print(f"  - generate_docs command name: {generate_docs.name}")
        return True
    except ImportError as e:
        print(f"✗ Failed to import CLI commands: {e}")
        return False


def test_click_commands():
    try:
        from click.testing import CliRunner
        from dawn_kestrel.agents.review.cli import review, generate_docs

        runner = CliRunner()

        result = runner.invoke(review, ["--help"])
        if result.exit_code == 0:
            print("✓ review --help works")
        else:
            print(f"✗ review --help failed: {result.output}")
            return False

        result = runner.invoke(generate_docs, ["--help"])
        if result.exit_code == 0:
            print("✓ generate_docs --help works")
        else:
            print(f"✗ generate_docs --help failed: {result.output}")
            return False

        return True
    except Exception as e:
        print(f"✗ Click command test failed: {e}")
        return False


def test_entry_points():
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"✗ pyproject.toml not found at {pyproject_path}")
        return False

    with open(pyproject_path) as f:
        content = f.read()

    if "dawn-kestrel" not in content:
        print("✗ dawn-kestrel entry point not found in pyproject.toml")
        return False

    print("✓ Entry point found in pyproject.toml:")
    print("  - dawn-kestrel")

    return True


def test_dependencies():
    core_dependencies = ["click", "rich"]

    optional_dependencies = ["pydantic", "aiofiles", "aiohttp", "gitpython"]

    missing_core = []
    for dep in core_dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing_core.append(dep)

    if missing_core:
        print(f"✗ Missing core dependencies: {', '.join(missing_core)}")
        return False

    missing_optional = []
    for dep in optional_dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing_optional.append(dep)

    print(f"✓ All {len(core_dependencies)} core dependencies are available")
    if missing_optional:
        print(f"  (Optional dependencies not installed: {', '.join(missing_optional)})")

    return True


def main():
    print("=" * 60)
    print("Review Agent CLI Tool Verification")
    print("=" * 60)
    print()

    tests = [
        ("Dependencies", test_dependencies),
        ("CLI Imports", test_cli_import),
        ("Click Commands", test_click_commands),
        ("Entry Points", test_entry_points),
    ]

    results = []
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        print("-" * 40)
        success = test_func()
        results.append((name, success))

    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {name}")

    print()
    print(f"Result: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All checks passed! The tool is ready for installation.")
        print("\nTo install as a uv tool:")
        print("  uv tool install .")
        print("\nThen run:")
        print("  dawn-kestrel review --help")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please fix the issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
