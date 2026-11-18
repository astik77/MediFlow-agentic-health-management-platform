import React from "react";
import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata = {
  title: "Privacy — MEDIFLOW",
  description: "How MEDIFLOW handles and protects your personal health data.",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-[#E4E7EC] pb-8 last:border-0 last:pb-0">
      <h2 className="text-lg font-bold text-[#172033] mb-3">{title}</h2>
      <div className="text-sm text-[#667085] leading-relaxed space-y-3">{children}</div>
    </div>
  );
}

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033] flex flex-col font-sans">
      <Navbar />

      <main className="max-w-3xl mx-auto px-6 py-16 w-full flex-1">
        <div className="mb-10">
          <h1 className="text-3xl font-extrabold text-[#172033]">Privacy</h1>
          <p className="mt-2 text-sm text-[#667085]">
            MEDIFLOW is a self-hosted personal application. This page explains what information the
            application stores and how it is handled during normal operation.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-[#E4E7EC] p-8 flex flex-col gap-8">
          <Section title="What data MEDIFLOW stores">
            <p>
              MEDIFLOW stores the following information inside your local installation:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>Your account details (name, email address, and one-way encrypted password)</li>
              <li>Medical documents you choose to upload</li>
              <li>
                Health history entries you confirm — such as conditions, allergies, symptoms,
                observations, and lab measurements
              </li>
              <li>Your conversation history with the AI Health Assistant</li>
              <li>Active sign-in session records</li>
            </ul>
            <p>
              During normal operation, no personal health data is sent to external servers operated
              by MEDIFLOW or any third party.
            </p>
          </Section>

          <Section title="Where your data is stored">
            <p>
              MEDIFLOW is designed to run on your own computer or personal server. Your account
              records, health history, and uploaded files are stored locally in your own
              installation. You remain responsible for securing and backing up the device or server
              where you run MEDIFLOW.
            </p>
          </Section>

          <Section title="Authentication and sessions">
            <p>
              Passwords are never stored in plain text. MEDIFLOW protects passwords using strong
              one-way hashing so your original password cannot be read back.
            </p>
            <p>
              Sign-in sessions use secure browser cookies that are inaccessible to page scripts and
              expire automatically. You can sign out or revoke active sessions from your profile
              settings at any time.
            </p>
          </Section>

          <Section title="AI processing and your records">
            <p>
              The AI Health Assistant uses a local AI service running on your own machine. When you
              ask a question, relevant excerpts from your own records are retrieved locally and
              processed on your device.
            </p>
            <p>
              <strong>External AI services are disabled by default.</strong> Your medical records
              are not transmitted to external AI providers during default operation.
            </p>
          </Section>

          <Section title="Account isolation">
            <p>
              Every uploaded document, health entry, timeline item, and assistant conversation is
              associated strictly with your signed-in account. Requests to access records are
              checked on the server against your active account.
            </p>
          </Section>

          <Section title="Exporting and deleting your data">
            <p>You stay in control of your records:</p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Export:</strong> Download a complete structured export of your personal
                health vault from your profile settings at any time.
              </li>
              <li>
                <strong>Delete:</strong> Permanently delete your account and all associated
                documents, health records, and assistant conversations from your profile settings.
                Account deletion cannot be undone.
              </li>
            </ul>
          </Section>

          <Section title="Third-party tracking">
            <p>
              MEDIFLOW does not include third-party advertising, analytics trackers, or telemetry
              services.
            </p>
          </Section>

          <Section title="Regulatory status">
            <p>
              MEDIFLOW is a personal, open-source project and does not claim HIPAA, GDPR, or other
              formal healthcare regulatory certification. If you operate MEDIFLOW in a setting
              subject to specific data protection rules, you are responsible for evaluating and
              meeting those obligations.
            </p>
          </Section>

          <Section title="Inspecting the source code">
            <p>
              Because MEDIFLOW is open source, you can review how data is stored and handled
              directly on{" "}
              <a
                href="https://github.com/astik77/MediFlow-agentic-health-management-platform"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#2457A6] hover:underline"
              >
                GitHub
              </a>
              .
            </p>
          </Section>
        </div>

        <div className="mt-8 flex gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E4E7EC] bg-white hover:bg-slate-50 text-sm text-[#172033] transition-colors"
          >
            Back to Home
          </Link>
          <Link
            href="/disclaimer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E4E7EC] bg-white hover:bg-slate-50 text-sm text-[#172033] transition-colors"
          >
            Health Disclaimer
          </Link>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
