import React from "react";
import Link from "next/link";
import {
  FileText,
  Bot,
  Clock,
  ShieldCheck,
  Upload,
  ScanText,
  TrendingUp,
  MessageSquareHeart,
  Lock,
  UserCheck,
  Cpu,
  BookOpen,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata = {
  title: "Features — MEDIFLOW",
  description:
    "Learn how MEDIFLOW helps you organize medical records, build a personal health timeline, and understand your health history with AI.",
};

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col font-sans">
      <Navbar />

      <main className="flex-1">
        {/* ── PAGE HERO: WHAT IS MEDIFLOW ───────────────────────────────────── */}
        <section className="bg-white border-b border-[#E4E7EC]">
          <div className="max-w-4xl mx-auto px-6 py-16 text-center">
            <p className="text-xs font-semibold uppercase tracking-wider text-[#2457A6] mb-3">
              What is MEDIFLOW
            </p>
            <h1 className="text-4xl font-extrabold tracking-tight text-[#172033]">
              A clearer way to organize and understand your health history
            </h1>
            <p className="mt-4 text-base text-[#667085] max-w-2xl mx-auto leading-relaxed">
              MEDIFLOW is a private, personal health workspace that helps you gather scattered
              medical documents, review the details inside them, and view your health story in one
              connected timeline.
            </p>
          </div>
        </section>

        {/* ── WHY MANAGING RECORDS IS DIFFICULT ─────────────────────────────── */}
        <section className="max-w-4xl mx-auto px-6 py-16">
          <div className="rounded-2xl border border-[#E4E7EC] bg-white p-8">
            <h2 className="text-xl font-bold text-[#172033] mb-4">
              Why managing medical records is harder than it should be
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                "Lab reports and prescriptions scattered across different clinics, emails, and folders",
                "No simple way to see how test results and measurements have changed over time",
                "Hard to recall past findings or dates when preparing for a doctor visit",
                "Medical terminology that can feel overwhelming without plain-language context",
                "No single place to search across all of your personal health documents",
                "Difficulty keeping track of allergies, conditions, and supporting reports together",
              ].map((point) => (
                <div key={point} className="flex items-start gap-2.5 text-sm text-[#667085]">
                  <span
                    className="mt-1 w-4 h-4 rounded-full bg-[#F7F9FC] border border-[#E4E7EC] flex-shrink-0 flex items-center justify-center"
                    aria-hidden="true"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2457A6]" />
                  </span>
                  <span>{point}</span>
                </div>
              ))}
            </div>
            <p className="mt-6 pt-5 border-t border-[#E4E7EC] text-sm text-[#172033] leading-relaxed">
              MEDIFLOW is built specifically for individual patients who want clarity over their own
              records. It is a personal health information workspace — not a hospital portal, clinic
              system, or diagnostic service.
            </p>
          </div>
        </section>

        {/* ── HOW MEDIFLOW HELPS & CORE CAPABILITIES ────────────────────────── */}
        <section className="bg-white border-y border-[#E4E7EC]">
          <div className="max-w-4xl mx-auto px-6 py-16">
            <h2 className="text-2xl font-bold text-[#172033] mb-2">
              How MEDIFLOW helps you every day
            </h2>
            <p className="text-sm text-[#667085] mb-10">
              Every capability is designed to keep your medical information organized, searchable,
              and under your control.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                {
                  icon: <Upload className="w-5 h-5" />,
                  iconBg: "bg-blue-50 text-[#2457A6]",
                  title: "Private document vault",
                  desc: "Store your lab reports, prescriptions, imaging summaries, and discharge documents in PDF or image format. Download your original files whenever you need them.",
                },
                {
                  icon: <ScanText className="w-5 h-5" />,
                  iconBg: "bg-indigo-50 text-[#2457A6]",
                  title: "Guided information extraction",
                  desc: "MEDIFLOW reads your uploaded reports and surfaces key findings such as test values, conditions, and dates. You review, adjust, or reject each item before saving.",
                },
                {
                  icon: <Clock className="w-5 h-5" />,
                  iconBg: "bg-amber-50 text-[#946200]",
                  title: "Chronological health timeline",
                  desc: "Every confirmed event and report appears in date order on your personal timeline, making it easier to trace how your health history unfolded.",
                },
                {
                  icon: <TrendingUp className="w-5 h-5" />,
                  iconBg: "bg-emerald-50 text-[#157A5B]",
                  title: "Health measurement trends",
                  desc: "Follow changes in lab measurements over time — such as blood glucose or cholesterol — plotted directly from your confirmed reports.",
                },
                {
                  icon: <FileText className="w-5 h-5" />,
                  iconBg: "bg-blue-50 text-[#2457A6]",
                  title: "Structured personal health history",
                  desc: "Keep an organized list of your medical conditions, allergies, symptoms, and observations — with links back to the source report for each record.",
                },
                {
                  icon: <MessageSquareHeart className="w-5 h-5" />,
                  iconBg: "bg-indigo-50 text-[#2457A6]",
                  title: "AI Health Assistant",
                  desc: "Ask questions about your own medical history in everyday language. Answers draw from your saved records and point you to the supporting documents.",
                },
                {
                  icon: <Bot className="w-5 h-5" />,
                  iconBg: "bg-blue-50 text-[#2457A6]",
                  title: "Fast document search",
                  desc: "Search across your uploaded medical files to quickly find a specific test, result, or report without opening every file one by one.",
                },
                {
                  icon: <UserCheck className="w-5 h-5" />,
                  iconBg: "bg-emerald-50 text-[#157A5B]",
                  title: "Full export and account control",
                  desc: "Export a complete portable copy of your health vault at any time, or permanently remove your account and all stored records whenever you choose.",
                },
              ].map((cap) => (
                <div
                  key={cap.title}
                  className="flex gap-4 p-5 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC]/40"
                >
                  <div
                    className={`w-9 h-9 rounded-lg ${cap.iconBg} flex items-center justify-center flex-shrink-0`}
                  >
                    {cap.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-[#172033]">{cap.title}</h3>
                    <p className="text-xs text-[#667085] mt-1 leading-relaxed">{cap.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── SIMPLE EXPLANATION OF THE WORKFLOW ────────────────────────────── */}
        <section className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-bold text-[#172033] mb-2">
            How medical information moves through MEDIFLOW
          </h2>
          <p className="text-sm text-[#667085] mb-10">
            Every record follows a transparent, patient-reviewed path from upload to insight.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              {
                step: "01",
                title: "Add a medical document",
                desc: "Upload a PDF or image of a lab report, prescription, or summary. Your file stays in your private document vault.",
              },
              {
                step: "02",
                title: "Review extracted details",
                desc: "MEDIFLOW highlights important details found in the document. Nothing is added to your confirmed history until you check and approve it.",
              },
              {
                step: "03",
                title: "Connect to your timeline",
                desc: "Approved entries join your chronological timeline and health history, staying linked to the original document for easy reference.",
              },
              {
                step: "04",
                title: "Track and ask questions",
                desc: "Review trends across visits, search past reports, and ask the AI assistant questions grounded in your personal records.",
              },
            ].map((s) => (
              <div
                key={s.step}
                className="flex gap-4 items-start p-5 rounded-xl border border-[#E4E7EC] bg-white"
              >
                <div className="w-9 h-9 rounded-lg bg-[#2457A6] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {s.step}
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-[#172033]">{s.title}</h3>
                  <p className="text-xs text-[#667085] mt-1 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── PATIENT CONTROL & PRIVACY ─────────────────────────────────────── */}
        <section className="bg-white border-y border-[#E4E7EC]">
          <div className="max-w-4xl mx-auto px-6 py-16">
            <h2 className="text-2xl font-bold text-[#172033] mb-2">
              Patient control and privacy
            </h2>
            <p className="text-sm text-[#667085] mb-8 max-w-2xl">
              MEDIFLOW is built for personal, self-hosted use so your medical information remains
              under your roof and under your decisions.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {[
                {
                  icon: <Lock className="w-5 h-5" />,
                  iconBg: "bg-blue-50 text-[#2457A6]",
                  title: "Private local storage",
                  desc: "Your documents and health records are stored on your own system rather than uploaded to third-party cloud platforms.",
                },
                {
                  icon: <ShieldCheck className="w-5 h-5" />,
                  iconBg: "bg-blue-50 text-[#2457A6]",
                  title: "Protected account access",
                  desc: "Passwords are protected with strong one-way encryption, and sessions expire automatically with the option to sign out across devices.",
                },
                {
                  icon: <Cpu className="w-5 h-5" />,
                  iconBg: "bg-indigo-50 text-[#2457A6]",
                  title: "Local-first AI processing",
                  desc: "The AI Health Assistant runs locally on your own device by default, with external AI services disabled unless you explicitly change settings.",
                },
                {
                  icon: <BookOpen className="w-5 h-5" />,
                  iconBg: "bg-amber-50 text-[#946200]",
                  title: "Patient-scoped access",
                  desc: "Each document, timeline entry, and assistant conversation is scoped strictly to your signed-in account.",
                },
              ].map((p) => (
                <div key={p.title} className="flex gap-4 p-5 rounded-xl border border-[#E4E7EC]">
                  <div
                    className={`w-9 h-9 rounded-lg ${p.iconBg} flex items-center justify-center flex-shrink-0`}
                  >
                    {p.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-[#172033]">{p.title}</h3>
                    <p className="text-xs text-[#667085] mt-1 leading-relaxed">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── WHAT AI CAN AND CANNOT DO ─────────────────────────────────────── */}
        <section className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-bold text-[#172033] mb-2">
            What MEDIFLOW&apos;s AI can and cannot do
          </h2>
          <p className="text-sm text-[#667085] mb-8">
            Clear boundaries help keep AI assistance helpful and responsible.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-6">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-5 h-5 text-[#157A5B]" />
                <h3 className="font-semibold text-sm text-[#157A5B]">What MEDIFLOW AI can do</h3>
              </div>
              <ul className="flex flex-col gap-2.5">
                {[
                  "Answer questions grounded in your personal health records",
                  "Summarize recent entries and reports from your health history",
                  "Help locate specific lab values, dates, or uploaded reports",
                  "Explain unfamiliar medical terms that appear in your records",
                  "Cite the supporting documents used in its answers",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-[#172033]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#157A5B] flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl border border-red-200 bg-red-50/70 p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertCircle className="w-5 h-5 text-[#B42318]" />
                <h3 className="font-semibold text-sm text-[#B42318]">
                  What MEDIFLOW AI cannot do
                </h3>
              </div>
              <ul className="flex flex-col gap-2.5">
                {[
                  "Diagnose medical conditions or confirm diseases",
                  "Prescribe medications or recommend specific treatments",
                  "Replace qualified doctors or emergency medical care",
                  "Know about health events not present in your uploaded records",
                  "Provide definitive clinical decisions about your health",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-[#172033]">
                    <AlertCircle className="w-3.5 h-3.5 text-[#B42318] flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-[#946200] leading-relaxed">
            <strong>Important:</strong> MEDIFLOW is a personal health information tool, not a
            medical device or clinical service. Always consult a qualified healthcare professional
            for medical advice, diagnosis, or treatment decisions.
          </div>
        </section>

        {/* ── ABOUT MEDIFLOW ────────────────────────────────────────────────── */}
        <section id="about-mediflow" className="scroll-mt-20 bg-white border-t border-[#E4E7EC]">
          <div className="max-w-4xl mx-auto px-6 py-16">
            <h2 className="text-2xl font-bold text-[#172033] mb-4">About MEDIFLOW</h2>
            <div className="text-sm text-[#667085] leading-relaxed space-y-4">
              <p>
                MEDIFLOW is an open-source, self-hosted personal healthcare management platform
                created for individuals who want a clearer, more organized way to manage their own
                medical history.
              </p>
              <p>
                Designed to run on your own computer or personal server, MEDIFLOW keeps your
                records private and under your control unless you choose to export or share them.
              </p>
              <p>
                MEDIFLOW is built strictly for individual patients. It is not a hospital
                administration portal, clinic workflow tool, or connected electronic health record
                network.
              </p>
            </div>
            <div className="mt-6 flex gap-3">
              <a
                href="https://github.com/astik77/MediFlow-agentic-health-management-platform"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E4E7EC] bg-[#F7F9FC] hover:bg-slate-100 text-sm text-[#172033] transition-colors font-medium"
              >
                View project on GitHub
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </section>

        {/* ── CTA ───────────────────────────────────────────────────────────── */}
        <section className="max-w-4xl mx-auto px-6 py-16 text-center">
          <h2 className="text-2xl font-bold text-[#172033]">Ready to organize your records?</h2>
          <p className="mt-3 text-sm text-[#667085] max-w-md mx-auto">
            Create your account and start building a clear, connected personal health timeline.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white font-medium text-sm transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] focus-visible:ring-offset-2"
            >
              Create Your Account
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg border border-[#E4E7EC] bg-white hover:bg-slate-50 text-[#172033] font-medium text-sm transition-colors"
            >
              Back to Home
            </Link>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
