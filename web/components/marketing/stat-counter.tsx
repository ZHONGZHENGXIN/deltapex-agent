"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { animate, useInView, useReducedMotion } from "framer-motion";

type StatCounterProps = {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  locale?: string;
};

export default function StatCounter({
  label,
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  locale = "en",
}: StatCounterProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const shouldReduceMotion = useReducedMotion();
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    if (!inView) {
      return;
    }

    if (shouldReduceMotion) {
      setDisplayValue(value);
      return;
    }

    const controls = animate(0, value, {
      duration: 1.4,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => {
        const factor = 10 ** decimals;
        setDisplayValue(Math.round(latest * factor) / factor);
      },
    });

    return () => controls.stop();
  }, [decimals, inView, shouldReduceMotion, value]);

  const formatter = useMemo(
    () =>
      new Intl.NumberFormat(locale, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }),
    [decimals, locale]
  );

  return (
    <div
      ref={ref}
      className="rounded-lg border border-[#eee7e1] bg-white px-5 py-6 shadow-[0_18px_50px_rgba(15,23,42,0.04)]"
    >
      <div className="text-[2rem] font-semibold tracking-tight text-[#d32f2f] sm:text-[2.2rem]">
        {prefix}
        {formatter.format(displayValue)}
        {suffix}
      </div>
      <p className="mt-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{label}</p>
    </div>
  );
}
