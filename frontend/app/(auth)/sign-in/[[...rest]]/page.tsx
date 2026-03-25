"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SignIn } from "@clerk/nextjs";

function SignInInner() {
  const params = useSearchParams();
  const redirect = params.get("redirect_url") || "/dashboard";
  return (
    <div id="main-content" className="min-h-dvh flex items-center justify-center bg-muted/30">
      <SignIn forceRedirectUrl={redirect} />
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-dvh flex items-center justify-center bg-muted/30 text-slate-500 text-sm">
          Loading&hellip;
        </div>
      }
    >
      <SignInInner />
    </Suspense>
  );
}
