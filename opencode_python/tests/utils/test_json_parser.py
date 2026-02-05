"""Tests for json_parser utility functions."""
from opencode_python.utils.json_parser import strip_json_code_blocks, strip_any_code_blocks


def test_strip_json_code_blocks_no_code_blocks():
    """Should return original text when no code blocks present."""
    text = '{"key": "value"}'
    result = strip_json_code_blocks(text)
    assert result == text


def test_strip_json_code_blocks_with_json_marker():
    """Should extract JSON from ```json code blocks."""
    text = '```json\n{"key": "value"}\n```'
    result = strip_json_code_blocks(text)
    assert result == '{"key": "value"}'


def test_strip_json_code_blocks_with_generic_marker():
    """Should extract JSON from ``` code blocks."""
    text = '```\n{"key": "value"}\n```'
    result = strip_json_code_blocks(text)
    assert result == '{"key": "value"}'


def test_strip_json_code_blocks_with_markdown_marker():
    """Should extract JSON from ```markdown code blocks."""
    text = '```markdown\n{"key": "value"}\n```'
    result = strip_json_code_blocks(text)
    assert result == '{"key": "value"}'


def test_strip_json_code_blocks_with_surrounding_text():
    """Should extract JSON when surrounded by other text."""
    text = 'Some text before\n```json\n{"key": "value"}\n```\nSome text after'
    result = strip_json_code_blocks(text)
    assert result == '{"key": "value"}'


def test_strip_json_code_blocks_empty_string():
    """Should handle empty strings."""
    result = strip_json_code_blocks('')
    assert result == ''


def test_strip_json_code_blocks_whitespace_only():
    """Should handle whitespace-only strings."""
    result = strip_json_code_blocks('   \n  ')
    assert result == '   \n  '.strip()


def test_strip_json_code_blocks_complex_json():
    """Should extract complex nested JSON."""
    text = '''```json
{
    "agent": "test",
    "summary": "Review complete",
    "severity": "merge",
    "findings": [
        {"id": "1", "title": "Issue", "severity": "warning"}
    ]
}
```'''
    expected = '''{
    "agent": "test",
    "summary": "Review complete",
    "severity": "merge",
    "findings": [
        {"id": "1", "title": "Issue", "severity": "warning"}
    ]
}'''
    result = strip_json_code_blocks(text)
    assert result == expected


def test_strip_any_code_blocks():
    """Should extract from ANY code block regardless of language marker."""
    text = '```python\nprint("hello")\n```'
    result = strip_any_code_blocks(text)
    assert result == 'print("hello")'


def test_strip_any_code_blocks_with_lang():
    """Should extract from language-specific code blocks."""
    text = '```typescript\nconst x = 5;\n```'
    result = strip_any_code_blocks(text)
    assert result == 'const x = 5;'
