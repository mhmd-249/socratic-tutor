"""Tests for learning profile service."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.conversation import Conversation, ConversationStatus
from app.models.conversation_summary import ConversationSummary
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.services.profile_service import (
    ProfileService,
    ConceptAssessment,
    ChapterMastery,
    IdentifiedGap,
    ChapterRecommendation,
    ProfileContext,
)


class TestConceptAssessment:
    """Tests for ConceptAssessment dataclass."""

    def test_create_understood_assessment(self):
        """Test creating an understood concept assessment."""
        assessment = ConceptAssessment(
            concept="neural networks",
            understood=True,
            confidence=0.9,
            evidence="Correctly explained backpropagation",
        )

        assert assessment.concept == "neural networks"
        assert assessment.understood is True
        assert assessment.confidence == 0.9
        assert "backpropagation" in assessment.evidence

    def test_create_struggled_assessment(self):
        """Test creating a struggled concept assessment."""
        assessment = ConceptAssessment(
            concept="gradient descent",
            understood=False,
            confidence=0.7,  # High severity
            evidence="Confused optimization with loss",
        )

        assert assessment.concept == "gradient descent"
        assert assessment.understood is False
        assert assessment.confidence == 0.7


class TestMasteryScoreUpdate:
    """Tests for mastery score calculation (exponential moving average)."""

    def test_first_study_establishes_baseline(self):
        """Test that first study session establishes baseline score."""
        service = MagicMock(spec=ProfileService)
        service._update_mastery_map = ProfileService._update_mastery_map
        service.DEFAULT_SCORE = 0.3
        service.RECENCY_WEIGHT = 0.7
        service.MIN_SCORE = 0.0
        service.MAX_SCORE = 1.0

        current_map = {}
        chapter_id = str(uuid4())
        assessments = [
            ConceptAssessment(concept="neural networks", understood=True, confidence=0.8),
        ]

        result = service._update_mastery_map(
            service, current_map, chapter_id, assessments, ["neural networks"]
        )

        assert chapter_id in result
        # New score should be weighted average of evidence (0.8) and default (0.3)
        # new_score = 0.7 * 0.8 + 0.3 * 0.3 = 0.56 + 0.09 = 0.65
        expected_score = 0.7 * 0.8 + 0.3 * 0.3
        assert abs(result[chapter_id]["score"] - expected_score) < 0.01
        assert result[chapter_id]["study_count"] == 1

    def test_repeat_study_uses_moving_average(self):
        """Test that repeated study uses exponential moving average."""
        service = MagicMock(spec=ProfileService)
        service._update_mastery_map = ProfileService._update_mastery_map
        service.DEFAULT_SCORE = 0.3
        service.RECENCY_WEIGHT = 0.7
        service.MIN_SCORE = 0.0
        service.MAX_SCORE = 1.0

        chapter_id = str(uuid4())
        current_map = {
            chapter_id: {
                "score": 0.5,  # Previous score
                "last_studied": "2024-01-01T00:00:00",
                "concepts_covered": ["basics"],
                "study_count": 1,
            }
        }

        # Student shows high understanding in second session
        assessments = [
            ConceptAssessment(concept="advanced topics", understood=True, confidence=0.9),
        ]

        result = service._update_mastery_map(
            service, current_map, chapter_id, assessments, ["advanced topics"]
        )

        # new_score = 0.7 * 0.9 + 0.3 * 0.5 = 0.63 + 0.15 = 0.78
        expected_score = 0.7 * 0.9 + 0.3 * 0.5
        assert abs(result[chapter_id]["score"] - expected_score) < 0.01
        assert result[chapter_id]["study_count"] == 2
        assert "advanced topics" in result[chapter_id]["concepts_covered"]

    def test_struggled_concepts_lower_score(self):
        """Test that struggling with concepts lowers the score."""
        service = MagicMock(spec=ProfileService)
        service._update_mastery_map = ProfileService._update_mastery_map
        service.DEFAULT_SCORE = 0.3
        service.RECENCY_WEIGHT = 0.7
        service.MIN_SCORE = 0.0
        service.MAX_SCORE = 1.0

        chapter_id = str(uuid4())
        current_map = {
            chapter_id: {
                "score": 0.8,  # High previous score
                "last_studied": "2024-01-01T00:00:00",
                "concepts_covered": ["basics"],
                "study_count": 3,
            }
        }

        # Student struggles in this session
        assessments = [
            ConceptAssessment(
                concept="hard topic", understood=False, confidence=0.8
            ),  # High severity struggle
        ]

        result = service._update_mastery_map(
            service, current_map, chapter_id, assessments, ["hard topic"]
        )

        # For struggled concepts: evidence_score = 1 - confidence = 0.2
        # new_score = 0.7 * 0.2 + 0.3 * 0.8 = 0.14 + 0.24 = 0.38
        expected_score = 0.7 * 0.2 + 0.3 * 0.8
        assert abs(result[chapter_id]["score"] - expected_score) < 0.01
        # Score should have dropped significantly
        assert result[chapter_id]["score"] < 0.5

    def test_mixed_results_balanced_score(self):
        """Test that mixed understood/struggled concepts balance out."""
        service = MagicMock(spec=ProfileService)
        service._update_mastery_map = ProfileService._update_mastery_map
        service.DEFAULT_SCORE = 0.3
        service.RECENCY_WEIGHT = 0.7
        service.MIN_SCORE = 0.0
        service.MAX_SCORE = 1.0

        chapter_id = str(uuid4())
        current_map = {}

        assessments = [
            ConceptAssessment(concept="concept1", understood=True, confidence=0.9),
            ConceptAssessment(concept="concept2", understood=False, confidence=0.5),
        ]

        result = service._update_mastery_map(
            service, current_map, chapter_id, assessments, []
        )

        # understood scores: [0.9]
        # struggled scores: [1 - 0.5] = [0.5]
        # average: (0.9 + 0.5) / 2 = 0.7
        # new_score = 0.7 * 0.7 + 0.3 * 0.3 = 0.49 + 0.09 = 0.58
        expected_score = 0.7 * 0.7 + 0.3 * 0.3
        assert abs(result[chapter_id]["score"] - expected_score) < 0.01

    def test_score_clamped_to_valid_range(self):
        """Test that score stays within 0.0-1.0."""
        service = MagicMock(spec=ProfileService)
        service._update_mastery_map = ProfileService._update_mastery_map
        service.DEFAULT_SCORE = 0.3
        service.RECENCY_WEIGHT = 0.7
        service.MIN_SCORE = 0.0
        service.MAX_SCORE = 1.0

        chapter_id = str(uuid4())
        current_map = {
            chapter_id: {
                "score": 0.95,
                "last_studied": "2024-01-01T00:00:00",
                "concepts_covered": [],
                "study_count": 5,
            }
        }

        # Perfect understanding
        assessments = [
            ConceptAssessment(concept="topic", understood=True, confidence=1.0),
        ]

        result = service._update_mastery_map(
            service, current_map, chapter_id, assessments, []
        )

        assert result[chapter_id]["score"] <= 1.0
        assert result[chapter_id]["score"] >= 0.0


class TestFuzzyConceptMatching:
    """Tests for fuzzy concept matching in gap identification."""

    def test_exact_match(self):
        """Test exact match works."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "gradient descent": {"concept": "gradient descent", "occurrence_count": 1}
        }

        result = service._find_matching_gap(service, "gradient descent", gaps_by_concept)
        assert result == "gradient descent"

    def test_case_insensitive_match(self):
        """Test case insensitive matching."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "gradient descent": {"concept": "Gradient Descent", "occurrence_count": 1}
        }

        result = service._find_matching_gap(service, "GRADIENT DESCENT", gaps_by_concept)
        assert result == "gradient descent"

    def test_containment_match_existing_contains_new(self):
        """Test matching when existing concept contains the new one."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "supervised vs unsupervised learning distinction": {
                "concept": "supervised vs unsupervised learning distinction",
                "occurrence_count": 1,
            }
        }

        # Shorter version should match longer
        result = service._find_matching_gap(
            service, "supervised vs unsupervised learning", gaps_by_concept
        )
        assert result == "supervised vs unsupervised learning distinction"

    def test_containment_match_new_contains_existing(self):
        """Test matching when new concept contains the existing one."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "supervised vs unsupervised learning": {
                "concept": "supervised vs unsupervised learning",
                "occurrence_count": 1,
            }
        }

        # Longer version should match shorter
        result = service._find_matching_gap(
            service, "supervised vs unsupervised learning distinction", gaps_by_concept
        )
        assert result == "supervised vs unsupervised learning"

    def test_word_overlap_three_words(self):
        """Test matching with 3+ shared words."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "understanding neural network architectures": {
                "concept": "understanding neural network architectures",
                "occurrence_count": 1,
            }
        }

        # Different phrasing with 3 shared words: neural, network, architectures
        result = service._find_matching_gap(
            service, "neural network architectures explained", gaps_by_concept
        )
        assert result == "understanding neural network architectures"

    def test_word_overlap_70_percent(self):
        """Test matching with 70%+ word overlap."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "learning rate tuning": {
                "concept": "learning rate tuning",
                "occurrence_count": 1,
            }
        }

        # 2 of 3 words match = 67%, but let's test 3 of 4 = 75%
        result = service._find_matching_gap(
            service, "learning rate tuning methods", gaps_by_concept
        )
        # 3 shared words out of 3 (smaller set) = 100%
        assert result == "learning rate tuning"

    def test_no_match_different_concepts(self):
        """Test that unrelated concepts don't match."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "gradient descent": {"concept": "gradient descent", "occurrence_count": 1}
        }

        # Completely different concept
        result = service._find_matching_gap(service, "activation functions", gaps_by_concept)
        assert result is None

    def test_no_match_insufficient_overlap(self):
        """Test that concepts with low overlap don't match."""
        service = MagicMock(spec=ProfileService)
        service._find_matching_gap = ProfileService._find_matching_gap

        gaps_by_concept = {
            "understanding deep learning fundamentals": {
                "concept": "understanding deep learning fundamentals",
                "occurrence_count": 1,
            }
        }

        # Only 1 word in common ("learning"), not enough
        result = service._find_matching_gap(
            service, "reinforcement learning basics", gaps_by_concept
        )
        assert result is None

    def test_fuzzy_match_updates_existing_gap(self):
        """Test that fuzzy matching correctly updates existing gaps."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        chapter_id = str(uuid4())

        # Existing gap with one phrasing
        current_gaps = [
            {
                "concept": "supervised vs unsupervised learning",
                "severity": "low",
                "occurrence_count": 1,
                "related_chapters": [str(uuid4())],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-01T00:00:00",
            }
        ]

        # Struggle with similar phrasing
        assessments = [
            ConceptAssessment(
                concept="supervised vs unsupervised learning distinction",
                understood=False,
                confidence=0.5,
            ),
        ]

        result = service._update_gaps(service, current_gaps, assessments, chapter_id)

        # Should merge into existing gap, not create new one
        assert len(result) == 1
        assert result[0]["occurrence_count"] == 2  # Incremented
        assert result[0]["severity"] == "medium"  # Escalated


class TestGapIdentification:
    """Tests for gap identification logic."""

    def test_first_struggle_creates_low_severity_gap(self):
        """Test that first struggle creates a low severity gap."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        current_gaps = []
        chapter_id = str(uuid4())
        assessments = [
            ConceptAssessment(concept="gradient descent", understood=False, confidence=0.5),
        ]

        result = service._update_gaps(service, current_gaps, assessments, chapter_id)

        assert len(result) == 1
        assert result[0]["concept"] == "gradient descent"
        assert result[0]["severity"] == "low"
        assert result[0]["occurrence_count"] == 1
        assert chapter_id in result[0]["related_chapters"]

    def test_repeated_struggle_increases_severity(self):
        """Test that repeated struggles increase gap severity."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        chapter_id_1 = str(uuid4())
        chapter_id_2 = str(uuid4())

        # Start with existing low severity gap
        current_gaps = [
            {
                "concept": "gradient descent",
                "severity": "low",
                "occurrence_count": 1,
                "related_chapters": [chapter_id_1],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-01T00:00:00",
            }
        ]

        # Second struggle with same concept
        assessments = [
            ConceptAssessment(concept="gradient descent", understood=False, confidence=0.6),
        ]

        result = service._update_gaps(service, current_gaps, assessments, chapter_id_2)

        assert len(result) == 1
        assert result[0]["severity"] == "medium"  # Increased from low
        assert result[0]["occurrence_count"] == 2
        assert chapter_id_2 in result[0]["related_chapters"]

    def test_third_struggle_becomes_high_severity(self):
        """Test that third struggle creates high severity gap."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        chapter_id = str(uuid4())

        # Start with medium severity gap
        current_gaps = [
            {
                "concept": "calculus",
                "severity": "medium",
                "occurrence_count": 2,
                "related_chapters": [str(uuid4())],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-02T00:00:00",
            }
        ]

        # Third struggle
        assessments = [
            ConceptAssessment(concept="calculus", understood=False, confidence=0.7),
        ]

        result = service._update_gaps(service, current_gaps, assessments, chapter_id)

        assert len(result) == 1
        assert result[0]["severity"] == "high"
        assert result[0]["occurrence_count"] == 3

    def test_understanding_reduces_gap(self):
        """Test that understanding a concept reduces gap severity."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        chapter_id = str(uuid4())

        current_gaps = [
            {
                "concept": "linear algebra",
                "severity": "medium",
                "occurrence_count": 2,
                "related_chapters": [str(uuid4())],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-02T00:00:00",
            }
        ]

        # Student now understands the concept
        assessments = [
            ConceptAssessment(concept="linear algebra", understood=True, confidence=0.8),
        ]

        result = service._update_gaps(service, current_gaps, assessments, chapter_id)

        assert len(result) == 1
        assert result[0]["occurrence_count"] == 1  # Reduced from 2
        assert result[0]["severity"] == "low"  # Back to low

    def test_full_understanding_removes_gap(self):
        """Test that understanding removes gap when occurrence reaches 0."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        chapter_id = str(uuid4())

        current_gaps = [
            {
                "concept": "linear algebra",
                "severity": "low",
                "occurrence_count": 1,
                "related_chapters": [str(uuid4())],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-01T00:00:00",
            }
        ]

        # Student understands it
        assessments = [
            ConceptAssessment(concept="linear algebra", understood=True, confidence=0.9),
        ]

        result = service._update_gaps(service, current_gaps, assessments, chapter_id)

        # Gap should be removed
        assert len(result) == 0

    def test_gaps_sorted_by_severity(self):
        """Test that gaps are sorted by severity (high first)."""
        service = MagicMock(spec=ProfileService)
        service._update_gaps = ProfileService._update_gaps
        service._find_matching_gap = ProfileService._find_matching_gap
        service._calculate_severity = ProfileService._calculate_severity
        service.HIGH_SEVERITY_THRESHOLD = 3
        service.MEDIUM_SEVERITY_THRESHOLD = 2

        chapter_id = str(uuid4())

        current_gaps = [
            {
                "concept": "low priority",
                "severity": "low",
                "occurrence_count": 1,
                "related_chapters": [],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-01T00:00:00",
            },
            {
                "concept": "high priority",
                "severity": "high",
                "occurrence_count": 3,
                "related_chapters": [],
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-01-03T00:00:00",
            },
        ]

        # No new assessments, just test sorting
        result = service._update_gaps(service, current_gaps, [], chapter_id)

        assert result[0]["concept"] == "high priority"
        assert result[1]["concept"] == "low priority"


class TestChapterRecommendations:
    """Tests for chapter recommendation logic."""

    @pytest.fixture
    def mock_service(self):
        """Create a mocked ProfileService."""
        service = MagicMock(spec=ProfileService)
        service._calculate_recommendations = ProfileService._calculate_recommendations
        service.chapter_repo = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_recommends_unmet_prerequisites_first(self, mock_service):
        """Test that unmet prerequisites are recommended first."""
        user_id = uuid4()
        prereq_id = uuid4()
        current_chapter_id = uuid4()

        # Current chapter has prerequisites
        current_chapter = MagicMock(spec=Chapter)
        current_chapter.id = current_chapter_id
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = [prereq_id]

        # No mastery for prerequisite
        mastery_map = {}
        gaps = []

        # Mock chapter repo to avoid DB calls
        mock_service.chapter_repo.get_by_book = AsyncMock(return_value=[])

        result = await mock_service._calculate_recommendations(
            mock_service, user_id, mastery_map, gaps, current_chapter
        )

        assert prereq_id in result
        assert result[0] == prereq_id  # First recommendation

    @pytest.mark.asyncio
    async def test_recommends_chapters_for_high_severity_gaps(self, mock_service):
        """Test that chapters addressing high severity gaps are recommended."""
        user_id = uuid4()
        gap_chapter_id = uuid4()
        current_chapter_id = uuid4()

        current_chapter = MagicMock(spec=Chapter)
        current_chapter.id = current_chapter_id
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = []

        mastery_map = {}
        gaps = [
            {
                "concept": "important topic",
                "severity": "high",
                "related_chapters": [str(gap_chapter_id)],
                "occurrence_count": 3,
            }
        ]

        mock_service.chapter_repo.get_by_book = AsyncMock(return_value=[])

        result = await mock_service._calculate_recommendations(
            mock_service, user_id, mastery_map, gaps, current_chapter
        )

        assert gap_chapter_id in result

    @pytest.mark.asyncio
    async def test_recommends_next_chapter_in_sequence(self, mock_service):
        """Test that next chapter in sequence is recommended."""
        user_id = uuid4()
        current_chapter_id = uuid4()
        next_chapter_id = uuid4()
        book_id = uuid4()

        current_chapter = MagicMock(spec=Chapter)
        current_chapter.id = current_chapter_id
        current_chapter.book_id = book_id
        current_chapter.chapter_number = 3
        current_chapter.prerequisites = []

        next_chapter = MagicMock(spec=Chapter)
        next_chapter.id = next_chapter_id
        next_chapter.chapter_number = 4

        mastery_map = {}
        gaps = []

        # Mock getting chapters from book
        mock_service.chapter_repo.get_by_book = AsyncMock(
            return_value=[current_chapter, next_chapter]
        )

        result = await mock_service._calculate_recommendations(
            mock_service, user_id, mastery_map, gaps, current_chapter
        )

        assert next_chapter_id in result

    @pytest.mark.asyncio
    async def test_recommendations_limited_to_5(self, mock_service):
        """Test that recommendations are limited to 5 chapters."""
        user_id = uuid4()
        current_chapter_id = uuid4()

        current_chapter = MagicMock(spec=Chapter)
        current_chapter.id = current_chapter_id
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = [uuid4() for _ in range(10)]  # 10 prerequisites

        mastery_map = {}
        gaps = []

        mock_service.chapter_repo.get_by_book = AsyncMock(return_value=[])

        result = await mock_service._calculate_recommendations(
            mock_service, user_id, mastery_map, gaps, current_chapter
        )

        assert len(result) <= 5


class TestStrengthsUpdate:
    """Tests for strengths identification."""

    def test_high_confidence_adds_strength(self):
        """Test that high-confidence understood concepts become strengths."""
        service = MagicMock(spec=ProfileService)
        service._update_strengths = ProfileService._update_strengths

        current_strengths = ["basics"]
        assessments = [
            ConceptAssessment(concept="Neural Networks", understood=True, confidence=0.9),
            ConceptAssessment(concept="Deep Learning", understood=True, confidence=0.85),
        ]

        result = service._update_strengths(service, current_strengths, assessments)

        assert "neural networks" in result
        assert "deep learning" in result
        assert "basics" in result

    def test_low_confidence_not_added_as_strength(self):
        """Test that low-confidence concepts are not added as strengths."""
        service = MagicMock(spec=ProfileService)
        service._update_strengths = ProfileService._update_strengths

        current_strengths = []
        assessments = [
            ConceptAssessment(concept="topic1", understood=True, confidence=0.6),  # Low
            ConceptAssessment(concept="topic2", understood=True, confidence=0.9),  # High
        ]

        result = service._update_strengths(service, current_strengths, assessments)

        assert "topic2" in result
        assert "topic1" not in result

    def test_struggled_concepts_not_strengths(self):
        """Test that struggled concepts are never added as strengths."""
        service = MagicMock(spec=ProfileService)
        service._update_strengths = ProfileService._update_strengths

        current_strengths = []
        assessments = [
            ConceptAssessment(concept="hard topic", understood=False, confidence=0.9),
        ]

        result = service._update_strengths(service, current_strengths, assessments)

        assert len(result) == 0


class TestBuildAssessmentsFromSummary:
    """Tests for building assessments from conversation summaries."""

    def test_handles_string_concepts(self):
        """Test parsing string-format concepts."""
        service = MagicMock(spec=ProfileService)
        service._build_assessments_from_summary = ProfileService._build_assessments_from_summary

        summary = MagicMock(spec=ConversationSummary)
        summary.concepts_understood = ["concept1", "concept2"]
        summary.concepts_struggled = ["hard concept"]

        result = service._build_assessments_from_summary(service, summary)

        understood = [a for a in result if a.understood]
        struggled = [a for a in result if not a.understood]

        assert len(understood) == 2
        assert len(struggled) == 1
        assert understood[0].confidence == 0.8  # Default confidence
        assert struggled[0].concept == "hard concept"

    def test_handles_dict_concepts(self):
        """Test parsing dictionary-format concepts."""
        service = MagicMock(spec=ProfileService)
        service._build_assessments_from_summary = ProfileService._build_assessments_from_summary

        summary = MagicMock(spec=ConversationSummary)
        summary.concepts_understood = [
            {"concept": "neural nets", "confidence": 0.95, "evidence": "explained well"}
        ]
        summary.concepts_struggled = [
            {"concept": "backprop", "severity": "high", "evidence": "confused"}
        ]

        result = service._build_assessments_from_summary(service, summary)

        understood = [a for a in result if a.understood]
        struggled = [a for a in result if not a.understood]

        assert len(understood) == 1
        assert understood[0].confidence == 0.95
        assert understood[0].evidence == "explained well"

        assert len(struggled) == 1
        assert struggled[0].confidence == 0.8  # High severity = 0.8

    def test_handles_empty_concepts(self):
        """Test handling empty concept lists."""
        service = MagicMock(spec=ProfileService)
        service._build_assessments_from_summary = ProfileService._build_assessments_from_summary

        summary = MagicMock(spec=ConversationSummary)
        summary.concepts_understood = []
        summary.concepts_struggled = None  # Could be None

        result = service._build_assessments_from_summary(service, summary)

        assert result == []


class TestProfileContextBuilding:
    """Tests for building profile context for conversations."""

    @pytest.fixture
    def mock_profile_service(self):
        """Create mock profile service with async session."""
        session = AsyncMock()
        service = ProfileService(session)
        service.profile_repo = AsyncMock()
        service.chapter_repo = AsyncMock()
        service.summary_repo = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_context_includes_relevant_gaps(self, mock_profile_service):
        """Test that context includes gaps relevant to chapter concepts."""
        user_id = uuid4()
        chapter_id = uuid4()

        # Mock profile with gaps
        profile = MagicMock(spec=LearningProfile)
        profile.mastery_map = {}
        profile.identified_gaps = [
            {
                "concept": "backpropagation",
                "severity": "high",
                "occurrence_count": 3,
                "related_chapters": [],
                "first_seen": "2024-01-01",
                "last_seen": "2024-01-03",
            }
        ]
        profile.strengths = ["linear algebra"]

        # Mock chapter with related concepts
        chapter = MagicMock(spec=Chapter)
        chapter.key_concepts = ["neural networks", "backpropagation", "gradient descent"]
        chapter.prerequisites = []

        mock_profile_service.profile_repo.get_by_user = AsyncMock(return_value=profile)
        mock_profile_service.chapter_repo.get = AsyncMock(return_value=chapter)
        mock_profile_service.summary_repo.get_by_user = AsyncMock(return_value=[])

        result = await mock_profile_service.get_context_for_conversation(user_id, chapter_id)

        # Should include the gap that relates to chapter concepts
        assert len(result.relevant_gaps) == 1
        assert result.relevant_gaps[0].concept == "backpropagation"
        assert result.strengths == ["linear algebra"]

    @pytest.mark.asyncio
    async def test_context_includes_chapter_mastery(self, mock_profile_service):
        """Test that context includes mastery info for the chapter."""
        user_id = uuid4()
        chapter_id = uuid4()

        profile = MagicMock(spec=LearningProfile)
        profile.mastery_map = {
            str(chapter_id): {
                "score": 0.75,
                "last_studied": "2024-01-15T10:00:00",
                "concepts_covered": ["topic1", "topic2"],
                "study_count": 3,
            }
        }
        profile.identified_gaps = []
        profile.strengths = []

        chapter = MagicMock(spec=Chapter)
        chapter.key_concepts = []
        chapter.prerequisites = []

        mock_profile_service.profile_repo.get_by_user = AsyncMock(return_value=profile)
        mock_profile_service.chapter_repo.get = AsyncMock(return_value=chapter)
        mock_profile_service.summary_repo.get_by_user = AsyncMock(return_value=[])

        result = await mock_profile_service.get_context_for_conversation(user_id, chapter_id)

        assert result.chapter_mastery is not None
        assert result.chapter_mastery.score == 0.75
        assert result.chapter_mastery.study_count == 3


# Integration tests (require mocked database)
@pytest.fixture
async def sample_user(db_session):
    """Create a sample user."""
    user = User(
        id=uuid4(),
        supabase_id="test-supabase-id",
        email="test@example.com",
        name="Test User",
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_book(db_session):
    """Create a sample book."""
    book = Book(
        id=uuid4(),
        title="Test Book on Machine Learning",
        author="Test Author",
        description="A test book",
        created_at=datetime.utcnow(),
    )
    db_session.add(book)
    await db_session.commit()
    return book


@pytest.fixture
async def sample_chapter(db_session, sample_book):
    """Create a sample chapter."""
    chapter = Chapter(
        id=uuid4(),
        book_id=sample_book.id,
        title="Introduction to Neural Networks",
        chapter_number=1,
        summary="This chapter introduces neural networks",
        key_concepts=["neural networks", "backpropagation", "activation functions"],
        prerequisites=[],
        created_at=datetime.utcnow(),
    )
    db_session.add(chapter)
    await db_session.commit()
    return chapter


@pytest.mark.asyncio
async def test_get_or_create_profile_creates_new(db_session, sample_user):
    """Test that get_or_create_profile creates a new profile."""
    pytest.skip("Requires database session - run with pytest fixtures")

    service = ProfileService(db_session)
    profile = await service.get_or_create_profile(sample_user.id)

    assert profile is not None
    assert profile.user_id == sample_user.id
    assert profile.mastery_map == {}
    assert profile.identified_gaps == []


@pytest.mark.asyncio
async def test_update_from_summary_integration(
    db_session, sample_user, sample_chapter
):
    """Test full update_from_summary flow."""
    pytest.skip("Requires database session - run with pytest fixtures")

    service = ProfileService(db_session)

    # Create mock summary
    summary = MagicMock(spec=ConversationSummary)
    summary.concepts_understood = [
        {"concept": "neural networks", "confidence": 0.9, "evidence": "explained well"}
    ]
    summary.concepts_struggled = [
        {"concept": "backpropagation", "severity": "medium", "evidence": "confused"}
    ]
    summary.questions_asked = 5

    profile = await service.update_from_summary(
        user_id=sample_user.id,
        summary=summary,
        chapter=sample_chapter,
    )

    assert profile is not None
    assert str(sample_chapter.id) in profile.mastery_map
    assert len(profile.identified_gaps) > 0
    assert "neural networks" in [s.lower() for s in profile.strengths]
