"use client";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageCircle, Send, Sparkles } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTED_QUESTIONS = [
  "Why did early adopters churn?",
  "Which customer segment should I focus on first?",
  "What's my biggest risk?",
  "How do I improve the viral coefficient?",
];

/** Renders model output as readable text (bold, headings, lists) instead of raw ** and ###. */
function AssistantMarkdown({ content }: { content: string }) {
  return (
    <div className="report-chat-markdown text-[13px] leading-relaxed text-slate-100/95 [&>*:first-child]:mt-0">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h4 className="mt-3 mb-1.5 text-sm font-bold tracking-tight text-white first:mt-0">{children}</h4>
          ),
          h2: ({ children }) => (
            <h4 className="mt-3 mb-1.5 text-sm font-bold tracking-tight text-white first:mt-0">{children}</h4>
          ),
          h3: ({ children }) => (
            <h4 className="mt-3 mb-1 text-sm font-semibold text-indigo-100 first:mt-0">{children}</h4>
          ),
          p: ({ children }) => <p className="mb-2.5 last:mb-0">{children}</p>,
          ul: ({ children }) => (
            <ul className="mb-2.5 list-disc space-y-1.5 pl-4 last:mb-0 marker:text-indigo-300/80">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2.5 list-decimal space-y-1.5 pl-4 last:mb-0 marker:text-indigo-300/80">{children}</ol>
          ),
          li: ({ children }) => <li className="pl-0.5">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          em: ({ children }) => <em className="italic text-slate-200">{children}</em>,
          hr: () => <hr className="my-3 border-0 border-t border-white/15" />,
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-indigo-400/50 pl-3 text-slate-300">{children}</blockquote>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              className="font-medium text-indigo-300 underline decoration-indigo-400/50 underline-offset-2 hover:text-indigo-200"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-black/25 px-1 py-0.5 font-mono text-[12px] text-indigo-100">{children}</code>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function ReportChat({ simulationId }: { simulationId: string }) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "I've analyzed your simulation results. Ask me anything about your startup's projected performance, customer behavior, or what to do next." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (message: string) => {
    if (!message.trim() || loading) return;
    const userMsg: Message = { role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { data } = await api.post(`/api/chat/${simulationId}`, {
        message,
        history: messages,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, something went wrong. Try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="relative rounded-2xl overflow-hidden border border-indigo-500/40 bg-gradient-to-b from-indigo-950/50 via-[hsl(234,32%,10%)] to-[hsl(234,33%,8%)] shadow-[0_0_0_1px_rgba(129,140,248,0.15),0_12px_40px_-12px_rgba(99,102,241,0.35)]"
      aria-labelledby="report-chat-heading"
    >
      <div
        className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 via-cyan-400 to-indigo-500 opacity-90"
        aria-hidden
      />
      <div className="px-4 sm:px-5 pt-5 pb-3 border-b border-white/10 bg-white/[0.03]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-400/30">
              <MessageCircle className="h-5 w-5" aria-hidden />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 gap-y-1">
                <h2 id="report-chat-heading" className="text-base font-semibold text-white tracking-tight">
                  Ask the simulation analyst
                </h2>
                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/25 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-indigo-200 ring-1 ring-indigo-400/40">
                  <Sparkles className="h-3 w-3" aria-hidden />
                  Chat here
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Your main place to dig into this report — powered by the ReportAgent.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 sm:px-5 py-3 flex flex-wrap gap-2 border-b border-white/5 bg-black/10">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => send(q)}
            className="text-xs px-3 py-1.5 rounded-full border border-indigo-500/35 bg-indigo-500/10 text-slate-200 hover:bg-indigo-500/20 hover:border-indigo-400/50 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="h-80 overflow-y-auto px-4 sm:px-5 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white whitespace-pre-wrap break-words"
                  : "bg-white/10 text-slate-100 border border-white/10"
              }`}
            >
              {msg.role === "user" ? (
                msg.content
              ) : (
                <AssistantMarkdown content={msg.content} />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/10 border border-white/10 rounded-2xl px-4 py-2.5 text-sm text-slate-400">
              Analyzing...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-white/10 px-4 sm:px-5 py-3 flex gap-2 bg-black/15">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Type a question about your simulation…"
          className="flex-1 bg-white/5 border-white/15 text-slate-100 placeholder:text-slate-500 focus-visible:ring-indigo-500/40"
          disabled={loading}
        />
        <Button
          size="icon"
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="shrink-0 bg-indigo-600 hover:bg-indigo-500 text-white"
          aria-label="Send message"
        >
          <Send size={16} />
        </Button>
      </div>
    </section>
  );
}
