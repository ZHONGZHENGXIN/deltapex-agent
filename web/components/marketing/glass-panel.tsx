"use client";

import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type GlassPanelProps = ComponentProps<"div">;

export default function GlassPanel({ className, ...props }: GlassPanelProps) {
  return (
    <div
      className={cn(
        "rounded-[24px] border border-[#ece5df] bg-white shadow-[0_28px_90px_rgba(15,23,42,0.08)]",
        className
      )}
      {...props}
    />
  );
}
