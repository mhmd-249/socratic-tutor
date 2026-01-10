"""Conversation summary generation prompts."""

from typing import Any


SUMMARY_SYSTEM_PROMPT = """You are an expert educational analyst specializing in assessing learning conversations. Your task is to analyze tutoring sessions and extract structured insights about student understanding.

You must ALWAYS respond with valid JSON only - no additional text, markdown, or explanations outside the JSON structure."""


SUMMARY_PROMPT_TEMPLATE = """Analyze this tutoring conversation and provide a structured assessment.

## Conversation Context
**Chapter**: {chapter_title}
**Book**: {book_title}
**Key Concepts**: {key_concepts}

## Conversation Transcript
{conversation_transcript}

## Analysis Instructions

Carefully analyze the conversation to identify:

1. **Topics Actually Discussed**: What specific topics from the chapter were covered?

2. **Concepts Understood**: Look for evidence that the student:
   - Correctly explained or paraphrased concepts
   - Made accurate connections between ideas
   - Applied concepts correctly
   - Asked insightful clarifying questions

3. **Concepts Struggled With**: Look for evidence that the student:
   - Gave incorrect explanations
   - Showed confusion or misconceptions
   - Needed multiple hints or explanations
   - Avoided or deflected certain topics

4. **Engagement Level**: Consider:
   - Quality and depth of student responses
   - Initiative in asking questions
   - Evidence of active thinking vs. passive listening
   - Effort shown when struggling

5. **Prerequisite Gaps**: Identify any foundational concepts the student seems to be missing that would help them understand the current material better.

## Required JSON Response Format

Respond with ONLY this JSON structure (no markdown code blocks, no extra text):

{{
    "summary": "2-3 sentence narrative summary of what was discussed and learned",
    "topics_covered": ["specific topic 1", "specific topic 2"],
    "concepts_understood": [
        {{
            "concept": "concept name",
            "confidence": 0.8,
            "evidence": "student correctly explained that..."
        }}
    ],
    "concepts_struggled": [
        {{
            "concept": "concept name",
            "severity": "high",
            "evidence": "student was confused about..."
        }}
    ],
    "questions_asked_by_student": 5,
    "engagement_level": "high",
    "engagement_score": 0.75,
    "recommended_next_steps": ["review concept X", "practice with Y examples"],
    "prerequisite_gaps": ["foundational concept they seem to be missing"]
}}

Notes:
- confidence: float from 0.0 to 1.0
- severity: "high", "medium", or "low"
- engagement_level: "high", "medium", or "low"
- engagement_score: float from 0.0 to 1.0
- All arrays can be empty [] if not applicable
- Be specific - use actual concept names from the conversation"""


def build_detailed_summary_prompt(
    messages: list[dict[str, str]],
    chapter_context: dict[str, Any],
) -> tuple[str, str]:
    """
    Build a detailed prompt for generating conversation summary.

    Args:
        messages: List of conversation messages with 'role' and 'content' keys
        chapter_context: Context about the chapter being studied

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format conversation transcript
    transcript_lines = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            transcript_lines.append(f"STUDENT: {content}")
        elif role == "assistant":
            transcript_lines.append(f"TUTOR: {content}")
        # Skip system messages

    conversation_transcript = "\n\n".join(transcript_lines)

    # Extract chapter info
    chapter_title = chapter_context.get("chapter_title", "Unknown Chapter")
    book_title = chapter_context.get("book_title", "Unknown Book")
    key_concepts = chapter_context.get("key_concepts", [])
    key_concepts_str = ", ".join(key_concepts) if key_concepts else "Not specified"

    # Format the prompt
    user_prompt = SUMMARY_PROMPT_TEMPLATE.format(
        chapter_title=chapter_title,
        book_title=book_title,
        key_concepts=key_concepts_str,
        conversation_transcript=conversation_transcript,
    )

    return SUMMARY_SYSTEM_PROMPT, user_prompt


def build_simple_summary_prompt(messages: list[dict[str, str]]) -> str:
    """
    Build a simple summary prompt for basic analysis.

    Falls back to this if chapter context is unavailable.

    Args:
        messages: List of conversation messages

    Returns:
        Combined prompt string
    """
    # Format conversation
    transcript_lines = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            transcript_lines.append(f"STUDENT: {content}")
        elif role == "assistant":
            transcript_lines.append(f"TUTOR: {content}")

    conversation_transcript = "\n\n".join(transcript_lines)

    return f"""Analyze this tutoring conversation and generate a structured summary.

## Conversation

{conversation_transcript}

## Generate Summary

Respond with ONLY valid JSON (no markdown, no extra text):

{{
    "summary": "2-3 sentence summary of the conversation",
    "topics_covered": ["topic1", "topic2"],
    "concepts_understood": ["concept1", "concept2"],
    "concepts_struggled": ["concept1"],
    "questions_asked": 5,
    "engagement_score": 0.75
}}

Notes:
- engagement_score should be between 0.0 and 1.0
- Be specific about actual topics and concepts discussed
- Arrays can be empty if not applicable"""
