"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Bot,
  ShieldCheck,
  Upload,
  ScanText,
  Clock,
  MessageSquareHeart,
  Lock,
  BookOpen,
  UserCheck,
  Cpu,
  ArrowRight,
  ChevronRight,
  TrendingUp,
  Activity,
  CalendarDays,
  FolderOpen,
  CheckCircle2,
  Link2,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Navbar } from "@/components/layout/Navbar";
import { PublicFooter } from "@/components/layout/PublicFooter";

/* ─────────────────────────── synthetic preview data ─────────────────────── */

const trendData = [
  { month: "Jan", value: 95 },
  { month: "Feb", value: 98 },
  { month: "Mar", value: 102 },
  { month: "Apr", value: 100 },
  { month: "May", value: 97 },
  { month: "Jun", value: 94 },
];

const timelineEvents = [
  {
    date: "12 Jun 2025",
    title: "Complete Blood Count",
    sub: "Haematology · City Diagnostics",
    category: "Lab Report",
    color: "#2457A6",
  },
  {
    date: "03 Apr 2025",
    title: "Lipid Panel",
    sub: "Cardiology · Central Lab",
    category: "Lab Report",
    color: "#157A5B",
  },
  {
    date: "18 Jan 2025",
    title: "Thyroid Function (TSH, T3, T4)",
    sub: "Endocrinology · Metro Labs",
    category: "Observation",
    color: "#946200",
  },
  {
    date: "05 Nov 2024",
    title: "Chest X-Ray Summary",
    sub: "Radiology · City Clinic",
    category: "Imaging",
    color: "#2457A6",
  },
];

const documents = [
  {
    name: "CBC Report — June 2025.pdf",
    type: "Lab Report",
    date: "12 Jun 2025",
    status: "Reviewed",
    statusColor: "#157A5B",
    statusBg: "#F0FDF4",
  },
  {
    name: "Lipid Panel — April 2025.pdf",
    type: "Lab Report",
    date: "03 Apr 2025",
    status: "Reviewed",
    statusColor: "#157A5B",
    statusBg: "#F0FDF4",
  },
  {
    name: "Thyroid Panel — Jan 2025.pdf",
    type: "Lab Report",
    date: "18 Jan 2025",
    status: "Pending Review",
    statusColor: "#946200",
    statusBg: "#FEF9C3",
  },
];

/* ─────────────────────────── hero product preview ───────────────────────── */

type PreviewTab = "overview" | "timeline" | "documents";

function ProductPreview() {
  const [tab, setTab] = useState<PreviewTab>("overview");

  const tabs: { key: PreviewTab; label: string; icon: React.ReactNode }[] = [
    { key: "overview", label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { key: "timeline", label: "Timeline", icon: <CalendarDays className="w-3.5 h-3.5" /> },
    { key: "documents", label: "Documents", icon: <FolderOpen className="w-3.5 h-3.5" /> },
  ];

  return (
    <div
      className="relative w-full max-w-[540px] rounded-2xl border border-[#E4E7EC] bg-white shadow-md overflow-hidden"
      aria-label="Interactive MEDIFLOW workspace preview"
    >
      {/* window chrome + accessible tablist */}
      <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-[#E4E7EC] bg-[#F7F9FC]">
        <div className="flex items-center gap-1.5" aria-hidden="true">
          <span className="w-2.5 h-2.5 rounded-full bg-[#D0D5DD]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#D0D5DD]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#D0D5DD]" />
        </div>
        <div
          role="tablist"
          aria-label="Preview sections"
          className="flex items-center gap-1 bg-white border border-[#E4E7EC] rounded-lg p-0.5"
        >
          {tabs.map((t) => {
            const isSelected = tab === t.key;
            return (
              <button
                key={t.key}
                type="button"
                role="tab"
                id={`preview-tab-${t.key}`}
                aria-selected={isSelected}
                aria-controls={`preview-panel-${t.key}`}
                onClick={() => setTab(t.key)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] ${
                  isSelected
                    ? "bg-[#2457A6] text-white shadow-xs"
                    : "text-[#667085] hover:text-[#172033] hover:bg-slate-50"
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* content area */}
      <div className="p-5 min-h-[348px] flex flex-col justify-between">
        {tab === "overview" && (
          <div
            key="overview"
            role="tabpanel"
            id="preview-panel-overview"
            aria-labelledby="preview-tab-overview"
            className="animate-panel-enter flex flex-col gap-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-[#667085]">Your Health Overview</p>
                <p className="text-sm font-semibold text-[#172033] mt-0.5">
                  Personal Health Summary
                </p>
              </div>
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-[#157A5B] border border-emerald-200/80">
                <span className="w-1.5 h-1.5 rounded-full bg-[#157A5B]" aria-hidden="true" />
                Recent upload · 12 Jun
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Documents", value: "12", sub: "3 added recently" },
                { label: "Conditions", value: "2", sub: "Recorded" },
                { label: "Allergies", value: "1", sub: "Confirmed" },
              ].map((kpi) => (
                <div
                  key={kpi.label}
                  className="rounded-xl border border-[#E4E7EC] bg-[#F7F9FC] p-3 hover:border-[#2457A6]/40 transition-colors"
                >
                  <p className="text-xs text-[#667085]">{kpi.label}</p>
                  <p className="text-xl font-bold text-[#172033] mt-0.5">{kpi.value}</p>
                  <p className="text-[11px] text-[#667085] mt-0.5">{kpi.sub}</p>
                </div>
              ))}
            </div>

            {/* biomarker trend visualization */}
            <div className="rounded-xl border border-[#E4E7EC] bg-white p-3.5 hover:border-[#2457A6]/40 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-[#172033] flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-[#2457A6]" />
                  Fasting Glucose (mg/dL)
                </p>
                <span className="text-[11px] text-[#667085]">Jan – Jun 2025</span>
              </div>
              <div className="w-full h-[92px]" aria-label="Sample fasting glucose trend chart from January to June 2025 showing values between 94 and 102 mg/dL">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 4, right: 8, bottom: 2, left: -8 }}>
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 10, fill: "#667085" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[88, 108]}
                      tick={{ fontSize: 10, fill: "#667085" }}
                      axisLine={false}
                      tickLine={false}
                      width={34}
                    />
                    <Tooltip
                      contentStyle={{
                        fontSize: 11,
                        padding: "4px 8px",
                        border: "1px solid #E4E7EC",
                        borderRadius: 8,
                        backgroundColor: "#FFFFFF",
                      }}
                      formatter={(v) => [`${v} mg/dL`, "Fasting Glucose"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#2457A6"
                      strokeWidth={2}
                      dot={{ r: 3, fill: "#2457A6", strokeWidth: 0 }}
                      activeDot={{ r: 4.5, fill: "#1D4688" }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {tab === "timeline" && (
          <div
            key="timeline"
            role="tabpanel"
            id="preview-panel-timeline"
            aria-labelledby="preview-tab-timeline"
            className="animate-panel-enter flex flex-col gap-3"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-[#172033]">Medical Timeline</p>
              <span className="text-[11px] text-[#667085]">Chronological · 2024–2025</span>
            </div>
            <div className="relative flex flex-col">
              {timelineEvents.map((ev, i) => (
                <div
                  key={ev.title}
                  className="flex gap-3 items-start group rounded-lg px-2 py-1.5 hover:bg-[#F7F9FC] transition-colors"
                >
                  <div className="flex flex-col items-center pt-1">
                    <div
                      className="w-2.5 h-2.5 rounded-full border-2 bg-white"
                      style={{ borderColor: ev.color }}
                    />
                    {i < timelineEvents.length - 1 && (
                      <div className="w-px flex-1 bg-[#E4E7EC] mt-1" style={{ minHeight: 28 }} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs text-[#667085]">{ev.date}</p>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-[#667085]">
                        {ev.category}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-[#172033] mt-0.5">{ev.title}</p>
                    <p className="text-xs text-[#667085]">{ev.sub}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "documents" && (
          <div
            key="documents"
            role="tabpanel"
            id="preview-panel-documents"
            aria-labelledby="preview-tab-documents"
            className="animate-panel-enter flex flex-col gap-3"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-[#172033]">Uploaded Documents</p>
              <span className="text-[11px] text-[#667085]">3 of 12 shown</span>
            </div>
            <div className="flex flex-col gap-2.5">
              {documents.map((doc) => (
                <div
                  key={doc.name}
                  className="flex items-center justify-between gap-3 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC]/60 hover:bg-[#F7F9FC] hover:border-[#2457A6]/40 p-3 transition-colors"
                >
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#2457A6] flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[#172033] truncate">{doc.name}</p>
                      <p className="text-xs text-[#667085]">
                        {doc.type} · {doc.date}
                      </p>
                    </div>
                  </div>
                  <span
                    className="text-[11px] font-medium px-2.5 py-0.5 rounded-full flex-shrink-0"
                    style={{ color: doc.statusColor, backgroundColor: doc.statusBg }}
                  >
                    {doc.status}
                  </span>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-[#E4E7EC] bg-blue-50/40 px-3.5 py-2.5 flex items-center gap-2 text-xs text-[#2457A6]">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>Extracted details wait for your review before joining your health history.</span>
            </div>
          </div>
        )}

        <p className="pt-3 mt-2 border-t border-[#E4E7EC]/70 text-center text-[11px] text-[#667085]">
          Illustrative product preview · Sample data
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────── how-it-works steps ─────────────────────────── */

const workflowSteps = [
  {
    num: "01",
    icon: <Upload className="w-4 h-4" />,
    title: "Upload your medical documents",
    desc: "Add your lab reports, prescriptions, imaging reports, and discharge summaries to your personal health space.",
    previewTitle: "Personal Document Space",
    preview: (
      <div className="flex flex-col gap-3">
        {[
          { name: "CBC Report — June 2025.pdf", meta: "Lab Report · 240 KB" },
          { name: "Lipid Panel — April 2025.pdf", meta: "Lab Report · 185 KB" },
          { name: "Chest X-Ray Summary — Nov 2024.pdf", meta: "Imaging · 410 KB" },
        ].map((f) => (
          <div
            key={f.name}
            className="flex items-center justify-between gap-3 rounded-xl border border-[#E4E7EC] bg-white p-3"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#2457A6] flex items-center justify-center flex-shrink-0">
                <FileText className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-[#172033] truncate">{f.name}</p>
                <p className="text-[11px] text-[#667085]">{f.meta}</p>
              </div>
            </div>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-blue-50 text-[#2457A6]">
              Stored
            </span>
          </div>
        ))}
        <div className="mt-1 flex items-center justify-center gap-2 rounded-xl border border-dashed border-[#2457A6]/50 bg-blue-50/40 p-3.5 text-xs font-medium text-[#2457A6]">
          <Upload className="w-4 h-4" />
          Add PDF reports or medical document images
        </div>
      </div>
    ),
  },
  {
    num: "02",
    icon: <ScanText className="w-4 h-4" />,
    title: "Extract and review information",
    desc: "Important information is extracted from your documents so you can review, edit, and confirm it before it becomes part of your history.",
    previewTitle: "Candidate Review — CBC Report",
    preview: (
      <div className="flex flex-col gap-3">
        {[
          { label: "Haemoglobin", val: "13.4 g/dL", range: "Ref: 12.0 – 16.0 g/dL" },
          { label: "WBC Count", val: "7,200 /μL", range: "Ref: 4,000 – 11,000 /μL" },
          { label: "Platelets", val: "230,000 /μL", range: "Ref: 150,000 – 450,000 /μL" },
        ].map((r) => (
          <div
            key={r.label}
            className="flex items-center justify-between rounded-xl border border-[#E4E7EC] bg-white p-3"
          >
            <div>
              <p className="text-xs font-semibold text-[#172033]">{r.label}</p>
              <p className="text-[11px] text-[#667085]">{r.range}</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold text-[#172033]">{r.val}</p>
              <span className="inline-block mt-0.5 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-[#157A5B]">
                Ready to confirm
              </span>
            </div>
          </div>
        ))}
        <div className="flex items-center gap-2.5 pt-1" aria-hidden="true">
          <span className="flex-1 text-center py-2 rounded-lg bg-[#2457A6] text-white text-xs font-medium">
            Confirm &amp; Add to History
          </span>
          <span className="px-4 py-2 rounded-lg border border-[#E4E7EC] bg-white text-[#667085] text-xs font-medium">
            Skip
          </span>
        </div>
      </div>
    ),
  },
  {
    num: "03",
    icon: <Clock className="w-4 h-4" />,
    title: "Build your medical timeline",
    desc: "Approved information becomes part of your chronological medical history, making previous reports and health events easier to follow.",
    previewTitle: "Chronological Health Timeline",
    preview: (
      <div className="flex flex-col gap-1">
        {timelineEvents.slice(0, 3).map((ev, i) => (
          <div key={ev.title} className="flex gap-3.5 items-start">
            <div className="flex flex-col items-center pt-1.5">
              <div
                className="w-3 h-3 rounded-full border-2 bg-white"
                style={{ borderColor: ev.color }}
              />
              {i < 2 && <div className="w-px flex-1 bg-[#E4E7EC] mt-1" style={{ minHeight: 38 }} />}
            </div>
            <div className="flex-1 rounded-xl border border-[#E4E7EC] bg-white p-3 mb-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-medium text-[#667085]">{ev.date}</span>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#F7F9FC] text-[#2457A6] border border-[#E4E7EC]">
                  {ev.category}
                </span>
              </div>
              <p className="text-xs font-semibold text-[#172033] mt-1">{ev.title}</p>
              <p className="text-[11px] text-[#667085] mt-0.5">{ev.sub}</p>
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    num: "04",
    icon: <MessageSquareHeart className="w-4 h-4" />,
    title: "Ask questions and explore insights",
    desc: "Explore your available health history, understand medical information, and find relevant details with source-linked answers.",
    previewTitle: "AI Health Assistant",
    preview: (
      <div className="flex flex-col gap-3">
        <div className="rounded-xl bg-white border border-[#E4E7EC] p-3.5">
          <p className="text-[11px] font-medium text-[#667085] mb-1">Your question</p>
          <p className="text-xs text-[#172033]">
            &ldquo;What were my haemoglobin values over the past year?&rdquo;
          </p>
        </div>
        <div className="rounded-xl bg-blue-50/70 border border-blue-200/80 p-3.5 text-xs text-[#172033]">
          <p className="font-semibold text-[#2457A6] mb-1.5">Answer grounded in your records</p>
          <p className="leading-relaxed">
            Across your uploaded blood count reports, your haemoglobin values were 13.1 g/dL
            (Dec 2024) and 13.4 g/dL (Jun 2025), both within the listed reference range of
            12.0 – 16.0 g/dL.
          </p>
          <div className="mt-3 pt-2.5 border-t border-blue-200/60 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-white text-[#2457A6] border border-blue-200">
              <Link2 className="w-3 h-3" />
              CBC Report — June 2025.pdf
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-white text-[#2457A6] border border-blue-200">
              <Link2 className="w-3 h-3" />
              CBC Report — Dec 2024.pdf
            </span>
          </div>
        </div>
        <p className="text-[11px] text-[#667085]">
          Informational summary based on your records — not medical advice.
        </p>
      </div>
    ),
  },
];

/* ───────────────────────────── main component ────────────────────────────── */

export default function Home() {
  const [activeStep, setActiveStep] = useState(0);

  const handleGetStarted = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById("how-it-works");
    if (target) {
      const offset = 72; // sticky header height
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;
      window.scrollTo({ top, behavior: prefersReducedMotion ? "auto" : "smooth" });
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col font-sans">
      <Navbar />

      <main className="flex-1">
        {/* ── HERO ──────────────────────────────────────────────────────────── */}
        <section className="max-w-6xl w-full mx-auto px-6 pt-16 pb-20 flex flex-col lg:flex-row items-center gap-14">
          {/* left */}
          <div className="flex flex-col gap-6 lg:w-[46%]">
            <h1 className="text-4xl xl:text-5xl font-extrabold tracking-tight text-[#172033] leading-[1.15]">
              Your health history,
              <br />
              <span className="text-[#2457A6]">in one connected timeline.</span>
            </h1>
            <p className="text-base text-[#667085] leading-relaxed max-w-lg">
              A private, AI-powered workspace for your medical records. Upload reports, organize
              health information, track changes over time, and ask questions grounded in your
              personal health history.
            </p>
            <div className="flex items-center gap-3 pt-1">
              <a
                href="#how-it-works"
                onClick={handleGetStarted}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white font-medium text-sm transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] focus-visible:ring-offset-2"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </a>
              <Link
                href="/features"
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-white border border-[#E4E7EC] hover:bg-slate-50 text-[#172033] font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] focus-visible:ring-offset-2"
              >
                Explore Features
                <ChevronRight className="w-4 h-4 text-[#667085]" />
              </Link>
            </div>
          </div>

          {/* right — interactive preview */}
          <div className="lg:w-[54%] w-full flex justify-center lg:justify-end">
            <ProductPreview />
          </div>
        </section>

        {/* ── FEATURE CARDS ─────────────────────────────────────────────────── */}
        <section
          aria-label="Core capabilities"
          className="bg-white border-y border-[#E4E7EC]"
        >
          <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: <FileText className="w-5 h-5" />,
                iconBg: "bg-blue-50 text-[#2457A6]",
                title: "Document Intelligence",
                desc: "Extract important information from lab reports, prescriptions, and discharge summaries. Review extracted details before adding them to your medical history.",
              },
              {
                icon: <Bot className="w-5 h-5" />,
                iconBg: "bg-indigo-50 text-[#2457A6]",
                title: "AI Health Assistant",
                desc: "Ask questions about your health history, understand medical reports, and retrieve relevant information with references to supporting records.",
              },
              {
                icon: <ShieldCheck className="w-5 h-5" />,
                iconBg: "bg-emerald-50 text-[#157A5B]",
                title: "Privacy & Data Control",
                desc: "Secure sessions, patient-scoped access, private document storage, and local-first AI processing with external AI disabled by default.",
              },
            ].map((card) => (
              <div
                key={card.title}
                className="h-full p-6 rounded-xl bg-white border border-[#E4E7EC] shadow-sm flex flex-col gap-3 hover:shadow-md hover:border-[#2457A6]/30 transition-all"
              >
                <div className={`w-10 h-10 rounded-lg ${card.iconBg} flex items-center justify-center flex-shrink-0`}>
                  {card.icon}
                </div>
                <h2 className="font-semibold text-[#172033] text-base">{card.title}</h2>
                <p className="text-sm text-[#667085] leading-relaxed">{card.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── HOW IT WORKS ──────────────────────────────────────────────────── */}
        <section id="how-it-works" className="scroll-mt-20 max-w-6xl mx-auto px-6 py-20">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold text-[#172033] tracking-tight">
              Your health records, connected.
            </h2>
            <p className="mt-3 text-[#667085] text-base max-w-xl mx-auto">
              From your first medical report to a clearer picture of your health history, MEDIFLOW
              helps bring everything together.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
            {/* connected vertical workflow steps */}
            <div
              role="tablist"
              aria-label="How MEDIFLOW works steps"
              aria-orientation="vertical"
              className="lg:col-span-5 relative flex flex-col gap-3"
            >
              {/* connecting progress line behind step icons */}
              <div
                className="hidden sm:block absolute left-[33px] top-8 bottom-8 w-px bg-[#E4E7EC] pointer-events-none"
                aria-hidden="true"
              />
              {workflowSteps.map((step, i) => {
                const isActive = activeStep === i;
                return (
                  <button
                    key={step.num}
                    type="button"
                    role="tab"
                    id={`workflow-tab-${i}`}
                    aria-selected={isActive}
                    aria-controls={`workflow-panel-${i}`}
                    onClick={() => setActiveStep(i)}
                    className={`relative z-10 flex items-start gap-4 p-4 rounded-xl text-left transition-all border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] ${
                      isActive
                        ? "border-[#2457A6] bg-white shadow-sm"
                        : "border-transparent bg-transparent hover:bg-white/80 hover:border-[#E4E7EC]"
                    }`}
                  >
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors border ${
                        isActive
                          ? "bg-[#2457A6] text-white border-[#2457A6]"
                          : "bg-white text-[#667085] border-[#E4E7EC]"
                      }`}
                    >
                      {step.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span
                        className={`text-xs font-semibold ${
                          isActive ? "text-[#2457A6]" : "text-[#667085]"
                        }`}
                      >
                        Step {step.num}
                      </span>
                      <p
                        className={`text-sm font-semibold mt-0.5 ${
                          isActive ? "text-[#172033]" : "text-[#475467]"
                        }`}
                      >
                        {step.title}
                      </p>
                      <p
                        className={`text-xs mt-1 leading-relaxed ${
                          isActive ? "text-[#667085]" : "text-[#667085]/80"
                        }`}
                      >
                        {step.desc}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* dynamic visual preview panel */}
            <div className="lg:col-span-7">
              <div
                key={activeStep}
                role="tabpanel"
                id={`workflow-panel-${activeStep}`}
                aria-labelledby={`workflow-tab-${activeStep}`}
                className="animate-panel-enter rounded-2xl border border-[#E4E7EC] bg-white shadow-sm overflow-hidden"
              >
                <div className="px-6 py-4 border-b border-[#E4E7EC] bg-[#F7F9FC] flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold text-[#2457A6]">
                      Step {workflowSteps[activeStep].num} of 04
                    </p>
                    <p className="text-sm font-semibold text-[#172033]">
                      {workflowSteps[activeStep].previewTitle}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5" aria-hidden="true">
                    {workflowSteps.map((s, idx) => (
                      <span
                        key={s.num}
                        className={`h-1.5 rounded-full transition-all ${
                          idx === activeStep
                            ? "w-6 bg-[#2457A6]"
                            : idx < activeStep
                            ? "w-3 bg-[#2457A6]/40"
                            : "w-3 bg-[#E4E7EC]"
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <div className="p-6 bg-[#F7F9FC]/60 min-h-[300px] flex flex-col justify-between">
                  {workflowSteps[activeStep].preview}
                  <p className="pt-4 mt-4 border-t border-[#E4E7EC] text-center text-[11px] text-[#667085]">
                    Illustrative demonstration · Sample data
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── TRUST SECTION ─────────────────────────────────────────────────── */}
        <section className="bg-white border-y border-[#E4E7EC]">
          <div className="max-w-6xl mx-auto px-6 py-16">
            <div className="mb-10 text-center">
              <h2 className="text-2xl font-bold text-[#172033] tracking-tight">
                What makes MEDIFLOW trustworthy
              </h2>
              <p className="mt-2 text-[#667085] text-sm max-w-lg mx-auto">
                Built for individual patients, with privacy, transparency, and personal control at
                its core.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              <div className="p-5 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC] flex flex-col gap-3">
                <div className="w-9 h-9 rounded-lg bg-blue-50 text-[#2457A6] flex items-center justify-center">
                  <Lock className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-sm text-[#172033]">
                  Privacy &amp; Data Protection
                </h3>
                <p className="text-xs text-[#667085] leading-relaxed">
                  Your records are accessible only through your signed-in account with strict
                  patient-scoped access and secure, automatically expiring sessions.
                </p>
              </div>

              <div className="p-5 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC] flex flex-col gap-3">
                <div className="w-9 h-9 rounded-lg bg-amber-50 text-[#946200] flex items-center justify-center">
                  <BookOpen className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-sm text-[#172033]">Source Provenance</h3>
                <p className="text-xs text-[#667085] leading-relaxed">
                  Health details remain linked to the original document they came from, so you can
                  always trace where an entry or answer originated.
                </p>
                <div className="mt-auto pt-1">
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-white text-[#2457A6] border border-[#E4E7EC]">
                    <Link2 className="w-3 h-3" />
                    Source: CBC Report · Jun 2025
                  </span>
                </div>
              </div>

              <div className="p-5 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC] flex flex-col gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 text-[#157A5B] flex items-center justify-center">
                  <UserCheck className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-sm text-[#172033]">Patient Control</h3>
                <p className="text-xs text-[#667085] leading-relaxed">
                  Review, edit, reject, or confirm extracted information before it enters your
                  confirmed history. Export your records or delete your account whenever you choose.
                </p>
              </div>

              <div className="p-5 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC] flex flex-col gap-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-50 text-[#2457A6] flex items-center justify-center">
                  <Cpu className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-sm text-[#172033]">Responsible AI</h3>
                <p className="text-xs text-[#667085] leading-relaxed">
                  Local-first AI helps you organize and understand your records with external AI
                  disabled by default. It never replaces qualified medical professionals or
                  emergency care.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── FINAL CTA ─────────────────────────────────────────────────────── */}
        <section className="max-w-6xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold text-[#172033] tracking-tight">
            Take control of your health history.
          </h2>
          <p className="mt-4 text-[#667085] text-base max-w-lg mx-auto">
            Bring your medical records together and make your health information easier to
            understand.
          </p>
          <div className="mt-8">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white font-medium text-sm transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] focus-visible:ring-offset-2"
            >
              Create Your Account
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
