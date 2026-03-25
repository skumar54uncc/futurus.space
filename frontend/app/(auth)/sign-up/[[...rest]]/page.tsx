"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SignUp } from "@clerk/nextjs";

function SignUpInner() {
  const params = useSearchParams();
  const redirect = params.get("redirect_url") || "/new";
  return (
    <div id="main-content" className="min-h-dvh flex items-center justify-center bg-muted/30">
      <SignUp forceRedirectUrl={redirect} />
    </div>
  );
}

export default function SignUpPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-dvh flex items-center justify-center bg-muted/30 text-slate-500 text-sm">
          Loading&hellip;
        </div>
      }
    >
      <SignUpInner />
    </Suspense>
  );
}
