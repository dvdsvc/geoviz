"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Database, Globe, Clock, Microscope } from "lucide-react";
import { Sample } from "@/types";

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

interface KpiCardsProps {
  samples: Sample[];
}

export default function KpiCards({ samples }: KpiCardsProps) {
  const stats = useMemo(() => {
    const ages = samples.filter((s) => s.ageMa != null).map((s) => s.ageMa!);
    const regions = new Set(samples.map((s) => s.region)).size;
    const techniques = samples.reduce<Record<string, number>>((acc, s) => {
      const t = s.technique || "Unknown";
      acc[t] = (acc[t] || 0) + 1;
      return acc;
    }, {});
    const topTechnique = Object.entries(techniques).sort((a, b) => b[1] - a[1])[0]?.[0] || "—";

    return [
      {
        label: "Samples",
        value: samples.length.toString(),
        icon: Database,
        accent: "#007aff",
      },
      {
        label: "Regions",
        value: regions.toString(),
        icon: Globe,
        accent: "#2a9d8f",
      },
      {
        label: "Age Span",
        value: ages.length > 0
          ? `${Math.min(...ages).toFixed(1)} – ${Math.max(...ages).toFixed(1)} Ma`
          : "—",
        icon: Clock,
        accent: "#e63946",
      },
      {
        label: "Top Method",
        value: topTechnique,
        icon: Microscope,
        accent: "#812b92",
      },
    ];
  }, [samples]);

  return (
    <div className="flex gap-2">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
              delay: 0.2 + i * 0.08,
            }}
            className="ios-card px-3.5 py-2.5 min-w-[110px]"
          >
            <div className="flex items-center gap-1.5 mb-1">
              <Icon className="w-3 h-3" style={{ color: stat.accent }} />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-tertiary-label">
                {stat.label}
              </span>
            </div>
            <p className="text-[17px] font-bold text-foreground leading-tight">
              {stat.value}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}
