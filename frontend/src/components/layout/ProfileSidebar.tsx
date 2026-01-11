"use client";

/**
 * Learning profile sidebar component
 */

import { useProfileStats, useTopGaps } from "@/hooks";

export default function ProfileSidebar() {
  const { stats, isLoading, error } = useProfileStats();
  const { gaps } = useTopGaps(3);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-3/4 mb-4" />
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-2/3" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Learning Profile
        </h3>
        <p className="text-sm text-gray-500">
          Start studying chapters to build your learning profile!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Your Progress
        </h3>

        <div className="space-y-4">
          {/* Chapters studied */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Chapters Studied</span>
            <span className="text-lg font-semibold text-gray-900">
              {stats.totalChaptersStudied}
            </span>
          </div>

          {/* Average mastery */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-600">Average Mastery</span>
              <span className="text-sm font-medium text-gray-900">
                {stats.averageMastery}%
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${stats.averageMastery}%` }}
              />
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="bg-green-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-green-600">
                {stats.strengthsCount}
              </div>
              <div className="text-xs text-green-700">Strengths</div>
            </div>
            <div className="bg-amber-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-amber-600">
                {stats.activeGaps}
              </div>
              <div className="text-xs text-amber-700">Areas to Review</div>
            </div>
          </div>

          {/* Study time */}
          {stats.totalStudyTime > 0 && (
            <div className="flex items-center justify-between pt-2 border-t border-gray-100">
              <span className="text-sm text-gray-600">Total Study Time</span>
              <span className="text-sm font-medium text-gray-900">
                {Math.floor(stats.totalStudyTime / 60)}h{" "}
                {stats.totalStudyTime % 60}m
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Gaps to review */}
      {gaps.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Concepts to Review
          </h3>
          <div className="space-y-3">
            {gaps.map((gap, index) => (
              <div
                key={index}
                className="flex items-start space-x-3 p-2 rounded-lg bg-gray-50"
              >
                <div
                  className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${
                    gap.severity === "high"
                      ? "bg-red-500"
                      : gap.severity === "medium"
                        ? "bg-amber-500"
                        : "bg-yellow-500"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {gap.concept}
                  </p>
                  <p className="text-xs text-gray-500">
                    Seen {gap.occurrence_count} time
                    {gap.occurrence_count > 1 ? "s" : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
