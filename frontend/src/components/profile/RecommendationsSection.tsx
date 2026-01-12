"use client";

/**
 * Recommendations section showing personalized chapter recommendations
 * Explains why each chapter is recommended and provides action to start studying
 */

import { useRouter } from "next/navigation";
import type { ChapterWithBook, LearningProfile, IdentifiedGap } from "@/types";

interface RecommendationsSectionProps {
  chapters: ChapterWithBook[];
  profile: LearningProfile | null;
}

// Determine why a chapter is recommended
function getRecommendationReason(
  chapter: ChapterWithBook,
  profile: LearningProfile | null,
  allChapters: ChapterWithBook[]
): { reason: string; priority: "high" | "medium" | "normal" } {
  if (!profile) {
    return { reason: "Start your learning journey!", priority: "normal" };
  }

  const mastery = profile.mastery_map?.[chapter.id];
  const score = mastery?.score ?? 0;

  // Check if it addresses a gap
  const addressesGap = profile.identified_gaps?.some((gap: IdentifiedGap) =>
    gap.related_chapters?.includes(chapter.id)
  );
  if (addressesGap) {
    const gap = profile.identified_gaps?.find((g: IdentifiedGap) =>
      g.related_chapters?.includes(chapter.id)
    );
    return {
      reason: `Strengthen your understanding of "${gap?.concept}"`,
      priority: gap?.severity === "high" ? "high" : "medium",
    };
  }

  // Check if prerequisites are mastered
  if (chapter.prerequisites && chapter.prerequisites.length > 0) {
    const prereqsMastered = chapter.prerequisites.every((prereqId) => {
      const prereqMastery = profile.mastery_map?.[prereqId];
      return prereqMastery && prereqMastery.score >= 0.6;
    });

    if (prereqsMastered && score === 0) {
      return {
        reason: "You've mastered the prerequisites - ready to advance!",
        priority: "medium",
      };
    }
  }

  // Check if it's the next chapter in sequence
  const sameBookChapters = allChapters
    .filter((ch) => ch.book_id === chapter.book_id)
    .sort((a, b) => a.chapter_number - b.chapter_number);

  const prevChapter = sameBookChapters.find(
    (ch) => ch.chapter_number === chapter.chapter_number - 1
  );
  if (prevChapter) {
    const prevMastery = profile.mastery_map?.[prevChapter.id];
    if (prevMastery && prevMastery.score >= 0.6 && score === 0) {
      return {
        reason: `Continue from Chapter ${prevChapter.chapter_number}`,
        priority: "medium",
      };
    }
  }

  // Not started but foundational
  if (score === 0 && chapter.chapter_number === 1) {
    return {
      reason: "Start from the beginning of this book",
      priority: "normal",
    };
  }

  // Needs review
  if (score > 0 && score < 0.6) {
    return {
      reason: "Review to improve your understanding",
      priority: "medium",
    };
  }

  return { reason: "Expand your knowledge", priority: "normal" };
}

// Recommendation card component
function RecommendationCard({
  chapter,
  reason,
  priority,
  masteryScore,
}: {
  chapter: ChapterWithBook;
  reason: string;
  priority: "high" | "medium" | "normal";
  masteryScore: number;
}) {
  const router = useRouter();

  const priorityStyles = {
    high: "border-red-200 bg-gradient-to-br from-red-50 to-orange-50",
    medium: "border-indigo-200 bg-gradient-to-br from-indigo-50 to-purple-50",
    normal: "border-gray-200 bg-white",
  };

  const priorityBadge = {
    high: { text: "High Priority", className: "bg-red-100 text-red-700" },
    medium: { text: "Recommended", className: "bg-indigo-100 text-indigo-700" },
    normal: { text: "Suggested", className: "bg-gray-100 text-gray-700" },
  };

  const handleStartStudying = () => {
    router.push(`/chat?chapter=${chapter.id}`);
  };

  return (
    <div className={`rounded-xl border ${priorityStyles[priority]} p-5 hover:shadow-md transition-shadow`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm border border-gray-100">
            <span className="text-lg font-bold text-indigo-600">
              {chapter.chapter_number}
            </span>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{chapter.title}</h3>
            <p className="text-sm text-gray-500">{chapter.book?.title}</p>
          </div>
        </div>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${priorityBadge[priority].className}`}>
          {priorityBadge[priority].text}
        </span>
      </div>

      {/* Reason */}
      <div className="flex items-start gap-2 mb-4">
        <svg className="w-4 h-4 text-indigo-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
        <p className="text-sm text-gray-600">{reason}</p>
      </div>

      {/* Current progress if any */}
      {masteryScore > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-500">Current mastery</span>
            <span className="font-medium text-gray-700">{Math.round(masteryScore * 100)}%</span>
          </div>
          <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 transition-all"
              style={{ width: `${Math.round(masteryScore * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Key concepts preview */}
      {chapter.key_concepts && chapter.key_concepts.length > 0 && (
        <div className="mb-4">
          <div className="flex flex-wrap gap-1.5">
            {chapter.key_concepts.slice(0, 3).map((concept, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-white border border-gray-200 text-gray-600"
              >
                {concept}
              </span>
            ))}
            {chapter.key_concepts.length > 3 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs text-gray-400">
                +{chapter.key_concepts.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Action button */}
      <button
        onClick={handleStartStudying}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        {masteryScore > 0 ? "Continue Studying" : "Start Studying"}
      </button>
    </div>
  );
}

export default function RecommendationsSection({
  chapters,
  profile,
}: RecommendationsSectionProps) {
  // Get recommended chapters from profile, or generate if none
  const recommendedChapterIds = profile?.recommended_chapters || [];

  // Build recommendations list
  const recommendations = recommendedChapterIds
    .map((id) => chapters.find((ch) => ch.id === id))
    .filter((ch): ch is ChapterWithBook => ch !== undefined)
    .map((chapter) => {
      const { reason, priority } = getRecommendationReason(chapter, profile, chapters);
      const masteryScore = profile?.mastery_map?.[chapter.id]?.score ?? 0;
      return { chapter, reason, priority, masteryScore };
    })
    .slice(0, 4); // Limit to 4 recommendations

  // If no recommendations, suggest first chapters
  if (recommendations.length === 0) {
    const firstChapters = chapters
      .filter((ch) => ch.chapter_number === 1)
      .slice(0, 2)
      .map((chapter) => ({
        chapter,
        reason: "Start your learning journey here!",
        priority: "normal" as const,
        masteryScore: 0,
      }));

    if (firstChapters.length > 0) {
      recommendations.push(...firstChapters);
    }
  }

  if (recommendations.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Recommendations Yet</h3>
        <p className="text-gray-500">
          Complete a few study sessions to get personalized recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Recommended Next Steps</h2>
        <p className="text-sm text-gray-500 mt-1">
          Personalized suggestions based on your learning journey
        </p>
      </div>

      {/* Recommendations grid */}
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {recommendations.map(({ chapter, reason, priority, masteryScore }) => (
          <RecommendationCard
            key={chapter.id}
            chapter={chapter}
            reason={reason}
            priority={priority}
            masteryScore={masteryScore}
          />
        ))}
      </div>
    </div>
  );
}
