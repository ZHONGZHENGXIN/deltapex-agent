"use client";

import { useMemo } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { BrainCircuit, FileText, Radar, Waypoints, ArrowUpRight } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { cn } from "@/lib/utils";
import StatCounter from "@/components/marketing/stat-counter";

type FeatureCardProps = {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  className?: string;
};

function FeatureCard({ title, description, icon: Icon, className }: FeatureCardProps) {
  return (
    <motion.article
      whileHover={{ y: -8, scale: 1.015 }}
      transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "group rounded-lg border border-[#ece7e2] bg-white p-6 shadow-[0_20px_60px_rgba(15,23,42,0.05)] transition-colors hover:border-[#d32f2f]/30 hover:shadow-[0_24px_70px_rgba(211,47,47,0.12)]",
        className
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex h-12 w-12 items-center justify-center rounded-md bg-[#fff4f2] text-[#d32f2f] ring-1 ring-[#f3d8d4] transition-transform duration-300 group-hover:scale-105">
          <Icon className="h-5 w-5" />
        </div>
        <div className="mt-10 space-y-3">
          <h3 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h3>
          <p className="text-sm leading-7 text-slate-600">{description}</p>
        </div>
      </div>
    </motion.article>
  );
}

export default function AboutSection() {
  const t = useTranslations();
  const locale = useLocale();
  const shouldReduceMotion = useReducedMotion();

  const features = useMemo(
    () => [
      { key: "orderFlow", icon: Radar },
      { key: "quantModels", icon: BrainCircuit },
      { key: "deepResearch", icon: FileText },
      { key: "executionFramework", icon: Waypoints },
    ],
    []
  );

  const stats = useMemo(
    () => [
      { label: t("marketing.about.stats.models"), value: 18, suffix: "+" },
      { label: t("marketing.about.stats.reports"), value: 240, suffix: "+" },
      { label: t("marketing.about.stats.sessions"), value: 3200, suffix: "+" },
      { label: t("marketing.about.stats.coverage"), value: 24, suffix: "/5" },
    ],
    [t]
  );

  const containerVariants: Variants | undefined = shouldReduceMotion
    ? undefined
    : {
        hidden: { opacity: 0 },
        show: {
          opacity: 1,
          transition: {
            staggerChildren: 0.15,
            delayChildren: 0.06,
          },
        },
      };

  const itemVariants: Variants | undefined = shouldReduceMotion
    ? undefined
    : {
        hidden: { opacity: 0, y: 28 },
        show: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.72, ease: [0.16, 1, 0.3, 1] },
        },
      };

  return (
    <section
      id="about"
      className="relative overflow-hidden border-t border-[#efe8e2] bg-[linear-gradient(180deg,#fcfbfa_0%,#f8f6f4_45%,#ffffff_100%)] py-24 sm:py-28"
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#d32f2f]/30 to-transparent" />
      <div className="pointer-events-none absolute left-0 top-24 h-64 w-64 rounded-full bg-[#d32f2f]/6 blur-3xl" />
      <div className="pointer-events-none absolute bottom-10 right-0 h-72 w-72 rounded-full bg-[#b71c1c]/6 blur-3xl" />

      <div className="relative mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={shouldReduceMotion ? false : "hidden"}
          whileInView={shouldReduceMotion ? undefined : "show"}
          viewport={{ once: true, amount: 0.2 }}
          variants={containerVariants}
          className="space-y-14"
        >
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <motion.div variants={itemVariants} className="max-w-xl">
              <div className="inline-flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.32em] text-[#d32f2f]">
                <span className="h-px w-10 bg-[#d32f2f]" />
                {t("marketing.about.eyebrow")}
              </div>
              <h2 className="mt-6 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
                {t("marketing.about.title")}
              </h2>
              <p className="mt-6 text-base leading-8 text-slate-600">{t("marketing.about.description")}</p>

              <motion.div
                variants={itemVariants}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                className="mt-10 rounded-lg border border-[#ede7e1] bg-white p-7 shadow-[0_24px_70px_rgba(15,23,42,0.06)]"
              >
                <div className="flex items-start justify-between gap-6">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#d32f2f]">
                      Deltapex Method
                    </p>
                    <p className="mt-4 text-lg font-medium leading-8 text-slate-900">
                      {locale === "zh"
                        ? "把研究、订单流判断与执行纪律放进同一套工作流，减少信息切换，提升临场决策质量。"
                        : "Bring research, order flow context, and execution discipline into one workflow before risk is deployed."}
                    </p>
                  </div>
                  <div className="hidden h-11 w-11 items-center justify-center rounded-full bg-[#fff4f2] text-[#d32f2f] sm:flex">
                    <ArrowUpRight className="h-5 w-5" />
                  </div>
                </div>
              </motion.div>
            </motion.div>

            <motion.div variants={itemVariants} className="grid gap-5 sm:grid-cols-2">
              {features.map(({ key, icon }) => (
                <FeatureCard
                  key={key}
                  icon={icon}
                  title={t(`marketing.about.cards.${key}.title`)}
                  description={t(`marketing.about.cards.${key}.description`)}
                />
              ))}
            </motion.div>
          </div>

          <motion.div
            variants={itemVariants}
            className="grid gap-4 rounded-lg border border-[#f0e8e3] bg-[#fffdfc] p-4 shadow-[0_18px_55px_rgba(15,23,42,0.04)] sm:grid-cols-2 sm:p-5 xl:grid-cols-4"
          >
            {stats.map((stat) => (
              <StatCounter
                key={stat.label}
                label={stat.label}
                value={stat.value}
                suffix={stat.suffix}
                locale={locale}
              />
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
