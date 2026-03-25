"use client";
import { motion } from "framer-motion";

interface Props {
  count: number;
  label: string;
}

export function AgentCounter({ count, label }: Props) {
  return (
    <div className="bg-muted rounded-lg p-4 text-center">
      <motion.div
        key={count}
        initial={{ scale: 1.2, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="text-2xl font-medium"
      >
        {count.toLocaleString()}
      </motion.div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}
