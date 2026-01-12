"use client";

/**
 * Gaps section component showing identified knowledge gaps
 * Displays concept name, severity, related chapters, and study action
 */

import { useRouter } from "next/navigation";
import type { IdentifiedGap, ChapterWithBook } from "@/types";

interface GapsSectionProps {
  gaps: IdentifiedGap[];
  chapters: ChapterWithBook[];
}

// Severity configuration
const severityConfig = {
  high: {
    label: "High Priority",
    color: "text-red-700",
    bgColor: "bg-red-100",
    borderColor: "border-red-200",
    icon: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
  },
  medium: {
    label: "Medium Priority",
    color: "text-orange-700",
    bgColor: "bg-orange-100",
    borderColor: "border-orange-200",
    icon: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
  },
  low: {
    label: "Low Priority",
    color: "text-yellow-700",
    bgColor: "bg-yellow-100",
    borderColor: "border-yellow-200",
    icon: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    ),
  },
};

// Individual gap card
function GapCard({ gap, chapters }: { gap: IdentifiedGap; chapters: ChapterWithBook[] }) {
  const router = useRouter();
  const config = severityConfig[gap.severity];

  // Find related chapters
  const relatedChapters = chapters.filter((ch) => gap.related_chapters?.includes(ch.id));

  // Format last seen date
  const formatLastSeen = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const handleStudyNow = (chapterId: string) => {
    router.push(`/chat?chapter=${chapterId}`);
  };

  return (
    <div className={`bg-white rounded-xl border ${config.borderColor} p-4 hover:shadow-md transition-shadow`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`${config.bgColor} ${config.color} p-1.5 rounded-lg`}>
            {config.icon}
          </span>
          <div>
            <h3 className="font-semibold text-gray-900">{gap.concept}</h3>
            <p className={`text-xs ${config.color} font-medium`}>{config.label}</p>
          </div>
        </div>
        {gap.occurrence_count > 1 && (
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            Seen {gap.occurrence_count}x
          </span>
        )}
      </div>

      {/* Last seen */}
      <p className="text-xs text-gray-500 mb-3">
        Last encountered: {formatLastSeen(gap.last_seen)}
      </p>

      {/* Related chapters */}
      {relatedChapters.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">
            Study to improve:
          </p>
          <div className="space-y-2">
            {relatedChapters.slice(0, 2).map((chapter) => (
              <div
                key={chapter.id}
                className="flex items-center justify-between bg-gray-50 rounded-lg p-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs font-semibold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">
                    Ch {chapter.chapter_number}
                  </span>
                  <span className="text-sm text-gray-700 truncate">{chapter.title}</span>
                </div>
                <button
                  onClick={() => handleStudyNow(chapter.id)}
                  className="flex-shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 px-2 py-1 rounded transition-colors"
                >
                  Study
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function GapsSection({ gaps, chapters }: GapsSectionProps) {
  // Sort gaps by severity (high first) and then by occurrence count
  const sortedGaps = [...gaps].sort((a, b) => {
    const severityOrder = { high: 0, medium: 1, low: 2 };
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
    if (severityDiff !== 0) return severityDiff;
    return b.occurrence_count - a.occurrence_count;
  });

  // Count by severity
  const highCount = gaps.filter((g) => g.severity === "high").length;
  const mediumCount = gaps.filter((g) => g.severity === "medium").length;
  const lowCount = gaps.filter((g) => g.severity === "low").length;

  if (gaps.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Knowledge Gaps!</h3>
        <p className="text-gray-500">
          Great job! Keep studying to maintain your mastery.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Knowledge Gaps</h2>
            <p className="text-sm text-gray-500 mt-1">
              Areas that need more attention based on your study sessions
            </p>
          </div>

          {/* Summary badges */}
          <div className="flex items-center gap-2">
            {highCount > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                {highCount} High
              </span>
            )}
            {mediumCount > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700">
                {mediumCount} Medium
              </span>
            )}
            {lowCount > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
                {lowCount} Low
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Gaps list */}
      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {sortedGaps.map((gap, index) => (
          <GapCard key={`${gap.concept}-${index}`} gap={gap} chapters={chapters} />
        ))}
      </div>
    </div>
  );
}
