/**
 * Custom hook for fetching and caching learning profile
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

// Query keys for cache management
export const profileKeys = {
  all: ["profile"] as const,
  profile: () => [...profileKeys.all, "data"] as const,
  recommendations: () => [...profileKeys.all, "recommendations"] as const,
};

/**
 * Fetch user's learning profile
 */
export function useLearningProfile() {
  return useQuery({
    queryKey: profileKeys.profile(),
    queryFn: () => apiClient.getLearningProfile(),
    staleTime: 2 * 60 * 1000, // Profile updates after conversations
  });
}

/**
 * Fetch recommended chapters based on profile
 */
export function useRecommendedChapters() {
  return useQuery({
    queryKey: profileKeys.recommendations(),
    queryFn: () => apiClient.getRecommendedChapters(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get mastery score for a specific chapter
 */
export function useChapterMastery(chapterId: string) {
  const { data: profile, ...rest } = useLearningProfile();

  const mastery = profile?.mastery_map?.[chapterId];

  return {
    ...rest,
    mastery,
    score: mastery?.score ?? 0,
    lastStudied: mastery?.last_studied,
    studyCount: mastery?.study_count ?? 0,
  };
}

/**
 * Get summary statistics from learning profile
 */
export function useProfileStats() {
  const { data: profile, ...rest } = useLearningProfile();

  if (!profile) {
    return {
      ...rest,
      stats: null,
    };
  }

  // Calculate stats
  const masteryEntries = Object.entries(profile.mastery_map || {});
  const totalChaptersStudied = masteryEntries.length;
  const averageMastery =
    totalChaptersStudied > 0
      ? masteryEntries.reduce((sum, [, entry]) => sum + entry.score, 0) /
        totalChaptersStudied
      : 0;

  const highMasteryCount = masteryEntries.filter(
    ([, entry]) => entry.score >= 0.7
  ).length;

  const activeGaps = profile.identified_gaps?.filter(
    (gap) => gap.severity === "high" || gap.severity === "medium"
  ).length ?? 0;

  const stats = {
    totalChaptersStudied,
    averageMastery: Math.round(averageMastery * 100),
    highMasteryCount,
    strengthsCount: profile.strengths?.length ?? 0,
    gapsCount: profile.identified_gaps?.length ?? 0,
    activeGaps,
    totalStudyTime: profile.total_study_time_minutes ?? 0,
    recommendedCount: profile.recommended_chapters?.length ?? 0,
  };

  return {
    ...rest,
    stats,
    profile,
  };
}

/**
 * Get top gaps (concepts to review)
 */
export function useTopGaps(limit = 5) {
  const { data: profile, ...rest } = useLearningProfile();

  const topGaps = profile?.identified_gaps
    ?.sort((a, b) => {
      // Sort by severity first, then by occurrence count
      const severityOrder = { high: 0, medium: 1, low: 2 };
      const severityDiff =
        severityOrder[a.severity] - severityOrder[b.severity];
      if (severityDiff !== 0) return severityDiff;
      return b.occurrence_count - a.occurrence_count;
    })
    .slice(0, limit);

  return {
    ...rest,
    gaps: topGaps ?? [],
  };
}
