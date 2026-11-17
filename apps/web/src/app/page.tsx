import React from "react";
import Link from "next/link";
import { Shield, FileText, Bot, CheckCircle2, ArrowRight } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col font-sans">
      <Navbar />

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col gap-10">
        <div className="flex flex-col items-start gap-4 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-[#157A5B] border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Phase 2: Medical History & Chronological Timeline Active
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-[#172033] leading-tight">
            Your health history, <br />
            <span className="text-[#2457A6]">intelligently connected.</span>
          </h1>
          <p className="text-base sm:text-lg text-[#667085] leading-relaxed">
            AI-powered longitudinal personal healthcare management platform. Consolidate diagnostic reports, track biomarker trends, and query health records with verified clinical provenance.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white font-medium text-sm transition-colors shadow-sm"
            >
              Get Started
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white border border-[#E4E7EC] hover:bg-slate-50 text-[#172033] font-medium text-sm transition-colors"
            >
              Sign In to Portal
            </Link>
          </div>
        </div>

        {/* System Capability Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl bg-white border border-[#E4E7EC] shadow-sm flex flex-col gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-[#2457A6] flex items-center justify-center">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-[#172033] text-base">Document Intelligence</h3>
            <p className="text-sm text-[#667085] leading-normal">
              Automated OCR & table parsing for blood tests, prescriptions, and discharge summaries with exact reference ranges.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white border border-[#E4E7EC] shadow-sm flex flex-col gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-[#2457A6] flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-[#172033] text-base">AI Health Assistant</h3>
            <p className="text-sm text-[#667085] leading-normal">
              Patient-specific conversational assistant grounded strictly in your personal records with explicit citations.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white border border-[#E4E7EC] shadow-sm flex flex-col gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-[#157A5B] flex items-center justify-center">
              <Shield className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-[#172033] text-base">Privacy & Isolation</h3>
            <p className="text-sm text-[#667085] leading-normal">
              Argon2id password hashing, zero cross-patient leakage, HttpOnly cookies, and strict local-first AI processing.
            </p>
          </div>
        </div>

        {/* Phase 1 Status Grid */}
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-[#E4E7EC] pb-4">
            <div>
              <h2 className="text-lg font-bold text-[#172033]">Platform Status</h2>
              <p className="text-xs text-[#667085]">Phase 2 Medical History, Provenance Revisions & Timeline active</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-50 text-[#157A5B] border border-emerald-200">
              58/58 Backend Tests Passing
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">Authentication</span>
              <span className="font-semibold text-sm text-[#172033]">Argon2id + HttpOnly Sessions</span>
              <span className="text-xs text-[#157A5B]">SEC-004, SEC-005, SEC-006 Verified</span>
            </div>
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">Patient Isolation</span>
              <span className="font-semibold text-sm text-[#172033]">Strict Server Ownership</span>
              <span className="text-xs text-[#157A5B]">SEC-001 / SEC-002 Verified</span>
            </div>
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">Database Engine</span>
              <span className="font-semibold text-sm text-[#172033]">PostgreSQL 16 + pgvector</span>
              <span className="text-xs text-[#667085]">SQLAlchemy 2.0 + Alembic</span>
            </div>
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">AI Execution Tier</span>
              <span className="font-semibold text-sm text-[#172033]">Local-First (Ollama)</span>
              <span className="text-xs text-[#667085]">External AI Disabled by Default</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#E4E7EC] bg-white py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#667085]">
          <p>© 2026 MediFlow Platform. Free and Open Source Architecture.</p>
          <div className="flex gap-4">
            <a
              href="http://localhost:8000/api/v1/health"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[#2457A6] transition-colors"
            >
              API Health Status
            </a>
            <span>Security Model: SEC-001–018</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
