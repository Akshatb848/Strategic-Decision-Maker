import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { PageShell } from "@/components/layout/PageShell";

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
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <Sidebar />
          {/* Main content offset by sidebar width */}
          <div
            style={{
              marginLeft: 220,
              flex: 1,
              display: "flex",
              flexDirection: "column",
              minHeight: "100vh",
              background: "var(--bg-base)",
            }}
          >
            <TopBar />
            <PageShell>{children}</PageShell>
          </div>
        </div>
      </body>
    </html>
  );
}
