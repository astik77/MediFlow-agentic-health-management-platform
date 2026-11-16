import React from "react";
import { Shield, FileText, Bot, CheckCircle2 } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="border-b border-[#E4E7EC] bg-white sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#2457A6] flex items-center justify-center text-white font-bold text-lg shadow-sm">
              M
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-[#172033]">MEDIFLOW</span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-[#2457A6] border border-blue-200">
                Phase 0
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium">
            <a
              href="http://localhost:8000/api/v1/health"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-[#E4E7EC] bg-white hover:bg-slate-50 transition-colors text-[#667085]"
            >
              <span className="w-2 h-2 rounded-full bg-[#157A5B] animate-pulse"></span>
              API Health Status
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col gap-10">
        <div className="flex flex-col items-start gap-4 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-[#157A5B] border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Foundation Layer Verified
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-[#172033] leading-tight">
            Your health history, <br />
            <span className="text-[#2457A6]">intelligently connected.</span>
          </h1>
          <p className="text-base sm:text-lg text-[#667085] leading-relaxed">
            AI-powered longitudinal personal healthcare management platform. Consolidate diagnostic reports, track biomarker trends, and query health records with verified clinical provenance.
          </p>
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

        {/* Phase 0 Architecture Status Grid */}
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-[#E4E7EC] pb-4">
            <div>
              <h2 className="text-lg font-bold text-[#172033]">Phase 0: Architecture & Environment Status</h2>
              <p className="text-xs text-[#667085]">Repository scaffolding, test suite, and operational environment</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-50 text-[#157A5B] border border-emerald-200">
              25/25 Tests Passing
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">Frontend Layer</span>
              <span className="font-semibold text-sm text-[#172033]">Next.js 15 (App Router)</span>
              <span className="text-xs text-[#157A5B]">TypeScript + Tailwind + shadcn</span>
            </div>
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">Backend API</span>
              <span className="font-semibold text-sm text-[#172033]">FastAPI 0.163 / Python 3.11</span>
              <span className="text-xs text-[#157A5B]">Modular Monolith + Asyncpg</span>
            </div>
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">Database Engine</span>
              <span className="font-semibold text-sm text-[#172033]">PostgreSQL 16 + pgvector</span>
              <span className="text-xs text-[#667085]">Docker Compose + Alembic</span>
            </div>
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex flex-col gap-1">
              <span className="text-xs font-medium text-[#667085]">AI Execution Tier</span>
              <span className="font-semibold text-sm text-[#172033]">Local-First (Ollama)</span>
              <span className="text-xs text-[#667085]">qwen2.5:1.5b (Phase 5)</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#E4E7EC] bg-white py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#667085]">
          <p>© 2026 MediFlow Platform. Free and Open Source Architecture.</p>
          <div className="flex gap-4">
            <span>Docs & Standards: Active</span>
            <span>Security Model: SEC-001–018</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
