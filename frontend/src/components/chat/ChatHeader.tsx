"use client";

/**
 * Chat header component with chapter info and controls
 */

import { useRouter } from "next/navigation";
import type { ChapterWithBook } from "@/types";

interface ChatHeaderProps {
  chapter: ChapterWithBook | null;
  isLoading?: boolean;
  onEndSession: () => void;
  isEnding?: boolean;
}

export default function ChatHeader({
  chapter,
  isLoading = false,
  onEndSession,
  isEnding = false,
}: ChatHeaderProps) {
  const router = useRouter();

  const handleBack = () => {
    router.push("/dashboard");
  };

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex-shrink-0">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        {/* Left: Back button and chapter info */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Back to Dashboard"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          {isLoading ? (
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-48 mb-1" />
              <div className="h-3 bg-gray-200 rounded w-32" />
            </div>
          ) : chapter ? (
            <div>
              <h1 className="text-lg font-semibold text-gray-900 line-clamp-1">
                Chapter {chapter.chapter_number}: {chapter.title}
              </h1>
              <p className="text-sm text-gray-500 line-clamp-1">
                {chapter.book?.title} by {chapter.book?.author}
              </p>
            </div>
          ) : (
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Study Session</h1>
              <p className="text-sm text-gray-500">Socratic Tutor</p>
            </div>
          )}
        </div>

        {/* Right: End session button */}
        <button
          onClick={onEndSession}
          disabled={isEnding || isLoading}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            isEnding || isLoading
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-red-50 text-red-600 hover:bg-red-100"
          }`}
        >
          {isEnding ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Ending...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              End Session
            </>
          )}
        </button>
      </div>
    </header>
  );
}
