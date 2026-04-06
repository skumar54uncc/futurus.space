"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { trackEvent } from "@/lib/analytics";
import toast from "react-hot-toast";
import { Loader2, Send, Shield } from "lucide-react";

export function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !message.trim()) {
      trackEvent("contact_submit_invalid");
      toast.error("A name, email, and a few words in the message are all I need.");
      return;
    }
    trackEvent("contact_submit_started");
    setSending(true);
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          subject: subject.trim() || "Note from Futurus contact form",
          message: message.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.error === "string" ? data.error : "Could not send that — try again in a moment.");
      }
      toast.success("Got it. I’ll read this and reply from my own inbox when I can.");
      trackEvent("contact_submit_success");
      setName("");
      setEmail("");
      setSubject("");
      setMessage("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong on our side.";
      trackEvent("contact_submit_failed");
      toast.error(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-lg rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 sm:p-8 shadow-xl shadow-black/20">
      <div className="flex items-start gap-3 mb-6 pb-6 border-b border-white/5">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20">
          <Shield className="h-4 w-4 text-indigo-300" aria-hidden />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-200">Your note stays between us</p>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            I only use what you send here to reply to you — not for marketing lists or resale. Share only what
            you&apos;re comfortable with.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <label htmlFor="contact-name" className="text-sm text-slate-300">
            What should I call you?
          </label>
          <Input
            id="contact-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="First name is fine"
            autoComplete="name"
            required
            aria-required="true"
            className="bg-white/[0.04] border-white/10 placeholder:text-slate-600"
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="contact-email" className="text-sm text-slate-300">
            Where can I write you back?
          </label>
          <Input
            id="contact-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            autoComplete="email"
            required
            aria-required="true"
            className="bg-white/[0.04] border-white/10 placeholder:text-slate-600"
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="contact-subject" className="text-sm text-slate-300">
            Topic <span className="text-slate-600">(optional)</span>
          </label>
          <Input
            id="contact-subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Idea about the simulation flow"
            className="bg-white/[0.04] border-white/10 placeholder:text-slate-600"
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="contact-message" className="text-sm text-slate-300">
            What&apos;s on your mind?
          </label>
          <Textarea
            id="contact-message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask anything, share feedback, or describe a rough edge you ran into — short or long is fine."
            rows={6}
            required
            aria-required="true"
            className="bg-white/[0.04] border-white/10 resize-y min-h-[150px] placeholder:text-slate-600"
          />
        </div>
        <Button
          type="submit"
          disabled={sending}
          className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-500 text-white duration-150"
        >
          {sending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sending…
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Send my message
            </>
          )}
        </Button>
        <p className="text-xs text-slate-600 leading-relaxed pt-1">
          I&apos;m a real human on the other end — I may need a day or two to respond, but I will.
        </p>
      </form>
    </div>
  );
}
