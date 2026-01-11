"use client";

/**
 * Profile page showing detailed learning profile information
 */

import { useAuth } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { useProfileStats, useLearningProfile, useTopGaps } from "@/hooks";

function ProfileContent() {
  const { user } = useAuth();
  const { stats, isLoading } = useProfileStats();
  const { data: profile } = useLearningProfile();
  const { gaps } = useTopGaps(10);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="bg-white rounded-xl p-6 space-y-4">
            <div className="h-6 bg-gray-200 rounded w-1/4" />
            <div className="h-4 bg-gray-200 rounded w-full" />
            <div className="h-4 bg-gray-200 rounded w-2/3" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Learning Profile</h1>
        <p className="mt-2 text-gray-600">
          Track your progress and identify areas for improvement.
        </p>
      </div>

      {/* User info */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center">
            <span className="text-2xl font-bold text-indigo-600">
              {user?.name?.charAt(0).toUpperCase() || "U"}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{user?.name}</h2>
            <p className="text-gray-500">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="text-3xl font-bold text-indigo-600">
              {stats.totalChaptersStudied}
            </div>
            <div className="text-sm text-gray-500">Chapters Studied</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="text-3xl font-bold text-green-600">
              {stats.averageMastery}%
            </div>
            <div className="text-sm text-gray-500">Avg. Mastery</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="text-3xl font-bold text-emerald-600">
              {stats.strengthsCount}
            </div>
            <div className="text-sm text-gray-500">Strengths</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="text-3xl font-bold text-amber-600">
              {stats.gapsCount}
            </div>
            <div className="text-sm text-gray-500">Areas to Review</div>
          </div>
        </div>
      )}

      {/* Strengths */}
      {profile?.strengths && profile.strengths.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Your Strengths
          </h3>
          <div className="flex flex-wrap gap-2">
            {profile.strengths.map((strength, index) => (
              <span
                key={index}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800"
              >
                {strength}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Gaps to review */}
      {gaps.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Concepts to Review
          </h3>
          <div className="space-y-3">
            {gaps.map((gap, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      gap.severity === "high"
                        ? "bg-red-500"
                        : gap.severity === "medium"
                          ? "bg-amber-500"
                          : "bg-yellow-500"
                    }`}
                  />
                  <span className="font-medium text-gray-900">{gap.concept}</span>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  <span>Seen {gap.occurrence_count}x</span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      gap.severity === "high"
                        ? "bg-red-100 text-red-800"
                        : gap.severity === "medium"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {gap.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mastery Map */}
      {profile?.mastery_map && Object.keys(profile.mastery_map).length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Chapter Mastery
          </h3>
          <div className="space-y-3">
            {Object.entries(profile.mastery_map)
              .sort(([, a], [, b]) => b.score - a.score)
              .map(([chapterId, entry]) => (
                <div key={chapterId} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 truncate max-w-xs">
                      Chapter {chapterId.slice(0, 8)}...
                    </span>
                    <span className="font-medium text-gray-900">
                      {Math.round(entry.score * 100)}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        entry.score >= 0.8
                          ? "bg-green-500"
                          : entry.score >= 0.6
                            ? "bg-yellow-500"
                            : entry.score >= 0.4
                              ? "bg-orange-500"
                              : "bg-red-500"
                      }`}
                      style={{ width: `${Math.round(entry.score * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {(!stats || stats.totalChaptersStudied === 0) && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-indigo-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No learning data yet
          </h3>
          <p className="text-gray-500 mb-4">
            Start studying chapters to build your learning profile!
          </p>
          <a
            href="/dashboard"
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Browse Chapters
          </a>
        </div>
      )}
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}
