"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface Crumb {
  label: string;
  href?: string;
}

function useBreadcrumbs(): Crumb[] {
  const pathname = usePathname();

  if (pathname === "/") {
    return [{ label: "Dashboard" }];
  }

  if (pathname === "/analysis/new") {
    return [
      { label: "Dashboard", href: "/" },
      { label: "New Analysis" },
    ];
  }

  if (pathname === "/reports") {
    return [
      { label: "Dashboard", href: "/" },
      { label: "Reports" },
    ];
  }

  if (pathname.startsWith("/analysis/") && pathname !== "/analysis/new") {
    return [
      { label: "Dashboard", href: "/" },
      { label: "Reports", href: "/reports" },
      { label: "Analysis" },
    ];
  }

  return [{ label: "Dashboard" }];
}

export function TopBar() {
  const pathname = usePathname();
  const crumbs = useBreadcrumbs();
  const showNewButton = pathname !== "/analysis/new";

  return (
    <header
      style={{
        height: 52,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingLeft: 24,
        paddingRight: 24,
        backgroundColor: "var(--bg-surface)",
        borderBottom: "1px solid var(--border)",
        position: "sticky",
        top: 0,
        zIndex: 30,
      }}
    >
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb">
        <ol
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            listStyle: "none",
          }}
        >
          {crumbs.map((crumb, i) => (
            <li
              key={i}
              style={{ display: "flex", alignItems: "center", gap: 4 }}
            >
              {i > 0 && (
                <ChevronRight
                  size={12}
                  style={{ color: "var(--text-tertiary)", flexShrink: 0 }}
                />
              )}
              {crumb.href ? (
                <Link
                  href={crumb.href}
                  style={{
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    textDecoration: "none",
                    transition: "color var(--transition-fast)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLAnchorElement).style.color =
                      "var(--text-primary)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLAnchorElement).style.color =
                      "var(--text-secondary)";
                  }}
                >
                  {crumb.label}
                </Link>
              ) : (
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: "var(--text-primary)",
                  }}
                >
                  {crumb.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>

      {/* Actions */}
      {showNewButton && (
        <Link href="/analysis/new">
          <Button variant="primary" size="sm" leftIcon={<Plus size={14} />}>
            New Analysis
          </Button>
        </Link>
      )}
    </header>
  );
}
