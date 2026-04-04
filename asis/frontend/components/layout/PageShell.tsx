"use client";

import { type ReactNode } from "react";
import { motion } from "framer-motion";
import { fadeUp } from "@/lib/animations";

interface PageShellProps {
  children: ReactNode;
}

export function PageShell({ children }: PageShellProps) {
  return (
    <motion.main
      initial={fadeUp.initial}
      animate={fadeUp.animate}
      transition={fadeUp.transition}
      style={{
        flex: 1,
        minHeight: "100vh",
        overflowY: "auto",
      }}
    >
      {children}
    </motion.main>
  );
}
