"use client";

/**
 * Chapter grid component for displaying chapters in a responsive grid layout
 * Groups chapters by book and sorts by chapter number
 */

import { useMemo } from "react";
import type { ChapterWithBook, LearningProfile } from "@/types";
import ChapterCard from "./ChapterCard";

interface ChapterGridProps {
  chapters: ChapterWithBook[];
  profile?: LearningProfile | null;
  onChapterClick?: (chapter: ChapterWithBook) => void;
  isLoading?: boolean;
}

// Skeleton component for loading state
function ChapterCardSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden animate-pulse">
      {/* Header skeleton */}
      <div className="px-4 py-3 bg-gradient-to-r from-gray-100 to-gray-50 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="h-3 bg-gray-200 rounded w-24" />
          <div className="w-2.5 h-2.5 rounded-full bg-gray-200" />
        </div>
      </div>

      {/* Content skeleton */}
      <div className="p-4">
        <div className="flex items-start space-x-3">
          <div className="w-12 h-12 bg-gray-200 rounded-xl" />
          <div className="flex-1">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-1/3" />
          </div>
        </div>
        <div className="mt-3 space-y-2">
          <div className="h-3 bg-gray-200 rounded w-full" />
          <div className="h-3 bg-gray-200 rounded w-2/3" />
        </div>
        <div className="mt-3 flex gap-1.5">
          <div className="h-5 bg-gray-200 rounded w-16" />
          <div className="h-5 bg-gray-200 rounded w-20" />
          <div className="h-5 bg-gray-200 rounded w-14" />
        </div>
      </div>

      {/* Footer skeleton */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <div className="h-3 bg-gray-200 rounded w-24" />
          <div className="h-3 bg-gray-200 rounded w-16" />
        </div>
      </div>
    </div>
  );
}

// Error state component
export function ChapterGridError({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-red-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        Failed to load chapters
      </h3>
      <p className="text-sm text-gray-500 text-center mb-4">
        Something went wrong while loading the chapters.
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <svg
            className="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Try Again
        </button>
      )}
    </div>
  );
}

// Empty state component
export function ChapterGridEmpty() {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        No chapters available
      </h3>
      <p className="text-sm text-gray-500 text-center">
        Chapters will appear here once they&apos;re added to the system.
      </p>
    </div>
  );
}

// Loading skeleton grid
export function ChapterGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <ChapterCardSkeleton key={i} />
      ))}
    </div>
  );
}

export default function ChapterGrid({
  chapters,
  profile,
  onChapterClick,
  isLoading = false,
}: ChapterGridProps) {
  // Group chapters by book and sort
  const groupedChapters = useMemo(() => {
    // Group by book
    const groups: Record<
      string,
      { bookTitle: string; bookAuthor: string; chapters: ChapterWithBook[] }
    > = {};

    chapters.forEach((chapter) => {
      const bookId = chapter.book_id;
      const bookTitle = chapter.book?.title || "Unknown Book";
      const bookAuthor = chapter.book?.author || "Unknown Author";

      if (!groups[bookId]) {
        groups[bookId] = {
          bookTitle,
          bookAuthor,
          chapters: [],
        };
      }

      groups[bookId].chapters.push(chapter);
    });

    // Sort chapters within each group by chapter number
    Object.values(groups).forEach((group) => {
      group.chapters.sort((a, b) => a.chapter_number - b.chapter_number);
    });

    // Sort groups by book title
    return Object.entries(groups).sort(([, a], [, b]) =>
      a.bookTitle.localeCompare(b.bookTitle)
    );
  }, [chapters]);

  // Get mastery score for a chapter
  const getMasteryScore = (chapterId: string): number | undefined => {
    if (!profile?.mastery_map) return undefined;
    const mastery = profile.mastery_map[chapterId];
    return mastery?.score;
  };

  // Check if chapter is recommended
  const isRecommended = (chapterId: string): boolean => {
    if (!profile?.recommended_chapters) return false;
    return profile.recommended_chapters.includes(chapterId);
  };

  // Check if chapter has identified gaps
  const hasGaps = (chapterId: string): boolean => {
    if (!profile?.identified_gaps) return false;
    return profile.identified_gaps.some((gap) =>
      gap.related_chapters?.includes(chapterId)
    );
  };

  if (isLoading) {
    return <ChapterGridSkeleton />;
  }

  if (chapters.length === 0) {
    return <ChapterGridEmpty />;
  }

  // Single book - no grouping needed
  if (groupedChapters.length === 1) {
    const [, { chapters: bookChapters }] = groupedChapters[0];

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {bookChapters.map((chapter) => (
          <ChapterCard
            key={chapter.id}
            chapter={chapter}
            masteryScore={getMasteryScore(chapter.id)}
            isRecommended={isRecommended(chapter.id)}
            hasGaps={hasGaps(chapter.id)}
            onClick={() => onChapterClick?.(chapter)}
          />
        ))}
      </div>
    );
  }

  // Multiple books - show grouped
  return (
    <div className="space-y-10">
      {groupedChapters.map(([bookId, { bookTitle, bookAuthor, chapters: bookChapters }]) => (
        <section key={bookId}>
          {/* Book header */}
          <div className="flex items-center mb-4 pb-2 border-b border-gray-200">
            <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center mr-3">
              <svg
                className="w-5 h-5 text-indigo-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {bookTitle}
              </h2>
              <p className="text-sm text-gray-500">{bookAuthor}</p>
            </div>
            <span className="ml-auto text-sm text-gray-400">
              {bookChapters.length} chapter{bookChapters.length !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Chapters grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {bookChapters.map((chapter) => (
              <ChapterCard
                key={chapter.id}
                chapter={chapter}
                masteryScore={getMasteryScore(chapter.id)}
                isRecommended={isRecommended(chapter.id)}
                hasGaps={hasGaps(chapter.id)}
                onClick={() => onChapterClick?.(chapter)}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
