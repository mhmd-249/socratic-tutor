"use client";

/**
 * Chat entry page
 * Handles starting a new conversation when ?chapter= query param is provided
 * Redirects to the conversation page once created
 */

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { useChat } from "@/hooks/useChat";

function ChatEntryContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const chapterId = searchParams.get("chapter");

  const { startConversation, error } = useChat();
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const initConversation = async () => {
      if (!chapterId || starting) return;

      setStarting(true);
      const conversationId = await startConversation(chapterId);

      if (conversationId) {
        // Redirect to the conversation page
        router.replace(`/chat/${conversationId}`);
      }
    };

    initConversation();
  }, [chapterId, startConversation, router, starting]);

  // No chapter ID provided
  if (!chapterId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Chapter Selected</h2>
          <p className="text-gray-500 mb-4">Please select a chapter from the dashboard to start studying.</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Error starting conversation
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to Start Session</h2>
          <p className="text-gray-500 mb-4">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Back to Dashboard
            </button>
            <button
              onClick={() => {
                setStarting(false);
                window.location.reload();
              }}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="relative w-24 h-24 mx-auto mb-6">
          {/* Animated book icon */}
          <div className="absolute inset-0 bg-indigo-100 rounded-2xl animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="w-12 h-12 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          {/* Spinner ring */}
          <div className="absolute inset-0 border-4 border-indigo-200 border-t-indigo-600 rounded-2xl animate-spin" style={{ animationDuration: "1.5s" }} />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Starting Your Session</h2>
        <p className="text-gray-500">Preparing the Socratic tutor...</p>
      </div>
    </div>
  );
}

export default function ChatEntryPage() {
  return (
    <ProtectedRoute>
      <ChatEntryContent />
    </ProtectedRoute>
  );
}
