import type { Metadata } from "next";
import Link from "next/link";
import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata: Metadata = {
  title: "Privacy Policy — Futurus",
  description: "How Futurus handles your data and privacy.",
};

export default function PrivacyPage() {
  return (
    <LegalPageShell title="Privacy Policy">
      <p className="text-slate-500 text-sm -mt-2 mb-6">
        This is a plain-language policy for a personal / early-stage product. It is not legal advice. If you need a
        formal policy for your jurisdiction or business, consult a qualified attorney.
      </p>

      <h2>Who we are</h2>
      <p>
        Futurus (&ldquo;we,&rdquo; &ldquo;us&rdquo;) is an idea-simulation tool. This policy describes how we collect,
        use, and share information when you use the website and related services.
      </p>

      <h2>Information we collect</h2>
      <ul>
        <li>
          <strong className="text-slate-300">Account data.</strong> If you sign in (for example via Clerk), we receive
          identifiers and profile details that the provider shares with us, such as email address and name, according to
          that provider&apos;s terms.
        </li>
        <li>
          <strong className="text-slate-300">Content you submit.</strong> Ideas, answers, simulation inputs, and
          messages you enter are processed to run simulations and show you results.
        </li>
        <li>
          <strong className="text-slate-300">Technical data.</strong> Standard logs and diagnostics (e.g. IP address,
          device/browser type, timestamps) may be collected by hosting or analytics tools to keep the service secure and
          reliable.
        </li>
      </ul>

      <h2>Cookies and consent</h2>
      <p>
        Futurus uses essential browser storage for core functionality (for example sign-in/session flows) and,
        only when you explicitly accept, analytics storage for product metrics like page views and key events.
        If you decline analytics consent, non-essential analytics tracking remains off.
      </p>
      <p>
        You can change your consent choice by clearing site storage in your browser and reloading the page.
      </p>

      <h2>How we use information</h2>
      <ul>
        <li>To provide, operate, and improve Futurus (including AI-assisted features).</li>
        <li>To authenticate you and protect against abuse.</li>
        <li>To communicate with you about the service when appropriate.</li>
        <li>To comply with law or enforce our terms.</li>
      </ul>

      <h2>AI and third-party services</h2>
      <p>
        Simulations may rely on third-party AI, database, email, or infrastructure providers. Those providers process
        data according to their own policies. We aim to use reputable vendors and limit what we send to what is needed for
        the feature.
      </p>

      <h2>Retention</h2>
      <p>
        We keep information only as long as needed for the purposes above, unless a longer period is required by law.
        You may request deletion of your account or associated data where applicable; we will respond consistent with
        our technical capabilities and legal obligations.
      </p>

      <h2>Security</h2>
      <p>
        We use reasonable technical and organizational measures to protect information. No method of transmission or
        storage is 100% secure.
      </p>

      <h2>Children</h2>
      <p>
        Futurus is not directed at children under 13 (or the minimum age in your region). We do not knowingly collect
        personal information from children.
      </p>

      <h2>International users</h2>
      <p>
        If you access Futurus from outside the country where servers or vendors operate, your information may be
        transferred and processed across borders.
      </p>

      <h2>Changes</h2>
      <p>
        We may update this policy from time to time. The &ldquo;Last updated&rdquo; date at the top will change when we
        do. Continued use after changes means you accept the updated policy.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about privacy? Use the{" "}
        <Link href="/contact" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">
          contact form
        </Link>
        .
      </p>
    </LegalPageShell>
  );
}
