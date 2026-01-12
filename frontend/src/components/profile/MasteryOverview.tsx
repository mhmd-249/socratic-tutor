"use client";

/**
 * Mastery overview component showing visual representation of mastery across chapters
 * Displays progress bars grouped by book with click-to-view details
 */

import { useMemo } from "react";
import type { ChapterWithBook, LearningProfile, MasteryEntry } from "@/types";

interface MasteryOverviewProps {
  chapters: ChapterWithBook[];
  profile: LearningProfile | null;
  onChapterClick?: (chapter: ChapterWithBook) => void;
}

// Get mastery status and color based on score
function getMasteryInfo(score: number | undefined): {
  label: string;
  color: string;
  bgColor: string;
  barColor: string;
} {
  if (score === undefined || score === 0) {
    return {
      label: "Not Started",
      color: "text-gray-500",
      bgColor: "bg-gray-100",
      barColor: "bg-gray-300",
    };
  }
  if (score >= 0.8) {
    return {
      label: "Mastered",
      color: "text-green-700",
      bgColor: "bg-green-50",
      barColor: "bg-green-500",
    };
  }
  if (score >= 0.6) {
    return {
      label: "Proficient",
      color: "text-blue-700",
      bgColor: "bg-blue-50",
      barColor: "bg-blue-500",
    };
  }
  if (score > 0) {
    return {
      label: "Learning",
      color: "text-yellow-700",
      bgColor: "bg-yellow-50",
      barColor: "bg-yellow-500",
    };
  }
  return {
    label: "Not Started",
    color: "text-gray-500",
    bgColor: "bg-gray-100",
    barColor: "bg-gray-300",
  };
}

// Format date for last studied
function formatLastStudied(dateString: string | undefined): string {
  if (!dateString) return "Never";
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Individual chapter mastery row
function ChapterMasteryRow({
  chapter,
  mastery,
  onClick,
}: {
  chapter: ChapterWithBook;
  mastery: MasteryEntry | undefined;
  onClick?: () => void;
}) {
  const score = mastery?.score ?? 0;
  const info = getMasteryInfo(score);

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors text-left group"
    >
      {/* Chapter number */}
      <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
        <span className="text-sm font-semibold text-indigo-600">
          {chapter.chapter_number}
        </span>
      </div>

      {/* Chapter info and progress */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-900 truncate pr-2">
            {chapter.title}
          </span>
          <span className={`text-xs font-medium ${info.color} flex-shrink-0`}>
            {score > 0 ? `${Math.round(score * 100)}%` : info.label}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${info.barColor} transition-all duration-500 ease-out`}
            style={{ width: `${Math.round(score * 100)}%` }}
          />
        </div>

        {/* Last studied */}
        {mastery && mastery.study_count > 0 && (
          <div className="mt-1 flex items-center justify-between text-xs text-gray-400">
            <span>{mastery.study_count} session{mastery.study_count !== 1 ? "s" : ""}</span>
            <span>Last: {formatLastStudied(mastery.last_studied)}</span>
          </div>
        )}
      </div>

      {/* Arrow */}
      <svg
        className="w-4 h-4 text-gray-400 group-hover:text-indigo-600 transition-colors flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}

export default function MasteryOverview({
  chapters,
  profile,
  onChapterClick,
}: MasteryOverviewProps) {
  // Group chapters by book
  const groupedChapters = useMemo(() => {
    const groups: Record<string, { book: ChapterWithBook["book"]; chapters: ChapterWithBook[] }> = {};

    chapters.forEach((chapter) => {
      const bookId = chapter.book_id;
      if (!groups[bookId]) {
        groups[bookId] = { book: chapter.book, chapters: [] };
      }
      groups[bookId].chapters.push(chapter);
    });

    // Sort chapters within each group
    Object.values(groups).forEach((group) => {
      group.chapters.sort((a, b) => a.chapter_number - b.chapter_number);
    });

    return Object.entries(groups).sort(([, a], [, b]) =>
      (a.book?.title || "").localeCompare(b.book?.title || "")
    );
  }, [chapters]);

  // Calculate overall stats
  const stats = useMemo(() => {
    const totalChapters = chapters.length;
    let masteredCount = 0;
    let inProgressCount = 0;
    let totalScore = 0;
    let studiedCount = 0;

    chapters.forEach((chapter) => {
      const mastery = profile?.mastery_map?.[chapter.id];
      if (mastery?.score) {
        totalScore += mastery.score;
        studiedCount++;
        if (mastery.score >= 0.8) masteredCount++;
        else if (mastery.score > 0) inProgressCount++;
      }
    });

    return {
      totalChapters,
      masteredCount,
      inProgressCount,
      notStartedCount: totalChapters - masteredCount - inProgressCount,
      averageScore: studiedCount > 0 ? totalScore / studiedCount : 0,
      overallProgress: totalChapters > 0 ? (masteredCount / totalChapters) * 100 : 0,
    };
  }, [chapters, profile]);

  if (chapters.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Chapters Available</h3>
        <p className="text-gray-500">Chapters will appear here once they&apos;re added.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header with overall stats */}
      <div className="px-6 py-5 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-purple-50">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Mastery Overview</h2>

        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{stats.masteredCount}</p>
            <p className="text-xs text-gray-500">Mastered</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-yellow-600">{stats.inProgressCount}</p>
            <p className="text-xs text-gray-500">In Progress</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-400">{stats.notStartedCount}</p>
            <p className="text-xs text-gray-500">Not Started</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-indigo-600">{Math.round(stats.overallProgress)}%</p>
            <p className="text-xs text-gray-500">Complete</p>
          </div>
        </div>

        {/* Overall progress bar */}
        <div className="mt-4">
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden flex">
            <div
              className="bg-green-500 transition-all duration-500"
              style={{ width: `${(stats.masteredCount / stats.totalChapters) * 100}%` }}
            />
            <div
              className="bg-yellow-500 transition-all duration-500"
              style={{ width: `${(stats.inProgressCount / stats.totalChapters) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Chapter list by book */}
      <div className="divide-y divide-gray-100">
        {groupedChapters.map(([bookId, { book, chapters: bookChapters }]) => (
          <div key={bookId} className="p-4">
            {/* Book header */}
            <div className="flex items-center gap-3 mb-3 px-3">
              <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{book?.title || "Unknown Book"}</h3>
                <p className="text-xs text-gray-500">{bookChapters.length} chapters</p>
              </div>
            </div>

            {/* Chapters */}
            <div className="space-y-1">
              {bookChapters.map((chapter) => (
                <ChapterMasteryRow
                  key={chapter.id}
                  chapter={chapter}
                  mastery={profile?.mastery_map?.[chapter.id]}
                  onClick={() => onChapterClick?.(chapter)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
