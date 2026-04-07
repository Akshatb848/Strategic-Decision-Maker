"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { PageShell } from "@/components/layout/PageShell";

// These routes are fully public — no shell, no auth check
const PUBLIC_ROUTES = ["/login", "/register"];

// The root "/" is semi-public: it renders itself based on auth state
// (welcome page for guests, dashboard content for logged-in users)
const SEMI_PUBLIC_ROUTES = ["/"];

function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();

  const isPublicRoute = PUBLIC_ROUTES.includes(pathname);
  const isSemiPublicRoute = SEMI_PUBLIC_ROUTES.includes(pathname);

  useEffect(() => {
    // Only hard-redirect from fully protected routes
    if (!isPublicRoute && !isSemiPublicRoute && !loading && !user) {
      router.replace("/login");
    }
  }, [isPublicRoute, isSemiPublicRoute, loading, user, router]);

  // Auth pages — bare page, no shell
  if (isPublicRoute) {
    return <>{children}</>;
  }

  // Root "/" — render without shell (the page itself decides what to show)
  if (isSemiPublicRoute) {
    if (loading) {
      return (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-base)" }}>
          <div style={{ width: 24, height: 24, borderRadius: "50%", border: "2px solid var(--border)", borderTopColor: "var(--accent)", animation: "spin 0.8s linear infinite" }} />
        </div>
      );
    }

    // Not authenticated → full-screen welcome (no sidebar)
    if (!user) {
      return <>{children}</>;
    }

    // Authenticated → wrap in full shell
    return (
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar />
        <div style={{ marginLeft: 220, flex: 1, display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--bg-base)" }}>
          <TopBar />
          <PageShell>{children}</PageShell>
        </div>
      </div>
    );
  }

  // Protected routes — waiting for auth
  if (loading || !user) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-base)" }}>
        <div style={{ width: 24, height: 24, borderRadius: "50%", border: "2px solid var(--border)", borderTopColor: "var(--accent)", animation: "spin 0.8s linear infinite" }} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ marginLeft: 220, flex: 1, display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--bg-base)" }}>
        <TopBar />
        <PageShell>{children}</PageShell>
      </div>
    </div>
  );
}

export function ClientRootLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <AppShell>{children}</AppShell>
    </AuthProvider>
  );
}
