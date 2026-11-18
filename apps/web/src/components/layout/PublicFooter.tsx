import React from "react";
import Link from "next/link";

const GITHUB_REPO_URL =
  "https://github.com/astik77/MediFlow-agentic-health-management-platform";

export function PublicFooter() {
  return (
    <footer className="border-t border-[#E4E7EC] bg-white py-6 mt-auto">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#667085]">
        <p>
          © {new Date().getFullYear()} MEDIFLOW. Personal health information workspace.
        </p>
        <nav aria-label="Footer navigation" className="flex items-center gap-5">
          <Link
            href="/privacy"
            className="hover:text-[#2457A6] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] rounded"
          >
            Privacy
          </Link>
          <Link
            href="/features#about-mediflow"
            className="hover:text-[#2457A6] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] rounded"
          >
            About
          </Link>
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[#2457A6] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] rounded"
          >
            GitHub
          </a>
          <Link
            href="/disclaimer"
            className="hover:text-[#2457A6] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2457A6] rounded"
          >
            Disclaimer
          </Link>
        </nav>
      </div>
    </footer>
  );
}
