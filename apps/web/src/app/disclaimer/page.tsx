import React from "react";
import Link from "next/link";
import { AlertTriangle, Phone } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata = {
  title: "Health Disclaimer — MEDIFLOW",
  description:
    "MEDIFLOW is a personal health information tool, not a medical device or professional health service.",
};

export default function DisclaimerPage() {
  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col font-sans">
      <Navbar />

      <main className="max-w-3xl mx-auto px-6 py-16 w-full flex-1">
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-[#946200] flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h1 className="text-3xl font-extrabold text-[#172033]">Health Disclaimer</h1>
          </div>
          <p className="text-sm text-[#667085]">
            Please read this notice carefully before using MEDIFLOW.
          </p>
        </div>

        {/* emergency banner */}
        <div className="mb-8 rounded-xl border border-red-200 bg-red-50 p-5 flex gap-4 items-start">
          <Phone className="w-5 h-5 text-[#B42318] flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-sm text-[#B42318]">
              In a medical emergency, call your local emergency services immediately.
            </p>
            <p className="text-xs text-[#B42318] mt-1 leading-relaxed">
              Do not use MEDIFLOW or its AI Health Assistant for urgent symptoms or emergencies.
              Contact emergency services or go to the nearest emergency medical facility right away.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-[#E4E7EC] p-8 flex flex-col gap-8">
          <div className="border-b border-[#E4E7EC] pb-8">
            <h2 className="text-lg font-bold text-[#172033] mb-3">Not a medical service</h2>
            <div className="text-sm text-[#667085] leading-relaxed space-y-3">
              <p>
                MEDIFLOW is a personal health information management tool designed to help you
                organize and understand your own medical records. It is not a medical service,
                clinical application, medical device, or telemedicine platform.
              </p>
              <p>
                MEDIFLOW is not operated by or affiliated with any healthcare organization, clinic,
                hospital, or health authority.
              </p>
            </div>
          </div>

          <div className="border-b border-[#E4E7EC] pb-8">
            <h2 className="text-lg font-bold text-[#172033] mb-3">
              Not a substitute for professional medical advice
            </h2>
            <div className="text-sm text-[#667085] leading-relaxed space-y-3">
              <p>
                Nothing in MEDIFLOW — including AI assistant responses, extracted document details,
                timeline summaries, or measurement charts — constitutes medical advice, clinical
                diagnosis, or treatment recommendations.
              </p>
              <p>
                Always consult a qualified healthcare professional regarding any medical question,
                condition, or treatment decision. Never disregard or delay seeking professional
                medical care based on information displayed in MEDIFLOW.
              </p>
            </div>
          </div>

          <div className="border-b border-[#E4E7EC] pb-8">
            <h2 className="text-lg font-bold text-[#172033] mb-3">Limitations of AI responses</h2>
            <div className="text-sm text-[#667085] leading-relaxed space-y-3">
              <p>
                The AI Health Assistant summarizes and retrieves information from the personal
                records you upload. Automated responses can occasionally be incomplete or inaccurate
                and should always be verified against your original documents and discussed with a
                qualified clinician.
              </p>
              <p>
                The assistant only sees information present in your uploaded records. It cannot
                examine you, assess urgent changes in your health, or account for missing medical
                history.
              </p>
            </div>
          </div>

          <div className="border-b border-[#E4E7EC] pb-8">
            <h2 className="text-lg font-bold text-[#172033] mb-3">
              Accuracy of extracted document information
            </h2>
            <div className="text-sm text-[#667085] leading-relaxed space-y-3">
              <p>
                Automated extraction from uploaded documents may misread text or numbers —
                especially on handwritten notes, faded scans, or complex layouts. Always check
                extracted items against your original medical reports during the review step before
                confirming them.
              </p>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-bold text-[#172033] mb-3">Intended personal use</h2>
            <div className="text-sm text-[#667085] leading-relaxed space-y-3">
              <p>
                MEDIFLOW is intended solely to help individuals organize and review their own
                medical records for personal reference and preparation for healthcare visits.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 flex gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E4E7EC] bg-white hover:bg-slate-50 text-sm text-[#172033] transition-colors"
          >
            Back to Home
          </Link>
          <Link
            href="/privacy"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E4E7EC] bg-white hover:bg-slate-50 text-sm text-[#172033] transition-colors"
          >
            Privacy
          </Link>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
