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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700;900&family=ZCOOL+KuaiLe&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
