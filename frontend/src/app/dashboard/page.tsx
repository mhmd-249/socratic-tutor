"use client";

/**
 * Dashboard page with chapter cards and learning profile sidebar
 */

import { useState, useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import ChapterGrid, { ChapterGridError, ChapterGridSkeleton } from "@/components/cards/ChapterGrid";
import ChapterDetail from "@/components/cards/ChapterDetail";
import ProfileSidebar from "@/components/layout/ProfileSidebar";
import { useChapters, useLearningProfile, useConversations } from "@/hooks";
import type { ChapterWithBook } from "@/types";

function DashboardContent() {
  const { user } = useAuth();
  const { data: chapters = [], isLoading, error, refetch } = useChapters();
  const { data: profile } = useLearningProfile();
  const { data: allConversations = [] } = useConversations(100); // Get more conversations for filtering

  // State for selected chapter detail
  const [selectedChapter, setSelectedChapter] = useState<ChapterWithBook | null>(null);

  // Get conversations for selected chapter
  const selectedChapterConversations = useMemo(() => {
    if (!selectedChapter || !allConversations) return [];
    return allConversations
      .filter((conv) => conv.chapter_id === selectedChapter.id)
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  }, [selectedChapter, allConversations]);

  // Handle chapter click
  const handleChapterClick = (chapter: ChapterWithBook) => {
    setSelectedChapter(chapter);
  };

  // Handle prerequisite click in detail view
  const handlePrerequisiteClick = (chapterId: string) => {
    const prereq = chapters.find((ch) => ch.id === chapterId);
    if (prereq) {
      setSelectedChapter(prereq);
    }
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
            <ChapterGridSkeleton count={6} />
          ) : error ? (
            <ChapterGridError onRetry={() => refetch()} />
          ) : (
            <ChapterGrid
              chapters={chapters}
              profile={profile}
              onChapterClick={handleChapterClick}
            />
          )}
        </div>

        {/* Sidebar - Learning profile */}
        <div className="lg:w-80 flex-shrink-0">
          <div className="lg:sticky lg:top-8">
            <ProfileSidebar />
          </div>
        </div>
      </div>

      {/* Chapter Detail Modal */}
      {selectedChapter && (
        <ChapterDetail
          chapter={selectedChapter}
          isOpen={!!selectedChapter}
          onClose={() => setSelectedChapter(null)}
          profile={profile}
          pastConversations={selectedChapterConversations}
          allChapters={chapters}
          onPrerequisiteClick={handlePrerequisiteClick}
        />
      )}
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
