"use client";

/**
 * Session summary modal shown when conversation ends
 * Displays summary, topics covered, and recommendations
 */

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { ConversationSummary, ChapterWithBook } from "@/types";

interface SessionSummaryProps {
  summary: ConversationSummary;
  chapter: ChapterWithBook | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function SessionSummary({
  summary,
  chapter,
  isOpen,
  onClose,
}: SessionSummaryProps) {
  const router = useRouter();

  // Close on escape key
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, handleEscape]);

  const handleReturnToDashboard = () => {
    onClose();
    router.push("/dashboard");
  };

  // Calculate engagement level based on score
  const getEngagementLevel = (score: number): { label: string; color: string; bgColor: string } => {
    if (score >= 0.8) return { label: "Excellent", color: "text-green-700", bgColor: "bg-green-100" };
    if (score >= 0.6) return { label: "Good", color: "text-blue-700", bgColor: "bg-blue-100" };
    if (score >= 0.4) return { label: "Fair", color: "text-yellow-700", bgColor: "bg-yellow-100" };
    return { label: "Needs Improvement", color: "text-orange-700", bgColor: "bg-orange-100" };
  };

  const engagement = getEngagementLevel(summary.engagement_score);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden animate-scale-in">
          {/* Header */}
          <div className="px-6 py-5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">Session Complete!</h2>
                <p className="text-sm text-indigo-100 mt-1">
                  {chapter?.title || "Study Session"}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
            {/* Summary */}
            <section className="mb-6">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Session Summary
              </h3>
              <p className="text-gray-700 leading-relaxed">{summary.summary}</p>
            </section>

            {/* Stats row */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              {/* Questions asked */}
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{summary.questions_asked}</p>
                    <p className="text-sm text-gray-500">Questions Asked</p>
                  </div>
                </div>
              </div>

              {/* Engagement score */}
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 ${engagement.bgColor} rounded-lg flex items-center justify-center`}>
                    <svg className={`w-5 h-5 ${engagement.color}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {Math.round(summary.engagement_score * 100)}%
                    </p>
                    <p className={`text-sm ${engagement.color} font-medium`}>{engagement.label}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Topics covered */}
            {summary.topics_covered.length > 0 && (
              <section className="mb-6">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Topics Covered
                </h3>
                <div className="flex flex-wrap gap-2">
                  {summary.topics_covered.map((topic, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm bg-indigo-50 text-indigo-700 border border-indigo-100"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Concepts understood */}
            {summary.concepts_understood.length > 0 && (
              <section className="mb-6">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Concepts Mastered
                </h3>
                <div className="flex flex-wrap gap-2">
                  {summary.concepts_understood.map((concept, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm bg-green-50 text-green-700 border border-green-100"
                    >
                      {concept}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Areas to improve */}
            {summary.concepts_struggled.length > 0 && (
              <section className="mb-6">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center">
                  <svg className="w-4 h-4 text-orange-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  Areas to Review
                </h3>
                <div className="flex flex-wrap gap-2">
                  {summary.concepts_struggled.map((concept, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm bg-orange-50 text-orange-700 border border-orange-100"
                    >
                      {concept}
                    </span>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex gap-3">
              <button
                onClick={handleReturnToDashboard}
                className="flex-1 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/25"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Animation styles */}
      <style jsx>{`
        @keyframes scaleIn {
          from {
            transform: scale(0.95);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }
        .animate-scale-in {
          animation: scaleIn 0.2s ease-out;
        }
      `}</style>
    </>
  );
}
