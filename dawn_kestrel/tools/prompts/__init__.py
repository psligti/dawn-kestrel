"""OpenCode Python Tool Prompts"""
import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def get_prompt(prompt_name: str) -> str:
    """Load prompt template by name"""
    prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt '{prompt_name}' not found at {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

__all__ = ["get_prompt"]
