"use client";

/**
 * Study history component showing timeline of past study sessions
 * Displays quick stats and allows clicking to view conversation summaries
 */

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import type { Conversation, ChapterWithBook, LearningProfile } from "@/types";

interface StudyHistoryProps {
  conversations: Conversation[];
  chapters: ChapterWithBook[];
  profile: LearningProfile | null;
}

// Format duration
function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

// Format date for timeline
function formatTimelineDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return date.toLocaleDateString("en-US", { weekday: "long" });
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Group conversations by date
function groupByDate(conversations: Conversation[]): Map<string, Conversation[]> {
  const groups = new Map<string, Conversation[]>();

  conversations.forEach((conv) => {
    const date = new Date(conv.started_at);
    const dateKey = date.toISOString().split("T")[0]; // YYYY-MM-DD

    if (!groups.has(dateKey)) {
      groups.set(dateKey, []);
    }
    groups.get(dateKey)!.push(conv);
  });

  return groups;
}

// Session item component
function SessionItem({
  conversation,
  chapter,
  onClick,
}: {
  conversation: Conversation;
  chapter: ChapterWithBook | undefined;
  onClick: () => void;
}) {
  const statusStyles = {
    completed: {
      bg: "bg-green-100",
      color: "text-green-600",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      ),
    },
    active: {
      bg: "bg-blue-100",
      color: "text-blue-600",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
        </svg>
      ),
    },
    abandoned: {
      bg: "bg-gray-100",
      color: "text-gray-500",
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      ),
    },
  };

  const style = statusStyles[conversation.status];

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors text-left group"
    >
      {/* Status icon */}
      <div className={`flex-shrink-0 w-10 h-10 ${style.bg} rounded-full flex items-center justify-center ${style.color}`}>
        {style.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900 truncate">
            {chapter ? `Ch ${chapter.chapter_number}: ${chapter.title}` : "Unknown Chapter"}
          </span>
          {conversation.status === "active" && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
              In Progress
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500">
          {chapter?.book?.title || "Unknown Book"} &bull; {formatTimelineDate(conversation.started_at)}
        </p>
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

export default function StudyHistory({
  conversations,
  chapters,
  profile,
}: StudyHistoryProps) {
  const router = useRouter();

  // Sort conversations by date (newest first)
  const sortedConversations = useMemo(
    () =>
      [...conversations].sort(
        (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
      ),
    [conversations]
  );

  // Group by date
  const groupedConversations = useMemo(
    () => groupByDate(sortedConversations),
    [sortedConversations]
  );

  // Calculate stats
  const stats = useMemo(() => {
    const completedCount = conversations.filter((c) => c.status === "completed").length;
    const totalMinutes = profile?.total_study_time_minutes || 0;

    return {
      totalSessions: conversations.length,
      completedSessions: completedCount,
      totalStudyTime: totalMinutes,
    };
  }, [conversations, profile]);

  // Get chapter for a conversation
  const getChapter = (chapterId: string): ChapterWithBook | undefined => {
    return chapters.find((ch) => ch.id === chapterId);
  };

  // Format date header
  const formatDateHeader = (dateKey: string): string => {
    const date = new Date(dateKey);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return date.toLocaleDateString("en-US", { weekday: "long" });
    return date.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
  };

  const handleSessionClick = (conversation: Conversation) => {
    router.push(`/chat/${conversation.id}`);
  };

  if (conversations.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Study Sessions Yet</h3>
        <p className="text-gray-500 mb-4">
          Start your first study session to begin tracking your progress.
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Browse Chapters
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header with stats */}
      <div className="px-6 py-5 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Study History</h2>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center px-4 py-3 bg-indigo-50 rounded-lg">
            <p className="text-2xl font-bold text-indigo-600">{stats.totalSessions}</p>
            <p className="text-xs text-gray-600">Total Sessions</p>
          </div>
          <div className="text-center px-4 py-3 bg-green-50 rounded-lg">
            <p className="text-2xl font-bold text-green-600">{stats.completedSessions}</p>
            <p className="text-xs text-gray-600">Completed</p>
          </div>
          <div className="text-center px-4 py-3 bg-purple-50 rounded-lg">
            <p className="text-2xl font-bold text-purple-600">
              {formatDuration(stats.totalStudyTime)}
            </p>
            <p className="text-xs text-gray-600">Study Time</p>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="max-h-96 overflow-y-auto">
        {Array.from(groupedConversations.entries()).map(([dateKey, convs]) => (
          <div key={dateKey}>
            {/* Date header */}
            <div className="px-6 py-2 bg-gray-50 border-b border-gray-100 sticky top-0">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                {formatDateHeader(dateKey)}
              </p>
            </div>

            {/* Sessions for this date */}
            <div className="px-4 py-2">
              {convs.map((conv) => (
                <SessionItem
                  key={conv.id}
                  conversation={conv}
                  chapter={getChapter(conv.chapter_id)}
                  onClick={() => handleSessionClick(conv)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* View all link */}
      {conversations.length > 10 && (
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
          <button className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            View all {conversations.length} sessions
          </button>
        </div>
      )}
    </div>
  );
}
