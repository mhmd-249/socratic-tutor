"use client";

/**
 * Dashboard page with chapter cards and learning profile sidebar
 */

import { useAuth } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import ChapterCard from "@/components/cards/ChapterCard";
import ProfileSidebar from "@/components/layout/ProfileSidebar";
import { useChaptersGroupedByBook, useLearningProfile } from "@/hooks";

function DashboardContent() {
  const { user } = useAuth();
  const { groupedChapters, isLoading, error } = useChaptersGroupedByBook();
  const { data: profile } = useLearningProfile();

  // Get mastery score for a chapter
  const getMasteryScore = (chapterId: string): number | undefined => {
    return profile?.mastery_map?.[chapterId]?.score;
  };

  // Check if chapter is recommended
  const isRecommended = (chapterId: string): boolean => {
    return profile?.recommended_chapters?.includes(chapterId) ?? false;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.name?.split(" ")[0] || "Student"}!
        </h1>
        <p className="mt-2 text-gray-600">
          Choose a chapter to start your Socratic learning journey.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main content - Chapter cards */}
        <div className="flex-1">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse"
                >
                  <div className="h-4 bg-gray-200 rounded w-1/4 mb-4" />
                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-gray-200 rounded-lg" />
                    <div className="flex-1">
                      <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
                      <div className="h-4 bg-gray-200 rounded w-full" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
              <p className="text-red-600">
                Failed to load chapters. Please try again later.
              </p>
            </div>
          ) : !groupedChapters || Object.keys(groupedChapters).length === 0 ? (
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
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No chapters available yet
              </h3>
              <p className="text-gray-500">
                Check back later for new learning content.
              </p>
            </div>
          ) : (
            <div className="space-y-8">
              {Object.entries(groupedChapters).map(([bookId, { book, chapters }]) => (
                <div key={bookId}>
                  {/* Book header */}
                  <div className="mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">
                      {book?.title || "Unknown Book"}
                    </h2>
                    <p className="text-sm text-gray-500">
                      by {book?.author || "Unknown Author"} &bull;{" "}
                      {chapters.length} chapter{chapters.length !== 1 ? "s" : ""}
                    </p>
                  </div>

                  {/* Chapter cards grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {chapters.map((chapter) => (
                      <ChapterCard
                        key={chapter.id}
                        chapter={chapter}
                        masteryScore={getMasteryScore(chapter.id)}
                        isRecommended={isRecommended(chapter.id)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar - Learning profile */}
        <div className="lg:w-80 flex-shrink-0">
          <div className="lg:sticky lg:top-8">
            <ProfileSidebar />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
