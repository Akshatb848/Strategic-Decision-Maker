"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { slideRight, staggerContainer } from "@/lib/animations";
import {
  LayoutDashboard,
  PlusCircle,
  FileBarChart2,
  Settings,
  Zap,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/",
    icon: <LayoutDashboard size={16} />,
  },
  {
    label: "New Analysis",
    href: "/analysis/new",
    icon: <PlusCircle size={16} />,
  },
  {
    label: "Reports",
    href: "/reports",
    icon: <FileBarChart2 size={16} />,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main navigation"
      style={{
        width: 220,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "fixed",
        left: 0,
        top: 0,
        backgroundColor: "var(--bg-surface)",
        borderRight: "1px solid var(--border)",
        overflowY: "auto",
        zIndex: 40,
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "20px 16px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Zap size={16} color="white" />
          </div>
          <div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "var(--text-primary)",
                letterSpacing: "-0.01em",
              }}
            >
              ASIS
            </div>
            <div
              style={{
                fontSize: 10,
                color: "var(--text-tertiary)",
                marginTop: 1,
              }}
            >
              v3.0
            </div>
          </div>
        </div>
        <div
          style={{
            marginTop: 8,
            fontSize: 10,
            color: "var(--text-tertiary)",
            lineHeight: 1.4,
          }}
        >
          Strategic Intelligence
        </div>
      </div>

      {/* Navigation */}
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        style={{ padding: "12px 8px", flex: 1 }}
      >
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <motion.div key={item.href} variants={slideRight}>
              <Link
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 10px",
                  borderRadius: "var(--radius-md)",
                  marginBottom: 2,
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                  backgroundColor: isActive ? "var(--bg-elevated)" : "transparent",
                  borderLeft: isActive
                    ? "2px solid var(--accent)"
                    : "2px solid transparent",
                  paddingLeft: isActive ? 8 : 10,
                  transition: "all var(--transition-fast)",
                  textDecoration: "none",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                      "var(--bg-elevated)";
                    (e.currentTarget as HTMLAnchorElement).style.color =
                      "var(--text-primary)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                      "transparent";
                    (e.currentTarget as HTMLAnchorElement).style.color =
                      "var(--text-secondary)";
                  }
                }}
              >
                <span style={{ flexShrink: 0, opacity: isActive ? 1 : 0.7 }}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </Link>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Bottom: Settings */}
      <div
        style={{
          padding: "12px 8px",
          borderTop: "1px solid var(--border)",
        }}
      >
        <Link
          href="/settings"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 10px",
            borderRadius: "var(--radius-md)",
            fontSize: 13,
            color: "var(--text-tertiary)",
            textDecoration: "none",
            transition: "all var(--transition-fast)",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
              "var(--bg-elevated)";
            (e.currentTarget as HTMLAnchorElement).style.color =
              "var(--text-secondary)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
              "transparent";
            (e.currentTarget as HTMLAnchorElement).style.color =
              "var(--text-tertiary)";
          }}
        >
          <Settings size={16} />
          <span>Settings</span>
        </Link>
      </div>
    </nav>
  );
}
