"use client";

/**
 * Learning profile page showing comprehensive overview of the user's learning journey
 * Includes mastery overview, knowledge gaps, recommendations, and study history
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { ChapterDetail } from "@/components/cards";
import {
  MasteryOverview,
  GapsSection,
  RecommendationsSection,
  StudyHistory,
} from "@/components/profile";
import { useChapters, useLearningProfile, useConversations } from "@/hooks";
import type { ChapterWithBook } from "@/types";

function ProfileContent() {
  const router = useRouter();
  const { user } = useAuth();
  const { data: chapters = [], isLoading: chaptersLoading } = useChapters();
  const { data: profile, isLoading: profileLoading } = useLearningProfile();
  const { data: conversations = [], isLoading: conversationsLoading } = useConversations(100);

  // State for chapter detail modal
  const [selectedChapter, setSelectedChapter] = useState<ChapterWithBook | null>(null);

  const isLoading = chaptersLoading || profileLoading || conversationsLoading;

  // Calculate overall progress for header
  const overallProgress = (() => {
    if (!profile?.mastery_map || chapters.length === 0) return 0;
    const masteredCount = chapters.filter((ch) => {
      const mastery = profile.mastery_map[ch.id];
      return mastery && mastery.score >= 0.8;
    }).length;
    return Math.round((masteredCount / chapters.length) * 100);
  })();

  // Handle chapter click from mastery overview
  const handleChapterClick = (chapter: ChapterWithBook) => {
    setSelectedChapter(chapter);
  };

  // Handle prerequisite click in chapter detail
  const handlePrerequisiteClick = (chapterId: string) => {
    const prereq = chapters.find((ch) => ch.id === chapterId);
    if (prereq) {
      setSelectedChapter(prereq);
    }
  };

  // Get conversations for selected chapter
  const selectedChapterConversations = selectedChapter
    ? conversations.filter((c) => c.chapter_id === selectedChapter.id)
    : [];

  // Loading state
  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="animate-pulse">
          {/* Header skeleton */}
          <div className="mb-8">
            <div className="h-8 bg-gray-200 rounded w-64 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-96" />
          </div>

          {/* Stats skeleton */}
          <div className="grid grid-cols-4 gap-4 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl p-6 border border-gray-200">
                <div className="h-8 bg-gray-200 rounded w-16 mb-2" />
                <div className="h-4 bg-gray-200 rounded w-24" />
              </div>
            ))}
          </div>

          {/* Content skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-white rounded-xl h-96 border border-gray-200" />
            <div className="bg-white rounded-xl h-96 border border-gray-200" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Learning Profile
            </h1>
            <p className="mt-2 text-gray-600">
              Track your progress and discover what to study next, {user?.name?.split(" ")[0] || "Student"}.
            </p>
          </div>
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-5 text-white">
          <p className="text-3xl font-bold">{overallProgress}%</p>
          <p className="text-sm text-indigo-100">Overall Progress</p>
        </div>
        <div className="bg-white rounded-xl p-5 border border-gray-200">
          <p className="text-3xl font-bold text-green-600">
            {profile?.strengths?.length || 0}
          </p>
          <p className="text-sm text-gray-500">Strengths</p>
        </div>
        <div className="bg-white rounded-xl p-5 border border-gray-200">
          <p className="text-3xl font-bold text-orange-600">
            {profile?.identified_gaps?.length || 0}
          </p>
          <p className="text-sm text-gray-500">Areas to Improve</p>
        </div>
        <div className="bg-white rounded-xl p-5 border border-gray-200">
          <p className="text-3xl font-bold text-purple-600">
            {profile?.total_study_time_minutes
              ? `${Math.round(profile.total_study_time_minutes / 60)}h`
              : "0h"}
          </p>
          <p className="text-sm text-gray-500">Study Time</p>
        </div>
      </div>

      {/* Strengths (if any) */}
      {profile?.strengths && profile.strengths.length > 0 && (
        <div className="mb-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Your Strengths
          </h2>
          <div className="flex flex-wrap gap-2">
            {profile.strengths.map((strength, index) => (
              <span
                key={index}
                className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm bg-green-50 text-green-700 border border-green-100"
              >
                {strength}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left column */}
        <div className="space-y-8">
          {/* Recommendations */}
          <RecommendationsSection chapters={chapters} profile={profile ?? null} />

          {/* Knowledge Gaps */}
          <GapsSection gaps={profile?.identified_gaps || []} chapters={chapters} />
        </div>

        {/* Right column */}
        <div className="space-y-8">
          {/* Mastery Overview */}
          <MasteryOverview
            chapters={chapters}
            profile={profile ?? null}
            onChapterClick={handleChapterClick}
          />

          {/* Study History */}
          <StudyHistory
            conversations={conversations}
            chapters={chapters}
            profile={profile ?? null}
          />
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

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}
