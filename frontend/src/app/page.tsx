"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.push("/dashboard");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h1 className="text-6xl font-bold text-white mb-6">
          Socratic Tutor
        </h1>
        <p className="text-2xl text-indigo-100 mb-12">
          AI-powered learning through guided dialogue
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="px-8 py-3 bg-white text-indigo-600 font-semibold rounded-lg shadow-lg hover:bg-indigo-50 transition"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="px-8 py-3 bg-indigo-700 text-white font-semibold rounded-lg shadow-lg hover:bg-indigo-800 transition border-2 border-white"
          >
            Get Started
          </Link>
        </div>
      </div>
    </div>
  );
}
