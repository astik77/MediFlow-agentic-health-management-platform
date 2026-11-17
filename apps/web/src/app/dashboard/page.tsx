"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  HeartPulse,
  Info,
  Loader2,
  MessageSquareHeart,
  Minus,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { analyticsApi } from "@/lib/api";
import type {
  BiomarkerTrendSeries,
  HealthSummaryItem,
  TrendDirection,
  TrendWindow,
} from "@/types/analytics";

interface ChartPoint {
  dateLabel: string;
  fullDate: string;
  value: number;
  valueRaw: string;
  unit: string;
  flag: string | null;
  refRange: string | null;
}

const WINDOW_OPTIONS: Array<{ value: TrendWindow; label: string }> = [
  { value: "30d", label: "30 Days" },
  { value: "90d", label: "90 Days" },
  { value: "1y", label: "1 Year" },
  { value: "all", label: "All Time" },
];

const SUMMARY_WINDOWS = [7, 14, 30];

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function formatFullDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function DirectionBadge({
  direction,
  deltaPercent,
}: {
  direction: TrendDirection;
  deltaPercent: number | null;
}) {
  if (direction === "increasing") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-[#946200] border border-amber-200">
        <ArrowUpRight className="w-3.5 h-3.5" />
        {deltaPercent !== null ? `+${deltaPercent.toFixed(1)}%` : "Rising"}
      </span>
    );
  }
  if (direction === "decreasing") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-[#2457A6] border border-blue-200">
        <ArrowDownRight className="w-3.5 h-3.5" />
        {deltaPercent !== null ? `${deltaPercent.toFixed(1)}%` : "Falling"}
      </span>
    );
  }
  if (direction === "stable") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-[#157A5B] border border-emerald-200">
        <Minus className="w-3.5 h-3.5" />
        Stable
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-[#667085] border border-slate-200">
      1 reading
    </span>
  );
}

function AbnormalityBadge({ flag }: { flag: string | null }) {
  if (!flag) return null;
  const f = flag.toLowerCase();
  if (f === "critical" || f === "high" || f === "low") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-red-50 text-[#B42318] border border-red-200">
        {f}
      </span>
    );
  }
  if (f === "normal") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-emerald-50 text-[#157A5B] border border-emerald-200">
        normal
      </span>
    );
  }
  return null;
}

export default function DashboardPage() {
  const { authenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [trendWindow, setTrendWindow] = useState<TrendWindow>("all");
  const [selectedBiomarkerKey, setSelectedBiomarkerKey] = useState<string | null>(
    null
  );
  const [summaryWindowDays, setSummaryWindowDays] = useState<number>(7);
  const [activeSummaryId, setActiveSummaryId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.push("/login");
    }
  }, [authLoading, authenticated, router]);

  const dashboardQuery = useQuery({
    queryKey: ["analytics", "dashboard"],
    queryFn: () => analyticsApi.getDashboard(),
    enabled: authenticated,
  });

  const trendsQuery = useQuery({
    queryKey: ["analytics", "trends", trendWindow],
    queryFn: () => analyticsApi.getTrends({ window: trendWindow }),
    enabled: authenticated,
  });

  const summariesQuery = useQuery({
    queryKey: ["analytics", "summaries"],
    queryFn: () => analyticsApi.listSummaries(15),
    enabled: authenticated,
  });

  const generateSummaryMutation = useMutation({
    mutationFn: (days: number) => analyticsApi.generateSummary(days),
    onSuccess: (created: HealthSummaryItem) => {
      setActiveSummaryId(created.id);
      queryClient.invalidateQueries({ queryKey: ["analytics", "dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["analytics", "summaries"] });
    },
  });

  const trendSeriesList = useMemo(
    () => trendsQuery.data?.series ?? [],
    [trendsQuery.data]
  );

  const selectedSeries: BiomarkerTrendSeries | null = useMemo(() => {
    if (trendSeriesList.length === 0) return null;
    if (selectedBiomarkerKey) {
      const found = trendSeriesList.find(
        (s) => s.biomarker_key === selectedBiomarkerKey
      );
      if (found) return found;
    }
    return trendSeriesList[0];
  }, [trendSeriesList, selectedBiomarkerKey]);

  const chartData: ChartPoint[] = useMemo(() => {
    if (!selectedSeries) return [];
    return selectedSeries.points.map((pt) => ({
      dateLabel: formatShortDate(pt.observed_at),
      fullDate: formatFullDate(pt.observed_at),
      value: pt.value,
      valueRaw: pt.value_raw,
      unit: pt.unit || pt.unit_raw || "",
      flag: pt.abnormality_flag,
      refRange: pt.reference_range_text,
    }));
  }, [selectedSeries]);

  const yDomain = useMemo<[number, number]>(() => {
    if (!selectedSeries || selectedSeries.points.length === 0) return [0, 100];
    const nums = selectedSeries.points.map((p) => p.value);
    if (selectedSeries.reference_low !== null)
      nums.push(selectedSeries.reference_low);
    if (selectedSeries.reference_high !== null)
      nums.push(selectedSeries.reference_high);
    const minVal = Math.min(...nums);
    const maxVal = Math.max(...nums);
    const pad = Math.max((maxVal - minVal) * 0.15, maxVal === minVal ? 5 : 0.5);
    return [
      Number(Math.max(0, minVal - pad).toFixed(2)),
      Number((maxVal + pad).toFixed(2)),
    ];
  }, [selectedSeries]);

  const displayedSummary: HealthSummaryItem | null = useMemo(() => {
    const history = summariesQuery.data?.items ?? [];
    if (activeSummaryId) {
      const matched = history.find((s) => s.id === activeSummaryId);
      if (matched) return matched;
    }
    return history[0] ?? dashboardQuery.data?.latest_summary ?? null;
  }, [summariesQuery.data, dashboardQuery.data, activeSummaryId]);

  if (authLoading || !authenticated) {
    return (
      <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-[#2457A6]" />
        </div>
      </div>
    );
  }

  const kpis = dashboardQuery.data?.kpis;
  const pendingDocs = dashboardQuery.data?.pending_review_documents ?? [];
  const abnormalAlerts = dashboardQuery.data?.recent_abnormal_observations ?? [];
  const summaryHistory = summariesQuery.data?.items ?? [];

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172033]">
            Health Dashboard
          </h1>
          <p className="text-sm text-[#667085] mt-1">
            Longitudinal overview, confirmed biomarker trends, and 7-day
            summaries from your personal health vault.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-[#E4E7EC] bg-white text-sm font-medium text-[#172033] hover:bg-slate-50 transition-colors"
          >
            <FileText className="w-4 h-4 text-[#2457A6]" />
            Upload Document
          </Link>
          <Link
            href="/assistant"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-[#E4E7EC] bg-white text-sm font-medium text-[#172033] hover:bg-slate-50 transition-colors"
          >
            <MessageSquareHeart className="w-4 h-4 text-[#2457A6]" />
            AI Assistant
          </Link>
          <button
            type="button"
            onClick={() => generateSummaryMutation.mutate(summaryWindowDays)}
            disabled={generateSummaryMutation.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white text-sm font-medium transition-colors shadow-sm disabled:opacity-60"
          >
            {generateSummaryMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            Generate {summaryWindowDays}-Day Summary
          </button>
        </div>
      </div>

      {/* KPI Strip */}
      {dashboardQuery.isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, idx) => (
            <div
              key={idx}
              className="h-24 rounded-xl bg-white border border-[#E4E7EC] animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link
            href="/health"
            className="p-4 rounded-xl bg-white border border-[#E4E7EC] hover:border-blue-200 transition-colors"
          >
            <div className="flex items-center justify-between text-xs font-medium text-[#667085]">
              <span>Confirmed Observations</span>
              <Activity className="w-4 h-4 text-[#2457A6]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-[#172033]">
                {kpis?.confirmed_observations_count ?? 0}
              </span>
              {(kpis?.abnormal_observations_count ?? 0) > 0 && (
                <span className="text-xs font-medium text-[#B42318]">
                  {kpis?.abnormal_observations_count} flagged
                </span>
              )}
            </div>
          </Link>

          <Link
            href="/health"
            className="p-4 rounded-xl bg-white border border-[#E4E7EC] hover:border-blue-200 transition-colors"
          >
            <div className="flex items-center justify-between text-xs font-medium text-[#667085]">
              <span>Active Conditions &amp; Allergies</span>
              <HeartPulse className="w-4 h-4 text-[#157A5B]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-[#172033]">
                {kpis?.active_conditions_count ?? 0}
              </span>
              <span className="text-xs text-[#667085]">
                conditions · {kpis?.active_allergies_count ?? 0} allergies
              </span>
            </div>
          </Link>

          <Link
            href="/health"
            className="p-4 rounded-xl bg-white border border-[#E4E7EC] hover:border-blue-200 transition-colors"
          >
            <div className="flex items-center justify-between text-xs font-medium text-[#667085]">
              <span>Ongoing Symptoms</span>
              <ShieldAlert className="w-4 h-4 text-[#946200]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-[#172033]">
                {kpis?.ongoing_symptoms_count ?? 0}
              </span>
              <span className="text-xs text-[#667085]">
                {kpis?.documents_count ?? 0} documents filed
              </span>
            </div>
          </Link>

          <Link
            href="/documents"
            className="p-4 rounded-xl bg-white border border-[#E4E7EC] hover:border-amber-200 transition-colors"
          >
            <div className="flex items-center justify-between text-xs font-medium text-[#667085]">
              <span>Pending Your Review</span>
              <ClipboardCheck className="w-4 h-4 text-[#946200]" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-[#172033]">
                {(kpis?.pending_candidates_count ?? 0) +
                  (kpis?.pending_symptom_proposals_count ?? 0)}
              </span>
              <span className="text-xs text-[#667085]">
                {kpis?.pending_candidates_count ?? 0} labs ·{" "}
                {kpis?.pending_symptom_proposals_count ?? 0} AI drafts
              </span>
            </div>
          </Link>
        </div>
      )}

      {/* Main Analytics Grid: Biomarker Trend Chart + Alerts/Review Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Biomarker Trends (2 cols) */}
        <section className="lg:col-span-2 rounded-xl bg-white border border-[#E4E7EC] p-6 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-[#172033] flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-[#2457A6]" />
                Biomarker Trends
              </h2>
              <p className="text-xs text-[#667085] mt-0.5">
                Plots strictly confirmed numeric observations on unit-safe
                axes. Unconfirmed extracted candidates are excluded.
              </p>
            </div>

            <div className="inline-flex rounded-lg border border-[#E4E7EC] bg-[#F7F9FC] p-0.5 self-start">
              {WINDOW_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setTrendWindow(opt.value)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                    trendWindow === opt.value
                      ? "bg-[#2457A6] text-white shadow-sm"
                      : "text-[#667085] hover:text-[#172033]"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Biomarker Selector Pills */}
          {trendsQuery.isLoading ? (
            <div className="h-64 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
            </div>
          ) : trendSeriesList.length === 0 ? (
            <div className="rounded-lg border border-dashed border-[#D0D5DD] bg-[#F7F9FC] p-8 text-center space-y-2">
              <Activity className="w-8 h-8 text-[#667085] mx-auto" />
              <p className="text-sm font-medium text-[#172033]">
                No confirmed numeric biomarkers in this time window
              </p>
              <p className="text-xs text-[#667085] max-w-md mx-auto">
                Add lab results or vital signs in{" "}
                <Link
                  href="/health"
                  className="text-[#2457A6] font-medium hover:underline"
                >
                  My Health
                </Link>{" "}
                or confirm extracted observations from an uploaded report in{" "}
                <Link
                  href="/documents"
                  className="text-[#2457A6] font-medium hover:underline"
                >
                  Documents
                </Link>
                .
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {trendSeriesList.map((series) => {
                  const isActive =
                    selectedSeries?.biomarker_key === series.biomarker_key;
                  return (
                    <button
                      key={series.biomarker_key}
                      type="button"
                      onClick={() =>
                        setSelectedBiomarkerKey(series.biomarker_key)
                      }
                      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                        isActive
                          ? "bg-blue-50 border-[#2457A6] text-[#2457A6]"
                          : "bg-white border-[#E4E7EC] text-[#172033] hover:bg-slate-50"
                      }`}
                    >
                      <span>{series.display_name}</span>
                      <span className="text-[#667085]">
                        {series.latest_value}
                        {series.unit ? ` ${series.unit}` : ""}
                      </span>
                    </button>
                  );
                })}
              </div>

              {selectedSeries && (
                <>
                  {/* Selected Biomarker Stats Strip */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC]">
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-[#667085]">
                        Latest ({formatShortDate(selectedSeries.latest_observed_at)})
                      </p>
                      <div className="mt-1 flex items-center gap-1.5">
                        <span className="text-base font-bold text-[#172033]">
                          {selectedSeries.latest_value}
                          {selectedSeries.unit ? ` ${selectedSeries.unit}` : ""}
                        </span>
                        <AbnormalityBadge
                          flag={selectedSeries.latest_abnormality_flag}
                        />
                      </div>
                    </div>

                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-[#667085]">
                        Trend
                      </p>
                      <div className="mt-1">
                        <DirectionBadge
                          direction={selectedSeries.direction}
                          deltaPercent={selectedSeries.delta_percent}
                        />
                      </div>
                    </div>

                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-[#667085]">
                        Min / Mean / Max
                      </p>
                      <p className="mt-1 text-xs font-semibold text-[#172033]">
                        {selectedSeries.min_value} / {selectedSeries.mean_value}{" "}
                        / {selectedSeries.max_value}
                      </p>
                    </div>

                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-[#667085]">
                        Reference Range
                      </p>
                      <p className="mt-1 text-xs font-semibold text-[#157A5B]">
                        {selectedSeries.reference_range_text || "Not specified"}
                      </p>
                    </div>
                  </div>

                  {/* Recharts LineChart with Normal ReferenceArea */}
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={chartData}
                        margin={{ top: 10, right: 16, left: 0, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" />
                        <XAxis
                          dataKey="dateLabel"
                          tick={{ fontSize: 12, fill: "#667085" }}
                          stroke="#D0D5DD"
                        />
                        <YAxis
                          domain={yDomain}
                          tick={{ fontSize: 12, fill: "#667085" }}
                          stroke="#D0D5DD"
                          width={52}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            borderColor: "#E4E7EC",
                            borderRadius: "8px",
                            fontSize: "12px",
                          }}
                          formatter={(
                            val: unknown,
                            _name: unknown,
                            item: { payload?: ChartPoint }
                          ) => {
                            const pt = item?.payload;
                            const displayVal =
                              typeof val === "number" ? val : String(val ?? "");
                            return [
                              `${displayVal}${pt?.unit ? ` ${pt.unit}` : ""}${
                                pt?.flag ? ` (${pt.flag})` : ""
                              }`,
                              selectedSeries.display_name,
                            ];
                          }}
                          labelFormatter={(
                            _label: unknown,
                            payload: ReadonlyArray<{ payload?: ChartPoint }>
                          ) => {
                            const pt = payload?.[0]?.payload;
                            return pt ? pt.fullDate : "";
                          }}
                        />
                        {selectedSeries.reference_low !== null &&
                          selectedSeries.reference_high !== null && (
                            <ReferenceArea
                              y1={selectedSeries.reference_low}
                              y2={selectedSeries.reference_high}
                              fill="#157A5B"
                              fillOpacity={0.09}
                              strokeOpacity={0}
                            />
                          )}
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#2457A6"
                          strokeWidth={2.5}
                          dot={{ r: 4, fill: "#2457A6", strokeWidth: 2 }}
                          activeDot={{ r: 6, fill: "#1D4688" }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </>
              )}
            </>
          )}
        </section>

        {/* Right Column: Pending Review Queue & Abnormal Alerts */}
        <div className="space-y-6">
          {/* Pending Review Queue */}
          <section className="rounded-xl bg-white border border-[#E4E7EC] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-[#172033] flex items-center gap-2">
                <ClipboardCheck className="w-4 h-4 text-[#946200]" />
                Pending Review Queue
              </h2>
              {(kpis?.pending_candidates_count ?? 0) > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-[#946200] border border-amber-200">
                  {kpis?.pending_candidates_count} pending
                </span>
              )}
            </div>

            {pendingDocs.length === 0 &&
            (kpis?.pending_symptom_proposals_count ?? 0) === 0 ? (
              <div className="flex items-center gap-2 text-xs text-[#157A5B] bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>All extracted observations and AI drafts are reviewed.</span>
              </div>
            ) : (
              <div className="space-y-2.5">
                {pendingDocs.map((doc) => (
                  <Link
                    key={doc.document_id}
                    href={`/documents/${doc.document_id}`}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg border border-amber-200 bg-amber-50/50 hover:bg-amber-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[#172033] truncate">
                        {doc.document_title}
                      </p>
                      <p className="text-xs text-[#946200]">
                        {doc.pending_count} candidate observation(s) awaiting
                        confirmation
                      </p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-[#946200] shrink-0" />
                  </Link>
                ))}
                {(kpis?.pending_symptom_proposals_count ?? 0) > 0 && (
                  <Link
                    href="/assistant"
                    className="flex items-center justify-between gap-3 p-3 rounded-lg border border-blue-200 bg-blue-50/50 hover:bg-blue-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[#172033]">
                        AI Assistant Symptom Drafts
                      </p>
                      <p className="text-xs text-[#2457A6]">
                        {kpis?.pending_symptom_proposals_count} proposed symptom
                        record(s) ready to confirm or dismiss
                      </p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-[#2457A6] shrink-0" />
                  </Link>
                )}
              </div>
            )}
          </section>

          {/* Recent Flagged / Abnormal Confirmed Observations */}
          <section className="rounded-xl bg-white border border-[#E4E7EC] p-5 space-y-4">
            <h2 className="text-base font-semibold text-[#172033] flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#B42318]" />
              Recent Out-of-Range Flags
            </h2>

            {abnormalAlerts.length === 0 ? (
              <p className="text-xs text-[#667085]">
                No confirmed out-of-range observations recorded.
              </p>
            ) : (
              <div className="space-y-2.5">
                {abnormalAlerts.map((obs) => (
                  <div
                    key={obs.id}
                    className="p-3 rounded-lg border border-[#E4E7EC] bg-[#F7F9FC] flex items-start justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-[#172033] truncate">
                          {obs.display_name}
                        </span>
                        <AbnormalityBadge flag={obs.abnormality_flag} />
                      </div>
                      <p className="text-xs text-[#172033] mt-0.5">
                        {obs.value_raw} {obs.unit_raw || ""}{" "}
                        {obs.reference_range_text && (
                          <span className="text-[#667085]">
                            (Ref: {obs.reference_range_text})
                          </span>
                        )}
                      </p>
                      <p className="text-[11px] text-[#667085] mt-0.5">
                        {formatFullDate(obs.observed_at)}
                      </p>
                    </div>
                    {obs.source_document_id && (
                      <Link
                        href={`/documents/${obs.source_document_id}`}
                        className="text-xs text-[#2457A6] hover:underline shrink-0"
                      >
                        Source
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* 7-Day Longitudinal Health Summary & History */}
      <section className="rounded-xl bg-white border border-[#E4E7EC] p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[#172033] flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#2457A6]" />
              Longitudinal Health Summaries
            </h2>
            <p className="text-xs text-[#667085] mt-0.5">
              Synthesizes confirmed observations, symptoms, conditions, and
              uploaded documents over your chosen window.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              aria-label="Summary window days"
              value={summaryWindowDays}
              onChange={(e) => setSummaryWindowDays(Number(e.target.value))}
              className="rounded-lg border border-[#D0D5DD] bg-white px-2.5 py-1.5 text-xs font-medium text-[#172033]"
            >
              {SUMMARY_WINDOWS.map((d) => (
                <option key={d} value={d}>
                  Last {d} days
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => generateSummaryMutation.mutate(summaryWindowDays)}
              disabled={generateSummaryMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white text-xs font-medium transition-colors disabled:opacity-60"
            >
              {generateSummaryMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              Generate
            </button>
          </div>
        </div>

        {generateSummaryMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-[#B42318]">
            Unable to generate summary right now. Please try again.
          </div>
        )}

        {displayedSummary ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Active Summary Detail */}
            <div className="lg:col-span-2 rounded-xl border border-[#E4E7EC] bg-[#F7F9FC] p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-base font-bold text-[#172033]">
                  {displayedSummary.headline}
                </h3>
                <span
                  className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
                    displayedSummary.generation_mode === "local_ai"
                      ? "bg-blue-50 text-[#2457A6] border-blue-200"
                      : "bg-slate-100 text-[#667085] border-slate-200"
                  }`}
                >
                  {displayedSummary.generation_mode === "local_ai"
                    ? `Local AI (${displayedSummary.model_name ?? "Ollama"})`
                    : "Deterministic Summary"}
                </span>
              </div>

              <p className="text-xs text-[#667085]">
                Window: {formatFullDate(displayedSummary.period_start)} –{" "}
                {formatFullDate(displayedSummary.period_end)} (
                {displayedSummary.window_days} days)
              </p>

              <p className="text-sm text-[#172033] leading-relaxed">
                {displayedSummary.summary_text}
              </p>

              {/* Window Snapshot Pills */}
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-md bg-white border border-[#E4E7EC] text-[#172033]">
                  Observations:{" "}
                  <strong>
                    {displayedSummary.metrics_snapshot.observations_in_window}
                  </strong>
                </span>
                <span className="px-2.5 py-1 rounded-md bg-white border border-[#E4E7EC] text-[#172033]">
                  Out-of-Range:{" "}
                  <strong>
                    {
                      displayedSummary.metrics_snapshot
                        .abnormal_observations_in_window
                    }
                  </strong>
                </span>
                <span className="px-2.5 py-1 rounded-md bg-white border border-[#E4E7EC] text-[#172033]">
                  Symptoms:{" "}
                  <strong>
                    {displayedSummary.metrics_snapshot.symptoms_logged_in_window}
                  </strong>
                </span>
                <span className="px-2.5 py-1 rounded-md bg-white border border-[#E4E7EC] text-[#172033]">
                  Documents:{" "}
                  <strong>
                    {
                      displayedSummary.metrics_snapshot
                        .documents_uploaded_in_window
                    }
                  </strong>
                </span>
              </div>

              {displayedSummary.highlights.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-[#667085] mb-1.5">
                    Key Highlights
                  </h4>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-[#172033]">
                    {displayedSummary.highlights.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {displayedSummary.questions_for_doctor.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-[#667085] mb-1.5">
                    Questions to Discuss With Your Clinician
                  </h4>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-[#2457A6]">
                    {displayedSummary.questions_for_doctor.map((q, idx) => (
                      <li key={idx}>{q}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex items-start gap-2 rounded-lg bg-white border border-[#E4E7EC] p-3 text-xs text-[#667085]">
                <Info className="w-4 h-4 text-[#2457A6] shrink-0 mt-0.5" />
                <span>{displayedSummary.informational_disclaimer}</span>
              </div>
            </div>

            {/* Historical Summaries Selector */}
            <div className="space-y-2.5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[#667085]">
                Summary History ({summaryHistory.length})
              </h3>
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {summaryHistory.map((item) => {
                  const isSelected = displayedSummary.id === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setActiveSummaryId(item.id)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        isSelected
                          ? "bg-blue-50 border-[#2457A6]"
                          : "bg-white border-[#E4E7EC] hover:bg-slate-50"
                      }`}
                    >
                      <p className="text-xs font-semibold text-[#172033] line-clamp-1">
                        {item.headline}
                      </p>
                      <p className="text-[11px] text-[#667085] mt-1">
                        {item.window_days}d window ·{" "}
                        {formatFullDate(item.created_at)}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-[#D0D5DD] bg-[#F7F9FC] p-6 text-center space-y-2">
            <p className="text-sm font-medium text-[#172033]">
              No longitudinal health summaries generated yet
            </p>
            <p className="text-xs text-[#667085]">
              Click &ldquo;Generate&rdquo; above to create your first 7-day
              summary and log it to your Medical Timeline.
            </p>
          </div>
        )}
      </section>
      </main>
    </div>
  );
}
