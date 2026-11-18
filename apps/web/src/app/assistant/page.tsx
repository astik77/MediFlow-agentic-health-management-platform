"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  MessageSquareHeart,
  Plus,
  Send,
  Archive,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  FileCheck2,
  Info,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { ApiError, conversationsApi } from "@/lib/api";
import type {
  ConversationDetail,
  ConversationItem,
} from "@/types/conversations";

export default function AssistantPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { authenticated, isLoading: authLoading } = useAuth();

  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [draftMessage, setDraftMessage] = useState<string>("");
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [selectedSeverities, setSelectedSeverities] = useState<Record<string, "mild" | "moderate" | "severe">>({});

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, authLoading, router]);

  const { data: conversations, isLoading: listLoading } = useQuery<
    ConversationItem[]
  >({
    queryKey: ["conversations"],
    queryFn: () => conversationsApi.list(false),
    enabled: authenticated,
  });

  // Auto-select latest conversation if none selected yet
  useEffect(() => {
    if (!activeConvId && conversations && conversations.length > 0) {
      setActiveConvId(conversations[0].id);
    }
  }, [activeConvId, conversations]);

  const { data: detail, isLoading: detailLoading } =
    useQuery<ConversationDetail>({
      queryKey: ["conversation", activeConvId],
      queryFn: () => conversationsApi.getDetail(activeConvId!),
      enabled: authenticated && Boolean(activeConvId),
    });

  const createConvMutation = useMutation({
    mutationFn: () => conversationsApi.create(),
    onSuccess: (created) => {
      setActiveConvId(created.id);
      setErrorBanner(null);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const archiveConvMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.archive(id),
    onSuccess: (_archived, id) => {
      if (activeConvId === id) {
        setActiveConvId(null);
      }
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const sendMutation = useMutation({
    mutationFn: async ({
      convId,
      content,
    }: {
      convId: string;
      content: string;
    }) => conversationsApi.sendMessage(convId, content),
    onSuccess: (turn) => {
      setDraftMessage("");
      setErrorBanner(null);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["conversation", turn.conversation.id],
      });
    },
    onError: (err: unknown) => {
      setErrorBanner(
        err instanceof ApiError
          ? err.detail
          : "Unable to send message right now."
      );
    },
  });

  const proposalMutation = useMutation({
    mutationFn: ({
      convId,
      msgId,
      decision,
      severity,
    }: {
      convId: string;
      msgId: string;
      decision: "accept" | "dismiss";
      severity?: "mild" | "moderate" | "severe";
    }) =>
      conversationsApi.resolveProposal(
        convId,
        msgId,
        decision,
        severity ? { severity } : undefined
      ),
    onSuccess: (_updated, vars) => {
      queryClient.invalidateQueries({
        queryKey: ["conversation", vars.convId],
      });
      queryClient.invalidateQueries({ queryKey: ["health"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
  });

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = draftMessage.trim();
    if (!content) return;
    setErrorBanner(null);

    try {
      let targetId = activeConvId;
      if (!targetId) {
        const created = await conversationsApi.create();
        targetId = created.id;
        setActiveConvId(created.id);
        queryClient.invalidateQueries({ queryKey: ["conversations"] });
      }
      sendMutation.mutate({ convId: targetId, content });
    } catch (err: unknown) {
      setErrorBanner(
        err instanceof ApiError
          ? err.detail
          : "Could not start a new conversation."
      );
    }
  };

  if (authLoading || !authenticated) {
    return (
      <div className="min-h-screen bg-[#F7F9FC]">
        <Navbar />
        <div className="flex items-center justify-center py-24 text-[#667085] gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
          Loading AI Health Assistant...
        </div>
      </div>
    );
  }

  const messages = detail?.messages || [];

  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6 flex flex-col gap-4">
        {/* Persistent Safety Disclaimer Header */}
        <div className="bg-blue-50/70 border border-blue-200 rounded-xl px-4 py-3 flex items-start gap-2.5 text-xs text-[#172033]">
          <Info className="w-4 h-4 text-[#2457A6] shrink-0 mt-0.5" />
          <p>
            <strong>Informational Personal Health Assistant:</strong> Grounded
            strictly in your private MEDIFLOW records.
            MEDIFLOW does not diagnose, prescribe, or change medication dosages.
            For emergencies, call <strong>112 / 108</strong> or local emergency
            services immediately.
          </p>
        </div>

        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[580px]">
          {/* Conversation Sidebar */}
          <aside className="lg:col-span-4 xl:col-span-3 bg-white border border-[#E4E7EC] rounded-xl shadow-sm flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[#E4E7EC] flex items-center justify-between gap-2">
              <h1 className="text-sm font-bold flex items-center gap-1.5">
                <MessageSquareHeart className="w-4 h-4 text-[#2457A6]" />
                Conversations
              </h1>
              <button
                type="button"
                disabled={createConvMutation.isPending}
                onClick={() => createConvMutation.mutate()}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[#2457A6] hover:bg-[#1D4688] text-white transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                New
              </button>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-[#E4E7EC]">
              {listLoading ? (
                <div className="p-6 text-center text-xs text-[#667085]">
                  Loading conversations...
                </div>
              ) : !conversations || conversations.length === 0 ? (
                <div className="p-6 text-center text-xs text-[#667085]">
                  No conversations yet. Start a new chat or send a message below.
                </div>
              ) : (
                conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`flex items-center justify-between gap-2 px-3.5 py-3 cursor-pointer transition-colors ${
                      conv.id === activeConvId
                        ? "bg-blue-50/70 border-l-2 border-l-[#2457A6]"
                        : "hover:bg-slate-50"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setActiveConvId(conv.id)}
                      className="text-left min-w-0 flex-1"
                    >
                      <p className="text-xs font-semibold text-[#172033] truncate">
                        {conv.title}
                      </p>
                      <p className="text-[11px] text-[#667085] mt-0.5">
                        {new Date(conv.last_message_at).toLocaleDateString()}
                      </p>
                    </button>
                    <button
                      type="button"
                      title="Archive conversation"
                      onClick={() => archiveConvMutation.mutate(conv.id)}
                      className="p-1.5 rounded-md text-[#98A2B3] hover:text-[#B42318] hover:bg-red-50 shrink-0"
                    >
                      <Archive className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </aside>

          {/* Main Chat Workspace */}
          <section className="lg:col-span-8 xl:col-span-9 bg-white border border-[#E4E7EC] rounded-xl shadow-sm flex flex-col overflow-hidden">
            {/* Chat Thread */}
            <div className="flex-1 p-5 overflow-y-auto space-y-4 max-h-[560px]">
              {detailLoading ? (
                <div className="flex items-center justify-center py-16 text-sm text-[#667085] gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-[#2457A6]" />
                  Loading messages...
                </div>
              ) : messages.length === 0 ? (
                <div className="py-14 text-center max-w-md mx-auto space-y-3">
                  <MessageSquareHeart className="w-10 h-10 text-[#2457A6]/80 mx-auto" />
                  <h2 className="text-base font-bold text-[#172033]">
                    Ask about your personal health history
                  </h2>
                  <p className="text-xs text-[#667085] leading-relaxed">
                    Try asking about recent lab results, explaining medical
                    terms from your documents, logging a new symptom, or
                    preparing questions for your next doctor visit.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 pt-2">
                    {[
                      "Summarize my active conditions and recent labs",
                      "I have had a mild headache since morning",
                      "Help me prepare questions for my doctor",
                    ].map((starter) => (
                      <button
                        key={starter}
                        type="button"
                        onClick={() => setDraftMessage(starter)}
                        className="text-xs px-3 py-1.5 rounded-full border border-[#D0D5DD] hover:border-[#2457A6] hover:bg-blue-50 text-[#172033] transition-colors"
                      >
                        {starter}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`max-w-[88%] rounded-xl px-4 py-3 text-sm space-y-3 ${
                        msg.role === "user"
                          ? "bg-[#2457A6] text-white"
                          : msg.safety_level === "emergency_escalation"
                            ? "bg-red-50 border-2 border-[#B42318] text-[#172033]"
                            : msg.safety_level === "boundary_refusal"
                              ? "bg-amber-50 border border-amber-300 text-[#172033]"
                              : "bg-[#F7F9FC] border border-[#E4E7EC] text-[#172033]"
                      }`}
                    >
                      {/* Safety header banner inside assistant message */}
                      {msg.safety_level === "emergency_escalation" && (
                        <div className="flex items-center gap-2 text-xs font-bold text-[#B42318]">
                          <ShieldAlert className="w-4 h-4 shrink-0" />
                          URGENT EMERGENCY ESCALATION
                        </div>
                      )}
                      {msg.safety_level === "boundary_refusal" && (
                        <div className="flex items-center gap-2 text-xs font-bold text-[#946200]">
                          <AlertTriangle className="w-4 h-4 shrink-0" />
                          Clinical Safety Boundary (Informational Only)
                        </div>
                      )}

                      <p className="whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </p>

                      {/* Cited Personal Health Records */}
                      {msg.cited_records_json &&
                        msg.cited_records_json.length > 0 && (
                          <div className="pt-2 border-t border-slate-200/80 space-y-1.5">
                            <p className="text-[11px] font-semibold text-[#667085] flex items-center gap-1">
                              <FileCheck2 className="w-3.5 h-3.5 text-[#2457A6]" />
                              Grounded in your records:
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {msg.cited_records_json.map((c) => (
                                <span
                                  key={`${c.entity_type}-${c.entity_id}`}
                                  className="text-[11px] px-2 py-0.5 rounded-full bg-white border border-[#D0D5DD] text-[#172033]"
                                >
                                  {c.label}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Clarifying Question Chips */}
                      {msg.clarifying_questions_json &&
                        msg.clarifying_questions_json.length > 0 && (
                          <div className="pt-2 border-t border-slate-200/80 space-y-1.5">
                            <p className="text-[11px] font-semibold text-[#667085]">
                              Helpful follow-up questions:
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {msg.clarifying_questions_json.map((q, idx) => (
                                <button
                                  key={idx}
                                  type="button"
                                  onClick={() => setDraftMessage(q)}
                                  className="text-left text-xs px-2.5 py-1 rounded-lg bg-white border border-blue-200 text-[#2457A6] hover:bg-blue-50 transition-colors"
                                >
                                  {q}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Proposal-Only Symptom Draft Card */}
                      {msg.proposed_action_json &&
                        msg.proposed_action_json.proposal_type === "symptom" && (
                          <div className="bg-white border border-blue-200 rounded-lg p-3 space-y-2 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-[#2457A6]">
                                Proposed Symptom Entry
                              </span>
                              <span className="capitalize px-2 py-0.5 rounded-full bg-slate-100 text-[#475467]">
                                {msg.proposed_action_json.status}
                              </span>
                            </div>
                            <div className="text-[#172033] space-y-1.5">
                              <div>
                                <strong>
                                  {msg.proposed_action_json.payload.name}
                                </strong>
                                {msg.proposed_action_json.payload.body_location &&
                                  ` · Area: ${msg.proposed_action_json.payload.body_location}`}
                              </div>

                              {msg.proposed_action_json.status === "pending" ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-[#475467] font-medium">Severity:</span>
                                  <div className="inline-flex rounded-md border border-[#D0D5DD] p-0.5 bg-slate-50 gap-1">
                                    {(["mild", "moderate", "severe"] as const).map((sev) => {
                                      const currentSev =
                                        selectedSeverities[msg.id] ??
                                        msg.proposed_action_json?.payload.severity ??
                                        "moderate";
                                      const isSelected = currentSev === sev;
                                      return (
                                        <button
                                          key={sev}
                                          type="button"
                                          onClick={() =>
                                            setSelectedSeverities((prev) => ({
                                              ...prev,
                                              [msg.id]: sev,
                                            }))
                                          }
                                          className={`px-2 py-0.5 rounded text-[11px] capitalize transition-colors ${
                                            isSelected
                                              ? "bg-[#2457A6] text-white font-semibold shadow-xs"
                                              : "text-[#475467] hover:text-[#172033] hover:bg-slate-200"
                                          }`}
                                        >
                                          {sev}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              ) : (
                                <p>
                                  Severity:{" "}
                                  <span className="capitalize font-medium">
                                    {msg.proposed_action_json.payload.severity}
                                  </span>
                                </p>
                              )}
                            </div>

                            {msg.proposed_action_json.status === "pending" && (
                              <div className="flex items-center gap-2 pt-1">
                                <button
                                  type="button"
                                  disabled={proposalMutation.isPending}
                                  onClick={() =>
                                    proposalMutation.mutate({
                                      convId: msg.conversation_id,
                                      msgId: msg.id,
                                      decision: "accept",
                                      severity:
                                        selectedSeverities[msg.id] ??
                                        msg.proposed_action_json?.payload.severity ??
                                        "moderate",
                                    })
                                  }
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#157A5B] hover:bg-emerald-800 text-white font-semibold"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Save to My Symptoms
                                </button>
                                <button
                                  type="button"
                                  disabled={proposalMutation.isPending}
                                  onClick={() =>
                                    proposalMutation.mutate({
                                      convId: msg.conversation_id,
                                      msgId: msg.id,
                                      decision: "dismiss",
                                    })
                                  }
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-[#D0D5DD] text-[#475467] hover:bg-slate-50"
                                >
                                  <XCircle className="w-3.5 h-3.5" />
                                  Dismiss
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {errorBanner && (
              <div className="mx-5 mb-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-xs text-[#B42318]">
                {errorBanner}
              </div>
            )}

            {/* Message Input Bar */}
            <form
              onSubmit={handleSend}
              className="p-4 border-t border-[#E4E7EC] bg-[#F7F9FC] flex items-center gap-2"
            >
              <input
                type="text"
                value={draftMessage}
                onChange={(e) => setDraftMessage(e.target.value)}
                placeholder="Ask about your health records, symptoms, or lab reports..."
                className="flex-1 px-3.5 py-2.5 text-sm bg-white border border-[#D0D5DD] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
              />
              <button
                type="submit"
                disabled={!draftMessage.trim() || sendMutation.isPending}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-semibold bg-[#2457A6] hover:bg-[#1D4688] text-white disabled:opacity-50 transition-colors"
              >
                {sendMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Send
              </button>
            </form>
          </section>
        </div>
      </main>
    </div>
  );
}
