import type { Metadata } from "next";
import Link from "next/link";
import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata: Metadata = {
  title: "Terms of Service — Futurus",
  description: "Terms for using Futurus.",
};

export default function TermsPage() {
  return (
    <LegalPageShell title="Terms of Service">
      <p className="text-slate-500 text-sm -mt-2 mb-6">
        These terms govern your use of Futurus. They are written for clarity for a personal / early-stage project and are
        not a substitute for legal advice.
      </p>

      <h2>Agreement</h2>
      <p>
        By accessing or using Futurus, you agree to these Terms. If you do not agree, do not use the service. We may
        update these Terms; continued use after changes constitutes acceptance.
      </p>

      <h2>The service</h2>
      <p>
        Futurus provides software that simulates ideas using AI-generated agents and reports. Output is{" "}
        <strong className="text-slate-300">informational and illustrative only</strong>. It is not financial, legal,
        medical, or professional advice, and not a guarantee of future outcomes, market performance, or customer
        behavior.
      </p>

      <h2>Your responsibilities</h2>
      <ul>
        <li>You are responsible for the accuracy of information you provide.</li>
        <li>You must not use the service unlawfully, to harm others, or to violate third-party rights.</li>
        <li>You must not attempt to disrupt, scrape, overload, or reverse-engineer the service beyond what is permitted by law.</li>
        <li>You are responsible for decisions you make based on simulation outputs.</li>
      </ul>

      <h2>Accounts</h2>
      <p>
        If the service requires an account, you must provide accurate information and keep credentials secure. We may
        suspend or terminate access for violations of these Terms or to protect the service.
      </p>

      <h2>Intellectual property</h2>
      <p>
        The Futurus name, branding, software, and content we create are owned by us or our licensors. You retain rights
        to your own inputs; you grant us a license to use those inputs solely to operate and improve the service for
        you.
      </p>

      <h2>Disclaimer of warranties</h2>
      <p>
        THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE.&rdquo; TO THE MAXIMUM EXTENT PERMITTED BY
        LAW, WE DISCLAIM ALL WARRANTIES, WHETHER EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A
        PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
        CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, DATA, OR GOODWILL, ARISING FROM YOUR USE OF THE
        SERVICE. OUR TOTAL LIABILITY FOR ANY CLAIM RELATING TO THE SERVICE WILL NOT EXCEED THE GREATER OF (A) THE AMOUNTS
        YOU PAID US FOR THE SERVICE IN THE TWELVE MONTHS BEFORE THE CLAIM OR (B) FIFTY U.S. DOLLARS (OR THE EQUIVALENT),
        IF YOU HAVE NOT PAID US.
      </p>

      <h2>Indemnity</h2>
      <p>
        You agree to indemnify and hold us harmless from claims, damages, and expenses (including reasonable attorneys&apos;
        fees) arising from your use of the service, your content, or your violation of these Terms, to the extent
        permitted by law.
      </p>

      <h2>Third parties</h2>
      <p>
        The service may link to or integrate third-party services. We are not responsible for their content or
        practices.
      </p>

      <h2>Cookies and analytics consent</h2>
      <p>
        Futurus may use essential storage for core site behavior and optional analytics only after your consent.
        By accepting analytics consent in the banner, you permit measurement of product usage events such as page
        views and feature interactions. You can decline optional analytics and continue using core functionality.
      </p>

      <h2>Governing law</h2>
      <p>
        These Terms are governed by the laws applicable in your primary place of residence or, if we specify a
        jurisdiction in a separate agreement, that jurisdiction—whichever we expressly publish in a future version of
        this page. Until then, disputes should be approached in good faith through contact below.
      </p>

      <h2>Contact</h2>
      <p>
        For questions about these Terms, reach out via the{" "}
        <Link href="/contact" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">
          contact form
        </Link>
        .
      </p>
    </LegalPageShell>
  );
}
