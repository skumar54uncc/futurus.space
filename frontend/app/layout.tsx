import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "react-hot-toast";
import { getFuturusClerkAppearance } from "@/lib/clerk-appearance";
import { AnalyticsGate } from "@/components/analytics/AnalyticsGate";
import { CookieConsentBanner } from "@/components/analytics/CookieConsentBanner";
import "./globals.css";

const clerkSignInFallback =
  process.env.NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL || "/dashboard";
const clerkSignUpFallback =
  process.env.NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL || "/new";
const vercelAnalyticsEnabled = process.env.NEXT_PUBLIC_ENABLE_VERCEL_ANALYTICS === "true";
const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
const googleSiteVerification = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION || "";
const bingSiteVerification = process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION || "";
const allowTestClerkInProd = process.env.ALLOW_TEST_CLERK_IN_PROD === "true";

const isProductionDeploy = process.env.VERCEL_ENV === "production";

if (isProductionDeploy && !allowTestClerkInProd && clerkPublishableKey.startsWith("pk_test_")) {
  throw new Error("Invalid Clerk configuration: set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY to a live key (pk_live_) in production.");
}

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
    url: "https://www.futurus.dev",
    siteName: "Futurus",
    type: "website",
    images: [
      {
        url: "/brand/futurus-logo-dark.png",
        width: 1200,
        height: 630,
        alt: "Futurus",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Futurus — See what is about to be",
    description: "Simulate any idea. See the future.",
    images: ["/brand/futurus-logo-dark.png"],
  },
  metadataBase: new URL("https://www.futurus.dev"),
  alternates: {
    canonical: "https://www.futurus.dev",
  },
  verification: {
    google: googleSiteVerification || undefined,
    ...(bingSiteVerification
      ? {
          other: {
            "msvalidate.01": bingSiteVerification,
          },
        }
      : {}),
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      appearance={getFuturusClerkAppearance()}
      signInFallbackRedirectUrl={clerkSignInFallback}
      signUpFallbackRedirectUrl={clerkSignUpFallback}
    >
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
          {vercelAnalyticsEnabled ? <AnalyticsGate /> : null}
          <CookieConsentBanner />
        </body>
      </html>
    </ClerkProvider>
  );
}
