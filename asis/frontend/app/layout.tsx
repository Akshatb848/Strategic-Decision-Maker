import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClientRootLayout } from "@/components/ClientRootLayout";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ASIS — Autonomous Strategic Intelligence System",
  description:
    "Board-level strategic decision intelligence powered by multi-agent AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        style={{
          background: "var(--bg-base)",
          color: "var(--text-primary)",
          minHeight: "100vh",
          WebkitFontSmoothing: "antialiased",
        }}
      >
        <ClientRootLayout>{children}</ClientRootLayout>
      </body>
    </html>
  );
}
