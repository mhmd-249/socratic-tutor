"use client";

/**
 * Chapter card component for displaying chapter information
 */

import Link from "next/link";
import type { ChapterWithBook } from "@/types";

interface ChapterCardProps {
  chapter: ChapterWithBook;
  masteryScore?: number;
  isRecommended?: boolean;
}

export default function ChapterCard({
  chapter,
  masteryScore,
  isRecommended = false,
}: ChapterCardProps) {
  // Determine mastery level for visual indicator
  const getMasteryColor = (score: number) => {
    if (score >= 0.8) return "bg-green-500";
    if (score >= 0.6) return "bg-yellow-500";
    if (score >= 0.4) return "bg-orange-500";
    if (score > 0) return "bg-red-500";
    return "bg-gray-300";
  };

  const getMasteryLabel = (score: number) => {
    if (score >= 0.8) return "Mastered";
    if (score >= 0.6) return "Proficient";
    if (score >= 0.4) return "Learning";
    if (score > 0) return "Needs Review";
    return "Not Started";
  };

  return (
    <Link href={`/chat/${chapter.id}`}>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-indigo-200 transition-all duration-200 overflow-hidden group">
        {/* Header with book info */}
        <div className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-indigo-600 uppercase tracking-wide">
              {chapter.book?.title || "Unknown Book"}
            </span>
            {isRecommended && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                Recommended
              </span>
            )}
          </div>
        </div>

        {/* Main content */}
        <div className="p-4">
          {/* Chapter number and title */}
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
              <span className="text-lg font-bold text-indigo-600">
                {chapter.chapter_number}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
                {chapter.title}
              </h3>
            </div>
          </div>

          {/* Summary */}
          {chapter.summary && (
            <p className="mt-3 text-sm text-gray-600 line-clamp-2">
              {chapter.summary}
            </p>
          )}

          {/* Key concepts */}
          {chapter.key_concepts && chapter.key_concepts.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {chapter.key_concepts.slice(0, 3).map((concept, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                >
                  {concept}
                </span>
              ))}
              {chapter.key_concepts.length > 3 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">
                  +{chapter.key_concepts.length - 3} more
                </span>
              )}
            </div>
          )}

          {/* Mastery indicator */}
          {masteryScore !== undefined && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Progress</span>
                <span className="font-medium text-gray-700">
                  {getMasteryLabel(masteryScore)}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getMasteryColor(masteryScore)} transition-all duration-300`}
                  style={{ width: `${Math.round(masteryScore * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {chapter.book?.author || "Unknown Author"}
            </span>
            <span className="text-xs font-medium text-indigo-600 group-hover:text-indigo-700">
              Start Learning &rarr;
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
