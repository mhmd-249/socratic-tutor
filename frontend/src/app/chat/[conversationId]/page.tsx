"use client";

/**
 * Chat page for an existing conversation
 * Loads conversation history and allows continued interaction
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { MessageList, MessageInput, ChatHeader, SessionSummary } from "@/components/chat";
import { useChat } from "@/hooks/useChat";

function ChatContent() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.conversationId as string;

  const {
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    error,
    chapter,
    summary,
    isEnding,
    sendMessage,
    endConversation,
    loadConversation,
    clearError,
  } = useChat();

  const [showSummary, setShowSummary] = useState(false);

  // Load conversation on mount
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    }
  }, [conversationId, loadConversation]);

  // Show summary modal when conversation ends
  useEffect(() => {
    if (summary) {
      setShowSummary(true);
    }
  }, [summary]);

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  const handleEndSession = async () => {
    await endConversation();
  };

  const handleCloseSummary = () => {
    setShowSummary(false);
    router.push("/dashboard");
  };

  // Loading state
  if (isLoading && messages.length === 0) {
    return (
      <div className="flex flex-col h-screen bg-gray-50">
        <ChatHeader chapter={null} isLoading onEndSession={handleEndSession} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-500">Loading conversation...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error && messages.length === 0) {
    return (
      <div className="flex flex-col h-screen bg-gray-50">
        <ChatHeader chapter={null} isLoading={false} onEndSession={() => router.push("/dashboard")} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md mx-auto px-4">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to load conversation</h2>
            <p className="text-gray-500 mb-4">{error}</p>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <ChatHeader
        chapter={chapter}
        isLoading={isLoading}
        onEndSession={handleEndSession}
        isEnding={isEnding}
      />

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <p className="text-sm text-red-600">{error}</p>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Message list */}
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
      />

      {/* Input area */}
      <MessageInput
        onSend={handleSendMessage}
        disabled={isStreaming || isEnding}
        placeholder="Ask a question or share your thoughts..."
      />

      {/* Session summary modal */}
      {summary && (
        <SessionSummary
          summary={summary}
          chapter={chapter}
          isOpen={showSummary}
          onClose={handleCloseSummary}
        />
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
}
