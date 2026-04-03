import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en" className="dark">
      <body className="bg-surface text-white antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
