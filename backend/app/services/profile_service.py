"""Learning profile service for tracking student progress and recommendations."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.models.conversation_summary import ConversationSummary
from app.models.learning_profile import LearningProfile
from app.repositories.chapter import ChapterRepository
from app.repositories.conversation_summary import ConversationSummaryRepository
from app.repositories.learning_profile import LearningProfileRepository

logger = logging.getLogger(__name__)


# Data classes for structured data
@dataclass
class ConceptAssessment:
    """Assessment of a concept from a conversation."""

    concept: str
    understood: bool
    confidence: float = 0.5  # 0.0-1.0 for understood, severity for struggled
    evidence: str = ""


@dataclass
class ChapterMastery:
    """Mastery information for a chapter."""

    chapter_id: str
    score: float  # 0.0-1.0
    last_studied: str  # ISO datetime
    concepts_covered: list[str] = field(default_factory=list)
    study_count: int = 1


@dataclass
class IdentifiedGap:
    """An identified knowledge gap."""

    concept: str
    severity: str  # "high", "medium", "low"
    occurrence_count: int
    related_chapters: list[str]
    first_seen: str  # ISO datetime
    last_seen: str  # ISO datetime


@dataclass
class ChapterRecommendation:
    """A recommended chapter for the user."""

    chapter_id: str
    chapter_title: str
    chapter_number: int
    book_title: str
    reason: str
    priority: float  # 0.0-1.0, higher = more urgent


@dataclass
class ProfileContext:
    """Context from learning profile for conversation."""

    strengths: list[str]
    relevant_gaps: list[IdentifiedGap]
    past_discussions: list[dict[str, Any]]
    chapter_mastery: ChapterMastery | None
    related_chapters_studied: list[str]


class ProfileService:
    """Service for managing learning profiles and recommendations."""

    # Constants for mastery calculation
    RECENCY_WEIGHT = 0.7  # Weight for new evidence vs old score
    MIN_SCORE = 0.0
    MAX_SCORE = 1.0
    DEFAULT_SCORE = 0.3  # Starting score for new concepts

    # Gap severity thresholds
    HIGH_SEVERITY_THRESHOLD = 3  # occurrences
    MEDIUM_SEVERITY_THRESHOLD = 2

    def __init__(self, session: AsyncSession):
        """
        Initialize profile service.

        Args:
            session: Database session
        """
        self.session = session
        self.profile_repo = LearningProfileRepository(session)
        self.chapter_repo = ChapterRepository(session)
        self.summary_repo = ConversationSummaryRepository(session)

    async def get_or_create_profile(self, user_id: UUID) -> LearningProfile:
        """
        Get existing profile or create new one.

        Args:
            user_id: User UUID

        Returns:
            LearningProfile model
        """
        profile = await self.profile_repo.get_by_user(user_id)

        if profile:
            return profile

        # Create new profile
        logger.info(f"Creating new learning profile for user {user_id}")
        profile_data = {
            "id": uuid4(),
            "user_id": user_id,
            "mastery_map": {},
            "identified_gaps": [],
            "strengths": [],
            "recommended_chapters": [],
            "total_study_time_minutes": 0,
            "updated_at": datetime.utcnow(),
        }

        profile = await self.profile_repo.create(profile_data)
        await self.session.commit()

        return profile

    async def update_from_summary(
        self,
        user_id: UUID,
        summary: ConversationSummary,
        chapter: Chapter,
    ) -> LearningProfile:
        """
        Update learning profile based on new conversation summary.

        This is called after every conversation ends.

        Args:
            user_id: User UUID
            summary: Conversation summary with concepts understood/struggled
            chapter: Chapter that was studied

        Returns:
            Updated LearningProfile
        """
        logger.info(f"Updating profile for user {user_id} from conversation summary")

        profile = await self.get_or_create_profile(user_id)

        # Build concept assessments from summary
        assessments = self._build_assessments_from_summary(summary)

        # Update mastery map for this chapter
        updated_mastery_map = self._update_mastery_map(
            profile.mastery_map or {},
            str(chapter.id),
            assessments,
            chapter.key_concepts or [],
        )

        # Update identified gaps
        updated_gaps = self._update_gaps(
            profile.identified_gaps or [],
            assessments,
            str(chapter.id),
        )

        # Update strengths based on high-confidence understood concepts
        updated_strengths = self._update_strengths(
            profile.strengths or [],
            assessments,
        )

        # Calculate study time (rough estimate based on messages)
        estimated_minutes = max(5, summary.questions_asked * 2)

        # Get recommended chapters
        recommended = await self._calculate_recommendations(
            user_id,
            updated_mastery_map,
            updated_gaps,
            chapter,
        )

        # Update profile
        await self.profile_repo.update(
            profile.id,
            {
                "mastery_map": updated_mastery_map,
                "identified_gaps": updated_gaps,
                "strengths": updated_strengths,
                "recommended_chapters": recommended,
                "total_study_time_minutes": (profile.total_study_time_minutes or 0)
                + estimated_minutes,
                "updated_at": datetime.utcnow(),
            },
        )
        await self.session.commit()

        # Refresh profile
        updated_profile = await self.profile_repo.get_by_user(user_id)

        logger.info(
            f"Profile updated: {len(updated_strengths)} strengths, "
            f"{len(updated_gaps)} gaps, {len(recommended)} recommendations"
        )

        return updated_profile

    async def get_recommended_chapters(
        self,
        user_id: UUID,
        book_id: UUID | None = None,
    ) -> list[ChapterRecommendation]:
        """
        Get personalized chapter recommendations based on profile.

        Args:
            user_id: User UUID
            book_id: Optional book to filter recommendations

        Returns:
            List of ChapterRecommendation objects
        """
        profile = await self.get_or_create_profile(user_id)
        recommendations = []

        if not profile.recommended_chapters:
            # No specific recommendations, suggest chapters based on gaps
            if profile.identified_gaps:
                for gap in profile.identified_gaps[:3]:  # Top 3 gaps
                    if isinstance(gap, dict):
                        related = gap.get("related_chapters", [])
                        for chapter_id in related[:1]:  # First related chapter
                            chapter = await self.chapter_repo.get(UUID(chapter_id))
                            if chapter:
                                book = await self.chapter_repo.session.get(
                                    type(chapter.book), chapter.book_id
                                )
                                recommendations.append(
                                    ChapterRecommendation(
                                        chapter_id=str(chapter.id),
                                        chapter_title=chapter.title,
                                        chapter_number=chapter.chapter_number,
                                        book_title=book.title if book else "Unknown",
                                        reason=f"Addresses gap: {gap.get('concept', 'Unknown')}",
                                        priority=0.8,
                                    )
                                )
            return recommendations

        # Build recommendations from stored chapter IDs
        for chapter_id in profile.recommended_chapters[:5]:  # Top 5
            try:
                chapter = await self.chapter_repo.get(chapter_id)
                if not chapter:
                    continue

                if book_id and chapter.book_id != book_id:
                    continue

                # Find reason for recommendation
                reason = self._get_recommendation_reason(
                    str(chapter.id),
                    profile.mastery_map or {},
                    profile.identified_gaps or [],
                    chapter,
                )

                from app.repositories.book import BookRepository

                book_repo = BookRepository(self.session)
                book = await book_repo.get(chapter.book_id)

                recommendations.append(
                    ChapterRecommendation(
                        chapter_id=str(chapter.id),
                        chapter_title=chapter.title,
                        chapter_number=chapter.chapter_number,
                        book_title=book.title if book else "Unknown",
                        reason=reason,
                        priority=0.7,
                    )
                )
            except Exception as e:
                logger.warning(f"Error getting chapter {chapter_id}: {e}")
                continue

        return recommendations

    async def get_context_for_conversation(
        self,
        user_id: UUID,
        chapter_id: UUID,
    ) -> ProfileContext:
        """
        Get relevant profile info to include in chat context.

        Args:
            user_id: User UUID
            chapter_id: Chapter being studied

        Returns:
            ProfileContext with relevant information
        """
        profile = await self.get_or_create_profile(user_id)
        chapter = await self.chapter_repo.get(chapter_id)

        # Get chapter mastery if exists
        chapter_mastery = None
        mastery_map = profile.mastery_map or {}
        if str(chapter_id) in mastery_map:
            mastery_data = mastery_map[str(chapter_id)]
            chapter_mastery = ChapterMastery(
                chapter_id=str(chapter_id),
                score=mastery_data.get("score", 0.0),
                last_studied=mastery_data.get("last_studied", ""),
                concepts_covered=mastery_data.get("concepts_covered", []),
                study_count=mastery_data.get("study_count", 0),
            )

        # Find gaps relevant to this chapter's concepts
        chapter_concepts = set(chapter.key_concepts or []) if chapter else set()
        relevant_gaps = []
        for gap in profile.identified_gaps or []:
            if isinstance(gap, dict):
                gap_concept = gap.get("concept", "").lower()
                # Check if gap relates to any chapter concept
                for concept in chapter_concepts:
                    if (
                        gap_concept in concept.lower()
                        or concept.lower() in gap_concept
                    ):
                        relevant_gaps.append(
                            IdentifiedGap(
                                concept=gap.get("concept", ""),
                                severity=gap.get("severity", "medium"),
                                occurrence_count=gap.get("occurrence_count", 1),
                                related_chapters=gap.get("related_chapters", []),
                                first_seen=gap.get("first_seen", ""),
                                last_seen=gap.get("last_seen", ""),
                            )
                        )
                        break

        # Get past discussions about this chapter
        past_discussions = []
        summaries = await self.summary_repo.get_by_user(user_id, limit=5)
        for summary in summaries:
            if summary.conversation:
                if summary.conversation.chapter_id == chapter_id:
                    past_discussions.append(
                        {
                            "summary": summary.summary,
                            "topics_covered": summary.topics_covered,
                            "concepts_understood": summary.concepts_understood,
                            "concepts_struggled": summary.concepts_struggled,
                            "date": (
                                summary.created_at.isoformat()
                                if summary.created_at
                                else ""
                            ),
                        }
                    )

        # Find related chapters user has studied
        related_chapters_studied = []
        if chapter and chapter.prerequisites:
            for prereq_id in chapter.prerequisites:
                if str(prereq_id) in mastery_map:
                    prereq = await self.chapter_repo.get(prereq_id)
                    if prereq:
                        related_chapters_studied.append(prereq.title)

        return ProfileContext(
            strengths=profile.strengths or [],
            relevant_gaps=relevant_gaps,
            past_discussions=past_discussions,
            chapter_mastery=chapter_mastery,
            related_chapters_studied=related_chapters_studied,
        )

    # Private helper methods

    def _build_assessments_from_summary(
        self, summary: ConversationSummary
    ) -> list[ConceptAssessment]:
        """Build concept assessments from conversation summary."""
        assessments = []

        # Add understood concepts
        for concept in summary.concepts_understood or []:
            if isinstance(concept, str):
                assessments.append(
                    ConceptAssessment(
                        concept=concept,
                        understood=True,
                        confidence=0.8,  # Default confidence
                        evidence="Demonstrated understanding in conversation",
                    )
                )
            elif isinstance(concept, dict):
                assessments.append(
                    ConceptAssessment(
                        concept=concept.get("concept", str(concept)),
                        understood=True,
                        confidence=concept.get("confidence", 0.8),
                        evidence=concept.get("evidence", ""),
                    )
                )

        # Add struggled concepts
        for concept in summary.concepts_struggled or []:
            if isinstance(concept, str):
                assessments.append(
                    ConceptAssessment(
                        concept=concept,
                        understood=False,
                        confidence=0.5,  # Medium severity
                        evidence="Showed difficulty in conversation",
                    )
                )
            elif isinstance(concept, dict):
                # Convert severity to confidence-like score
                severity = concept.get("severity", "medium")
                severity_score = {"high": 0.8, "medium": 0.5, "low": 0.3}.get(
                    severity.lower(), 0.5
                )
                assessments.append(
                    ConceptAssessment(
                        concept=concept.get("concept", str(concept)),
                        understood=False,
                        confidence=severity_score,
                        evidence=concept.get("evidence", ""),
                    )
                )

        return assessments

    def _update_mastery_map(
        self,
        current_map: dict[str, Any],
        chapter_id: str,
        assessments: list[ConceptAssessment],
        chapter_concepts: list[str],
    ) -> dict[str, Any]:
        """
        Update mastery map with new assessment data.

        Uses exponential moving average for score updates.
        """
        now = datetime.utcnow().isoformat()

        # Get current chapter data or create new
        chapter_data = current_map.get(
            chapter_id,
            {
                "score": self.DEFAULT_SCORE,
                "last_studied": now,
                "concepts_covered": [],
                "study_count": 0,
            },
        )

        current_score = chapter_data.get("score", self.DEFAULT_SCORE)
        concepts_covered = set(chapter_data.get("concepts_covered", []))

        # Calculate new evidence score
        if assessments:
            understood_scores = [
                a.confidence for a in assessments if a.understood
            ]
            struggled_scores = [
                1 - a.confidence for a in assessments if not a.understood
            ]

            # Average of all evidence
            all_scores = understood_scores + struggled_scores
            if all_scores:
                evidence_score = sum(all_scores) / len(all_scores)
            else:
                evidence_score = current_score

            # Exponential moving average
            new_score = (
                self.RECENCY_WEIGHT * evidence_score
                + (1 - self.RECENCY_WEIGHT) * current_score
            )

            # Clamp to valid range
            new_score = max(self.MIN_SCORE, min(self.MAX_SCORE, new_score))
        else:
            new_score = current_score

        # Track concepts covered
        for assessment in assessments:
            concepts_covered.add(assessment.concept)
        for concept in chapter_concepts:
            concepts_covered.add(concept)

        # Update chapter data
        chapter_data = {
            "score": round(new_score, 3),
            "last_studied": now,
            "concepts_covered": list(concepts_covered),
            "study_count": chapter_data.get("study_count", 0) + 1,
        }

        # Update map
        updated_map = current_map.copy()
        updated_map[chapter_id] = chapter_data

        return updated_map

    def _find_matching_gap(
        self,
        concept: str,
        gaps_by_concept: dict[str, dict[str, Any]],
    ) -> str | None:
        """
        Find a matching gap using fuzzy concept matching.

        Matching criteria (in order):
        1. Exact match (case-insensitive)
        2. One concept contains the other
        3. High word overlap (3+ shared words or 70%+ overlap)

        Args:
            concept: The concept to match
            gaps_by_concept: Dictionary of existing gaps keyed by lowercase concept

        Returns:
            The matching gap key, or None if no match found
        """
        concept_lower = concept.lower().strip()
        concept_words = set(concept_lower.split())

        # 1. Exact match
        if concept_lower in gaps_by_concept:
            return concept_lower

        # 2. Check if one contains the other, or high word overlap
        best_match = None
        best_overlap_ratio = 0.0

        for existing_key, gap in gaps_by_concept.items():
            existing_lower = existing_key.lower().strip()
            existing_words = set(existing_lower.split())

            # Check containment (one is substring of the other)
            if concept_lower in existing_lower or existing_lower in concept_lower:
                logger.debug(
                    f"Fuzzy match (containment): '{concept}' matches '{gap.get('concept')}'"
                )
                return existing_key

            # Check word overlap
            if concept_words and existing_words:
                shared_words = concept_words & existing_words
                # Calculate overlap as ratio of shared words to smaller set
                smaller_set_size = min(len(concept_words), len(existing_words))
                overlap_ratio = len(shared_words) / smaller_set_size if smaller_set_size > 0 else 0

                # Match if 3+ shared words OR 70%+ overlap
                if len(shared_words) >= 3 or overlap_ratio >= 0.7:
                    if overlap_ratio > best_overlap_ratio:
                        best_overlap_ratio = overlap_ratio
                        best_match = existing_key

        if best_match:
            logger.debug(
                f"Fuzzy match (word overlap {best_overlap_ratio:.0%}): "
                f"'{concept}' matches '{gaps_by_concept[best_match].get('concept')}'"
            )

        return best_match

    def _update_gaps(
        self,
        current_gaps: list[dict[str, Any]],
        assessments: list[ConceptAssessment],
        chapter_id: str,
    ) -> list[dict[str, Any]]:
        """
        Update identified gaps based on new assessments.

        Uses fuzzy matching to identify similar concepts.
        Tracks occurrence patterns and severity.
        """
        now = datetime.utcnow().isoformat()

        # Convert to dict for easier lookup (keyed by lowercase concept)
        gaps_by_concept = {
            gap.get("concept", "").lower(): gap for gap in current_gaps
        }

        # Process all assessments
        for assessment in assessments:
            concept_lower = assessment.concept.lower()

            # Try to find a matching existing gap (fuzzy match)
            matching_key = self._find_matching_gap(assessment.concept, gaps_by_concept)

            if assessment.understood:
                # If they understood it now, reduce gap severity
                if matching_key:
                    gap = gaps_by_concept[matching_key]
                    # Reduce occurrence count or remove
                    occurrence = gap.get("occurrence_count", 1) - 1
                    if occurrence <= 0:
                        logger.info(
                            f"Gap resolved: '{gap.get('concept')}' - student now understands"
                        )
                        del gaps_by_concept[matching_key]
                    else:
                        gap["occurrence_count"] = occurrence
                        gap["severity"] = self._calculate_severity(occurrence)
                        logger.debug(
                            f"Gap reduced: '{gap.get('concept')}' occurrence_count={occurrence}"
                        )
            else:
                # Add or update gap for struggled concept
                if matching_key:
                    # Update existing gap
                    gap = gaps_by_concept[matching_key]
                    old_count = gap.get("occurrence_count", 1)
                    gap["occurrence_count"] = old_count + 1
                    gap["severity"] = self._calculate_severity(gap["occurrence_count"])
                    gap["last_seen"] = now
                    # Add chapter to related if not present
                    related = gap.get("related_chapters", [])
                    if chapter_id not in related:
                        related.append(chapter_id)
                        gap["related_chapters"] = related
                    logger.info(
                        f"Gap updated: '{gap.get('concept')}' "
                        f"occurrence_count={gap['occurrence_count']} severity={gap['severity']}"
                    )
                else:
                    # New gap
                    gaps_by_concept[concept_lower] = {
                        "concept": assessment.concept,
                        "severity": "low",
                        "occurrence_count": 1,
                        "related_chapters": [chapter_id],
                        "first_seen": now,
                        "last_seen": now,
                    }
                    logger.info(f"New gap identified: '{assessment.concept}'")

        # Convert back to list, sorted by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        gaps_list = sorted(
            gaps_by_concept.values(),
            key=lambda g: (
                severity_order.get(g.get("severity", "low"), 2),
                -g.get("occurrence_count", 0),
            ),
        )

        return gaps_list

    def _calculate_severity(self, occurrence_count: int) -> str:
        """Calculate gap severity based on occurrence count."""
        if occurrence_count >= self.HIGH_SEVERITY_THRESHOLD:
            return "high"
        elif occurrence_count >= self.MEDIUM_SEVERITY_THRESHOLD:
            return "medium"
        return "low"

    def _update_strengths(
        self,
        current_strengths: list[str],
        assessments: list[ConceptAssessment],
    ) -> list[str]:
        """Update strengths based on high-confidence understood concepts."""
        strengths = set(s.lower() for s in current_strengths)

        for assessment in assessments:
            if assessment.understood and assessment.confidence >= 0.8:
                strengths.add(assessment.concept.lower())

        # Return as list, preserving case for first occurrence
        return list(strengths)

    async def _calculate_recommendations(
        self,
        user_id: UUID,
        mastery_map: dict[str, Any],
        gaps: list[dict[str, Any]],
        current_chapter: Chapter,
    ) -> list[UUID]:
        """
        Calculate recommended chapters.

        Priority:
        1. Unmet prerequisites for current chapter
        2. Chapters addressing high-severity gaps
        3. Next logical chapters (by chapter number)
        4. Chapters addressing medium-severity gaps
        """
        recommendations = []
        seen = set()

        # 1. Check prerequisites
        if current_chapter.prerequisites:
            for prereq_id in current_chapter.prerequisites:
                prereq_str = str(prereq_id)
                if prereq_str not in mastery_map or mastery_map[prereq_str].get(
                    "score", 0
                ) < 0.5:
                    if prereq_id not in seen:
                        recommendations.append(prereq_id)
                        seen.add(prereq_id)

        # 2. Chapters addressing high-severity gaps
        for gap in gaps:
            if gap.get("severity") == "high":
                for chapter_id_str in gap.get("related_chapters", []):
                    try:
                        chapter_id = UUID(chapter_id_str)
                        if chapter_id not in seen:
                            recommendations.append(chapter_id)
                            seen.add(chapter_id)
                    except (ValueError, TypeError):
                        continue

        # 3. Next logical chapter
        try:
            # Get chapters from same book
            chapters = await self.chapter_repo.get_by_book(current_chapter.book_id)
            chapters_sorted = sorted(chapters, key=lambda c: c.chapter_number)

            current_idx = next(
                (
                    i
                    for i, c in enumerate(chapters_sorted)
                    if c.id == current_chapter.id
                ),
                -1,
            )

            # Suggest next chapter if not at end
            if current_idx >= 0 and current_idx < len(chapters_sorted) - 1:
                next_chapter = chapters_sorted[current_idx + 1]
                if next_chapter.id not in seen:
                    recommendations.append(next_chapter.id)
                    seen.add(next_chapter.id)
        except Exception as e:
            logger.warning(f"Error getting next chapter: {e}")

        # 4. Chapters addressing medium-severity gaps
        for gap in gaps:
            if gap.get("severity") == "medium":
                for chapter_id_str in gap.get("related_chapters", []):
                    try:
                        chapter_id = UUID(chapter_id_str)
                        if chapter_id not in seen:
                            recommendations.append(chapter_id)
                            seen.add(chapter_id)
                    except (ValueError, TypeError):
                        continue

        # Limit to top 5
        return recommendations[:5]

    def _get_recommendation_reason(
        self,
        chapter_id: str,
        mastery_map: dict[str, Any],
        gaps: list[dict[str, Any]],
        chapter: Chapter,
    ) -> str:
        """Get the reason a chapter is recommended."""
        # Check if it's a prerequisite need
        if chapter_id not in mastery_map:
            return "Prerequisite chapter not yet studied"

        mastery_data = mastery_map.get(chapter_id, {})
        if mastery_data.get("score", 0) < 0.5:
            return "Low mastery score - review recommended"

        # Check if it addresses a gap
        for gap in gaps:
            if chapter_id in gap.get("related_chapters", []):
                return f"Addresses knowledge gap: {gap.get('concept', 'unknown')}"

        return "Recommended for continued learning"
