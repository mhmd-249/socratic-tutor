"""Socratic tutoring prompts for AI teaching assistant."""

from typing import Any


SOCRATIC_SYSTEM_PROMPT = """You are an expert AI tutor using the Socratic method to help students learn AI and machine learning concepts. Your teaching philosophy embodies these core principles:

## Core Teaching Principles

1. **Never Give Direct Answers Immediately**
   - Guide students to discover answers through questioning
   - Let them struggle productively with concepts
   - Only provide explanations after they've demonstrated effort

2. **Ask Probing Questions**
   - Assess current understanding before explaining
   - Use questions to reveal gaps in knowledge
   - Build from what they know to what they need to learn

3. **Build on Existing Knowledge**
   - Connect new concepts to familiar ideas
   - Reference their previous statements and understanding
   - Create bridges between concepts

4. **Provide Hints, Not Solutions**
   - Give progressively clearer hints if they struggle
   - Start with gentle nudges, escalate if needed
   - Never rob them of the "aha!" moment

5. **Use Analogies and Examples**
   - Make abstract concepts concrete
   - Draw from real-world scenarios
   - Use the textbook examples when relevant

6. **Check Understanding Frequently**
   - Don't move forward until concepts are grasped
   - Ask them to explain back to you
   - Probe for misconceptions

7. **Be Encouraging and Patient**
   - Celebrate insights and effort, not just correct answers
   - Normalize confusion as part of learning
   - Create a safe space for mistakes

8. **Stay Focused**
   - Keep conversations centered on chapter concepts
   - Gently redirect off-topic discussions
   - Link back to learning objectives

## You Have Access To

**Course Materials**: You have relevant excerpts from the textbook. Use these to:
- Verify accuracy of your explanations
- Reference specific definitions and examples
- Guide students to key passages
- Ground discussions in authoritative content

**Student Context**: You have information about:
- What they've studied before (learning profile)
- Their conversation history
- Concepts they've struggled with
- Topics they've mastered

## Your Communication Style

- **Conversational**: Write naturally, like a friendly but knowledgeable mentor
- **Concise**: Keep responses focused - no walls of text
- **Responsive**: Address their specific question or confusion
- **Adaptive**: Match their level - explain differently if they don't get it

## Example Socratic Interactions

**❌ Bad (Direct Answer)**:
Student: "What is backpropagation?"
Tutor: "Backpropagation is an algorithm that calculates gradients..."

**✅ Good (Socratic)**:
Student: "What is backpropagation?"
Tutor: "Great question! Before I explain, let me check your intuition. When a neural network makes a prediction that's wrong, what do you think needs to happen to improve it?"

**❌ Bad (Too Much Info)**:
Student: "I don't understand gradient descent."
Tutor: [Provides 3 paragraphs explaining gradient descent, learning rates, local minima, etc.]

**✅ Good (Focused & Probing)**:
Student: "I don't understand gradient descent."
Tutor: "Let's break this down. Imagine you're hiking down a mountain in fog - you can only see the ground right beneath your feet. What strategy would you use to find the bottom? How is that similar to what an algorithm might do when trying to minimize error?"

## Remember

Your goal is to help students **think** and **understand**, not just to give them information. The best learning happens when they arrive at insights themselves, guided by your questions.
"""


def build_socratic_prompt(
    chapter_context: dict[str, Any],
    retrieved_content: str,
    learning_profile: dict[str, Any] | None = None,
    conversation_summary: str | None = None,
) -> str:
    """
    Build the complete system prompt for Socratic tutoring.

    Args:
        chapter_context: Information about the current chapter
        retrieved_content: RAG-retrieved content from textbook
        learning_profile: User's learning profile (optional)
        conversation_summary: Summary of conversation so far (optional)

    Returns:
        Complete formatted system prompt
    """
    # Extract chapter info
    chapter_title = chapter_context.get("chapter_title", "Unknown Chapter")
    chapter_number = chapter_context.get("chapter_number", "?")
    book_title = chapter_context.get("book_title", "Unknown Book")
    book_author = chapter_context.get("book_author", "Unknown Author")
    summary = chapter_context.get("summary", "No summary available")
    key_concepts = chapter_context.get("key_concepts", [])

    # Build chapter context section
    chapter_section = f"""
## Current Chapter Context

**Book**: {book_title} by {book_author}
**Chapter {chapter_number}**: {chapter_title}

**Chapter Summary**: {summary}

**Key Concepts to Cover**:
{_format_list(key_concepts) if key_concepts else "- No specific concepts listed"}
"""

    # Build retrieved content section
    content_section = f"""
## Relevant Textbook Content

{retrieved_content}

Use this content to ground your responses and guide students to these specific passages when relevant.
"""

    # Build learning profile section (if available)
    profile_section = ""
    if learning_profile:
        strengths = learning_profile.get("strengths", [])
        gaps = learning_profile.get("identified_gaps", [])

        profile_section = "\n## Student Learning Profile\n"

        if strengths:
            profile_section += f"\n**Known Strengths**:\n{_format_list(strengths)}\n"

        if gaps:
            gap_concepts = [gap.get("concept", "") for gap in gaps if isinstance(gap, dict)]
            if gap_concepts:
                profile_section += f"\n**Known Gaps/Struggles**:\n{_format_list(gap_concepts)}\n"

        profile_section += "\nUse this context to build on their strengths and address their gaps.\n"

    # Build conversation summary section (if available)
    summary_section = ""
    if conversation_summary:
        summary_section = f"""
## Conversation So Far

{conversation_summary}

Continue building on this discussion. Reference earlier points when relevant.
"""

    # Combine all sections
    full_prompt = SOCRATIC_SYSTEM_PROMPT + chapter_section

    if retrieved_content and retrieved_content.strip():
        full_prompt += content_section

    if profile_section:
        full_prompt += profile_section

    if summary_section:
        full_prompt += summary_section

    return full_prompt


def build_initial_greeting_prompt(
    chapter_context: dict[str, Any],
    learning_profile: dict[str, Any] | None = None,
) -> str:
    """
    Build a prompt for generating an initial greeting.

    Args:
        chapter_context: Information about the current chapter
        learning_profile: User's learning profile with gaps and strengths (optional)

    Returns:
        Prompt for initial greeting
    """
    chapter_title = chapter_context.get("chapter_title", "this chapter")
    key_concepts = chapter_context.get("key_concepts", [])

    concepts_str = ", ".join(key_concepts[:3]) if key_concepts else "the topics in this chapter"

    # Build profile context section
    profile_section = ""
    if learning_profile:
        gaps = learning_profile.get("identified_gaps", [])
        strengths = learning_profile.get("strengths", [])

        if gaps or strengths:
            profile_section = "\n\n## Student Context (use this to personalize your greeting)\n"

            if gaps:
                # Extract gap concepts with severity
                gap_info = []
                for gap in gaps[:3]:  # Top 3 gaps
                    if isinstance(gap, dict):
                        concept = gap.get("concept", "")
                        severity = gap.get("severity", "low")
                        if concept:
                            gap_info.append(f"- {concept} (struggled {severity} severity)")
                    elif gap:
                        gap_info.append(f"- {gap}")

                if gap_info:
                    profile_section += "\n**Known Struggles** (acknowledge gently, offer support):\n"
                    profile_section += "\n".join(gap_info)
                    profile_section += "\n"

            if strengths:
                profile_section += f"\n**Known Strengths**: {', '.join(strengths[:5])}\n"

            profile_section += """
When relevant, acknowledge their previous struggles supportively. For example:
- "I know [topic] can be tricky - let's explore it together"
- "We've worked on [topic] before - let's build on that"
"""

    return f"""Generate a warm, friendly greeting to start a tutoring session on "{chapter_title}".
{profile_section}
Your greeting should:
1. Welcome the student warmly
2. Express enthusiasm about the topic
3. If the student has known struggles related to this chapter, acknowledge them supportively
4. Ask an opening question to assess their current familiarity with {concepts_str}
5. Keep it brief (2-4 sentences max)
6. Set a collaborative, encouraging tone

Do NOT explain concepts yet - just greet, optionally acknowledge past struggles, and ask an initial assessment question."""


def build_summary_prompt(messages: list[dict[str, str]]) -> str:
    """
    Build a prompt for generating a conversation summary.

    Args:
        messages: List of conversation messages

    Returns:
        Prompt for generating summary
    """
    # Format conversation
    conversation_text = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            conversation_text += f"\nStudent: {content}\n"
        elif role == "assistant":
            conversation_text += f"\nTutor: {content}\n"

    return f"""Analyze this tutoring conversation and generate a structured summary.

## Conversation

{conversation_text}

## Generate Summary

Provide a JSON summary with:
1. **topics_covered**: List of main topics discussed (array of strings)
2. **concepts_understood**: Concepts the student seemed to grasp well (array of strings)
3. **concepts_struggled**: Concepts the student struggled with (array of strings)
4. **questions_asked**: Total number of questions student asked (integer)
5. **engagement_score**: Rate engagement 0.0-1.0 based on:
   - Question quality and frequency
   - Depth of responses
   - Evidence of thinking and reasoning
6. **summary**: Brief narrative summary (2-3 sentences)

Return ONLY valid JSON, no additional text."""


def _format_list(items: list[str]) -> str:
    """Format a list of items as bullet points."""
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)
