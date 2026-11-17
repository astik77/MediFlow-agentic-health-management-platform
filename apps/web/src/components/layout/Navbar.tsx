"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LogOut,
  User as UserIcon,
  ShieldCheck,
  HeartPulse,
  FileText,
  Clock,
  MessageSquareHeart,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";

export function Navbar() {
  const { authenticated, user, isOnboarded, logout, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const navLinkClass = (href: string) =>
    `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
      pathname === href
        ? "bg-blue-50 text-[#2457A6] font-semibold"
        : "text-[#172033] hover:bg-slate-100"
    }`;

  return (
    <header className="border-b border-[#E4E7EC] bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-[#2457A6] group-hover:bg-[#1D4688] transition-colors flex items-center justify-center text-white font-bold text-lg shadow-sm">
              M
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-[#172033]">
                MEDIFLOW
              </span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-[#2457A6] border border-blue-200 hidden sm:inline">
                Phase 6
              </span>
            </div>
          </Link>

          {authenticated && (
            <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
              <Link href="/health" className={navLinkClass("/health")}>
                <HeartPulse className="w-4 h-4 text-[#2457A6]" />
                My Health
              </Link>
              <Link href="/documents" className={navLinkClass("/documents")}>
                <FileText className="w-4 h-4 text-[#2457A6]" />
                Documents
              </Link>
              <Link href="/timeline" className={navLinkClass("/timeline")}>
                <Clock className="w-4 h-4 text-[#2457A6]" />
                Timeline
              </Link>
              <Link href="/assistant" className={navLinkClass("/assistant")}>
                <MessageSquareHeart className="w-4 h-4 text-[#2457A6]" />
                AI Assistant
              </Link>
            </nav>
          )}
        </div>

        <nav className="flex items-center gap-2 sm:gap-3 text-sm font-medium">
          {isLoading ? (
            <span className="text-xs text-[#667085]">Checking session...</span>
          ) : authenticated && user ? (
            <>
              <Link
                href="/health"
                className="md:hidden inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-[#172033] hover:bg-slate-100"
              >
                <HeartPulse className="w-4 h-4 text-[#2457A6]" />
                Health
              </Link>
              <Link
                href="/documents"
                className="md:hidden inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-[#172033] hover:bg-slate-100"
              >
                <FileText className="w-4 h-4 text-[#2457A6]" />
                Docs
              </Link>
              <Link
                href="/timeline"
                className="md:hidden inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-[#172033] hover:bg-slate-100"
              >
                <Clock className="w-4 h-4 text-[#2457A6]" />
                Timeline
              </Link>
              <Link
                href="/assistant"
                className="md:hidden inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-[#172033] hover:bg-slate-100"
              >
                <MessageSquareHeart className="w-4 h-4 text-[#2457A6]" />
                AI
              </Link>
              {!isOnboarded && (
                <Link
                  href="/onboarding"
                  className="hidden lg:inline-flex text-xs px-3 py-1.5 rounded-md bg-amber-50 text-[#946200] border border-amber-200 hover:bg-amber-100 transition-colors"
                >
                  Complete Onboarding
                </Link>
              )}
              <Link href="/profile" className={navLinkClass("/profile")}>
                <UserIcon className="w-4 h-4 text-[#2457A6]" />
                <span className="hidden sm:inline">My Profile</span>
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#E4E7EC] text-[#667085] hover:text-[#B42318] hover:border-red-200 hover:bg-red-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="px-3.5 py-2 rounded-lg text-[#172033] hover:bg-slate-100 transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white transition-colors shadow-sm"
              >
                <ShieldCheck className="w-4 h-4" />
                Create Account
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
