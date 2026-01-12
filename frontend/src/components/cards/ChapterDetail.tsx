"use client";

/**
 * Chapter detail modal/slide-over component
 * Shows full chapter information with key concepts, prerequisites, and past conversations
 */

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { ChapterWithBook, Conversation, LearningProfile } from "@/types";

type MasteryStatus = "mastered" | "proficient" | "learning" | "needs_review" | "not_started";

interface ChapterDetailProps {
  chapter: ChapterWithBook;
  isOpen: boolean;
  onClose: () => void;
  profile?: LearningProfile | null;
  pastConversations?: Conversation[];
  allChapters?: ChapterWithBook[];
  onPrerequisiteClick?: (chapterId: string) => void;
}

export default function ChapterDetail({
  chapter,
  isOpen,
  onClose,
  profile,
  pastConversations = [],
  allChapters = [],
  onPrerequisiteClick,
}: ChapterDetailProps) {
  const router = useRouter();

  // Close on escape key
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, handleEscape]);

  // Get mastery info
  const getMasteryStatus = (): MasteryStatus => {
    if (!profile?.mastery_map) return "not_started";
    const mastery = profile.mastery_map[chapter.id];
    if (!mastery?.score || mastery.score === 0) return "not_started";

    const hasGaps = profile.identified_gaps?.some((gap) =>
      gap.related_chapters?.includes(chapter.id)
    );

    if (hasGaps && mastery.score < 0.7) return "needs_review";
    if (mastery.score >= 0.8) return "mastered";
    if (mastery.score >= 0.6) return "proficient";
    if (mastery.score > 0) return "learning";
    return "not_started";
  };

  const getMasteryScore = (): number | undefined => {
    if (!profile?.mastery_map) return undefined;
    return profile.mastery_map[chapter.id]?.score;
  };

  const status = getMasteryStatus();
  const masteryScore = getMasteryScore();

  const statusConfig: Record<MasteryStatus, { color: string; bgColor: string; label: string }> = {
    mastered: { color: "text-green-700", bgColor: "bg-green-100", label: "Mastered" },
    proficient: { color: "text-blue-700", bgColor: "bg-blue-100", label: "Proficient" },
    learning: { color: "text-yellow-700", bgColor: "bg-yellow-100", label: "In Progress" },
    needs_review: { color: "text-orange-700", bgColor: "bg-orange-100", label: "Needs Review" },
    not_started: { color: "text-gray-600", bgColor: "bg-gray-100", label: "Not Started" },
  };

  const config = statusConfig[status];

  // Get prerequisite chapters
  const prerequisiteChapters = allChapters.filter((ch) =>
    chapter.prerequisites?.includes(ch.id)
  );

  // Check if chapter is recommended
  const isRecommended = profile?.recommended_chapters?.includes(chapter.id);

  // Handle start studying
  const handleStartStudying = () => {
    onClose();
    router.push(`/chat?chapter=${chapter.id}`);
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg">
        <div className="h-full bg-white shadow-xl flex flex-col animate-slide-in-right">
          {/* Header */}
          <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-indigo-100">
                {chapter.book?.title || "Unknown Book"}
              </span>
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/20 rounded-lg transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
                <span className="text-2xl font-bold">{chapter.chapter_number}</span>
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-xl font-bold leading-tight">{chapter.title}</h2>
                <p className="text-sm text-indigo-100 mt-1">
                  by {chapter.book?.author || "Unknown Author"}
                </p>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Status and recommendations */}
            <div className="flex flex-wrap gap-2">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.bgColor} ${config.color}`}>
                {config.label}
                {masteryScore !== undefined && masteryScore > 0 && (
                  <span className="ml-1">({Math.round(masteryScore * 100)}%)</span>
                )}
              </span>
              {isRecommended && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-emerald-100 text-emerald-700">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  Recommended
                </span>
              )}
            </div>

            {/* Summary */}
            {chapter.summary && (
              <section>
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-2">
                  Summary
                </h3>
                <p className="text-gray-600 leading-relaxed">{chapter.summary}</p>
              </section>
            )}

            {/* Key Concepts */}
            {chapter.key_concepts && chapter.key_concepts.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">
                  Key Concepts
                </h3>
                <div className="flex flex-wrap gap-2">
                  {chapter.key_concepts.map((concept, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm bg-indigo-50 text-indigo-700 border border-indigo-100"
                    >
                      {concept}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Prerequisites */}
            {prerequisiteChapters.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">
                  Prerequisites
                </h3>
                <div className="space-y-2">
                  {prerequisiteChapters.map((prereq) => {
                    const prereqMastery = profile?.mastery_map?.[prereq.id]?.score;
                    const isMastered = prereqMastery !== undefined && prereqMastery >= 0.8;

                    return (
                      <button
                        key={prereq.id}
                        onClick={() => onPrerequisiteClick?.(prereq.id)}
                        className="w-full flex items-center p-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-left"
                      >
                        <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
                          <span className="text-sm font-semibold text-gray-600">
                            {prereq.chapter_number}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {prereq.title}
                          </p>
                          <p className="text-xs text-gray-500">
                            {prereq.book?.title}
                          </p>
                        </div>
                        {isMastered ? (
                          <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z" clipRule="evenodd" />
                          </svg>
                        )}
                      </button>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Past Conversations */}
            {pastConversations.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">
                  Past Study Sessions
                </h3>
                <div className="space-y-2">
                  {pastConversations.slice(0, 5).map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => {
                        onClose();
                        router.push(`/chat/${conv.id}`);
                      }}
                      className="w-full flex items-center p-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-left"
                    >
                      <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          {formatDate(conv.started_at)}
                        </p>
                        <p className="text-xs text-gray-500 capitalize">
                          {conv.status === "completed" ? "Completed" : conv.status === "active" ? "In Progress" : "Abandoned"}
                        </p>
                      </div>
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Footer with action button */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={handleStartStudying}
              className="w-full flex items-center justify-center px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/25"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              {status === "not_started" ? "Start Studying" : "Continue Studying"}
            </button>
          </div>
        </div>
      </div>

      {/* Animation styles */}
      <style jsx>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slideInRight 0.3s ease-out;
        }
      `}</style>
    </>
  );
}
