import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI伯乐 · 探索星球",
  description: "四种探索方式，一颗属于每个孩子的成长星球。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
