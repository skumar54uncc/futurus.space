import { ExternalLink } from "lucide-react";
import type { Citation } from "@/lib/types";

interface Props {
  citations: Citation[];
}

export function CitationsList({ citations }: Props) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <h2 className="text-xl font-semibold mb-1 text-[--text-primary]">Sources</h2>
      <p className="text-sm text-[--text-tertiary] mb-5">
        Real-world industry data retrieved to ground this report&apos;s benchmarks and risk assessments
      </p>

      <ol className="space-y-3">
        {citations.map((c) => (
          <li key={c.id} className="flex gap-3 items-start">
            <span className="text-xs font-mono text-[--text-tertiary] mt-0.5 shrink-0 w-5 text-right">
              [{c.id}]
            </span>
            <div className="min-w-0">
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-[--text-primary] hover:text-white transition-colors group"
              >
                <span className="truncate">{c.title || c.source}</span>
                <ExternalLink className="h-3 w-3 shrink-0 text-[--text-tertiary] group-hover:text-white transition-colors" />
              </a>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-[--text-tertiary]">{c.source}</span>
                {c.year && (
                  <>
                    <span className="text-xs text-[--border-default]">·</span>
                    <span className="text-xs text-[--text-tertiary]">{c.year}</span>
                  </>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
