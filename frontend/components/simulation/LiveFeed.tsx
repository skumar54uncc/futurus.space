"use client";
import { LiveEvent } from "@/lib/types";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const EVENT_COLORS: Record<string, string> = {
  adopted: "text-green-600 bg-green-50",
  churned: "text-red-600 bg-red-50",
  referred: "text-blue-600 bg-blue-50",
  rejected: "text-gray-500 bg-gray-50",
};

const EVENT_LABELS: Record<string, string> = {
  adopted: "Adopted",
  churned: "Churned",
  referred: "Referred",
  rejected: "Rejected",
};

export function LiveFeed({ events }: { events: LiveEvent[] }) {
  return (
    <div className="divide-y max-h-80 overflow-y-auto">
      <AnimatePresence initial={false}>
        {events.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">
            Waiting for agent activity...
          </div>
        )}
        {events.map((event, i) => (
          <motion.div
            key={`${event.agent_name}-${i}`}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex items-start gap-3 px-4 py-2.5"
          >
            <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 mt-0.5", EVENT_COLORS[event.event_type] || "text-gray-600 bg-gray-100")}>
              {EVENT_LABELS[event.event_type] || event.event_type}
            </span>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-foreground">{event.agent_name}</span>
              <span className="text-xs text-muted-foreground ml-2">{event.segment}</span>
              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{event.description}</p>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
