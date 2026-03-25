import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "react-hot-toast";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Futurus — See what is about to be",
  description:
    "Write any idea. Futurus simulates it through 1,000 AI minds and shows you the future before you commit. For founders, creators, and curious thinkers.",
  keywords: [
    "idea simulation",
    "AI simulation",
    "startup validation",
    "idea testing",
    "MiroFish",
    "what-if simulation",
  ],
  openGraph: {
    title: "Futurus — See what is about to be",
    description:
      "Simulate any idea through 1,000 AI minds. Know the future before you commit.",
    url: "https://futurus.dev",
    siteName: "Futurus",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Futurus — See what is about to be",
    description: "Simulate any idea. See the future.",
  },
  metadataBase: new URL("https://futurus.dev"),
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark" suppressHydrationWarning>
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        </head>
        <body className="font-sans antialiased relative">
          <a href="#main-content" className="skip-nav">
            Skip to main content
          </a>
          {children}
          <Toaster
            position="bottom-right"
            gutter={10}
            toastOptions={{
              duration: 4000,
              style: {
                background: "var(--bg-elevated)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "10px",
                fontSize: "13px",
                fontFamily: "var(--font-sans)",
                padding: "10px 14px",
                boxShadow: "0 8px 40px rgba(0,0,0,0.35)",
                maxWidth: "360px",
              },
              success: {
                iconTheme: { primary: "#34d399", secondary: "var(--bg-void)" },
              },
              error: {
                iconTheme: { primary: "#f87171", secondary: "var(--bg-void)" },
                duration: 6000,
              },
            }}
          />
          <Analytics />
          <SpeedInsights />
        </body>
      </html>
    </ClerkProvider>
  );
}
