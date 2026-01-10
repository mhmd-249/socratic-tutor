"""Prompts module for AI tutoring system."""

from app.prompts.socratic_tutor import build_socratic_prompt
from app.prompts.summary_prompt import (
    build_detailed_summary_prompt,
    build_simple_summary_prompt,
)

__all__ = [
    "build_socratic_prompt",
    "build_detailed_summary_prompt",
    "build_simple_summary_prompt",
]
