import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GeoViz · 合成数据演示",
  description: "交互式地质样品地图与数据查询平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="h-full">
        {children}
        <div className="fixed bottom-3 left-1/2 -translate-x-1/2 z-[1200] rounded-full border border-black/10 bg-white/95 px-4 py-1.5 text-xs text-slate-600 shadow-sm pointer-events-none">
          Synthetic demo · 合成数据演示
        </div>
      </body>
    </html>
  );
}
