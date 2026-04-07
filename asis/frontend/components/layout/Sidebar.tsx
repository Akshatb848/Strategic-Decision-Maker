"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { slideRight, staggerContainer } from "@/lib/animations";
import { useAuth } from "@/contexts/AuthContext";
import {
  LayoutDashboard,
  PlusCircle,
  FileBarChart2,
  Zap,
  LogOut,
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

function userInitials(user: { email: string; full_name?: string | null }): string {
  if (user.full_name) {
    const parts = user.full_name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  return user.email.slice(0, 2).toUpperCase();
}

function roleLabel(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

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

      {/* Bottom: User profile + logout */}
      <div
        style={{
          padding: "12px 8px",
          borderTop: "1px solid var(--border)",
        }}
      >
        {user && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 9,
              padding: "8px 10px",
              borderRadius: "var(--radius-md)",
              marginBottom: 4,
              backgroundColor: "var(--bg-elevated)",
            }}
          >
            {/* Avatar */}
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: "50%",
                backgroundColor: "var(--accent)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: 11,
                fontWeight: 700,
                color: "white",
                letterSpacing: "0.02em",
              }}
            >
              {userInitials(user)}
            </div>

            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {user.full_name ?? user.email.split("@")[0]}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-tertiary)",
                  marginTop: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    padding: "1px 5px",
                    borderRadius: 3,
                    backgroundColor: "var(--accent-dim)",
                    color: "var(--accent)",
                    fontWeight: 600,
                    fontSize: 9,
                    letterSpacing: "0.03em",
                    textTransform: "uppercase",
                  }}
                >
                  {roleLabel(user.role)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Logout button */}
        <button
          type="button"
          onClick={handleLogout}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "7px 10px",
            borderRadius: "var(--radius-md)",
            width: "100%",
            fontSize: 13,
            color: "var(--text-tertiary)",
            background: "none",
            border: "none",
            cursor: "pointer",
            transition: "all var(--transition-fast)",
            textAlign: "left",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(239,68,68,0.08)";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--danger)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = "transparent";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--text-tertiary)";
          }}
        >
          <LogOut size={15} style={{ flexShrink: 0 }} />
          <span>Sign out</span>
        </button>
      </div>
    </nav>
  );
}
