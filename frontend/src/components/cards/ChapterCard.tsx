"use client";

/**
 * Chapter card component for displaying chapter information
 * Shows mastery status and handles click to view details
 */

import type { ChapterWithBook } from "@/types";

type MasteryStatus = "mastered" | "proficient" | "learning" | "needs_review" | "not_started";

interface ChapterCardProps {
  chapter: ChapterWithBook;
  masteryScore?: number;
  isRecommended?: boolean;
  hasGaps?: boolean;
  onClick?: () => void;
}

export default function ChapterCard({
  chapter,
  masteryScore,
  isRecommended = false,
  hasGaps = false,
  onClick,
}: ChapterCardProps) {
  // Determine mastery status based on score and gaps
  const getMasteryStatus = (score?: number): MasteryStatus => {
    if (score === undefined || score === 0) return "not_started";
    if (hasGaps && score < 0.7) return "needs_review";
    if (score >= 0.8) return "mastered";
    if (score >= 0.6) return "proficient";
    if (score > 0) return "learning";
    return "not_started";
  };

  const status = getMasteryStatus(masteryScore);

  // Status configuration for colors and labels
  const statusConfig: Record<MasteryStatus, { color: string; bgColor: string; label: string; icon: string }> = {
    mastered: {
      color: "text-green-700",
      bgColor: "bg-green-500",
      label: "Mastered",
      icon: "M5 13l4 4L19 7",
    },
    proficient: {
      color: "text-blue-700",
      bgColor: "bg-blue-500",
      label: "Proficient",
      icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
    },
    learning: {
      color: "text-yellow-700",
      bgColor: "bg-yellow-500",
      label: "In Progress",
      icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
    },
    needs_review: {
      color: "text-orange-700",
      bgColor: "bg-orange-500",
      label: "Needs Review",
      icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
    },
    not_started: {
      color: "text-gray-500",
      bgColor: "bg-gray-300",
      label: "Not Started",
      icon: "M12 6v6m0 0v6m0-6h6m-6 0H6",
    },
  };

  const config = statusConfig[status];

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:border-indigo-300 hover:scale-[1.02] transition-all duration-200 overflow-hidden group cursor-pointer"
    >
      {/* Header with book info and status badge */}
      <div className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-indigo-600 uppercase tracking-wide truncate max-w-[60%]">
            {chapter.book?.title || "Unknown Book"}
          </span>
          <div className="flex items-center gap-2">
            {isRecommended && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800 animate-pulse">
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                Recommended
              </span>
            )}
            {/* Status indicator dot */}
            <div className={`w-2.5 h-2.5 rounded-full ${config.bgColor}`} title={config.label} />
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="p-4">
        {/* Chapter number and title */}
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
            <span className="text-xl font-bold text-indigo-600">
              {chapter.chapter_number}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
              {chapter.title}
            </h3>
            {/* Status label under title */}
            <div className={`flex items-center mt-1 ${config.color}`}>
              <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
              </svg>
              <span className="text-xs font-medium">{config.label}</span>
            </div>
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
          <div className="mt-3 flex flex-wrap gap-1.5">
            {chapter.key_concepts.slice(0, 3).map((concept, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-gray-100 text-gray-700 group-hover:bg-indigo-50 group-hover:text-indigo-700 transition-colors"
              >
                {concept}
              </span>
            ))}
            {chapter.key_concepts.length > 3 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-gray-100 text-gray-500">
                +{chapter.key_concepts.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Progress bar */}
        {masteryScore !== undefined && masteryScore > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-gray-500">Mastery</span>
              <span className="font-semibold text-gray-700">
                {Math.round(masteryScore * 100)}%
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${config.bgColor} transition-all duration-500 ease-out`}
                style={{ width: `${Math.round(masteryScore * 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 truncate max-w-[50%]">
            {chapter.book?.author || "Unknown Author"}
          </span>
          <span className="text-xs font-medium text-indigo-600 group-hover:text-indigo-700 flex items-center">
            View Details
            <svg className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </div>
  );
}
