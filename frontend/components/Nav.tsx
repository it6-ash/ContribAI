"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null));
  }, [pathname]);

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-background/85 backdrop-blur">
      <nav className="mx-auto flex h-16 max-w-[1400px] items-center gap-6 px-6">
        <Link href={user ? "/dashboard" : "/"} className="font-semibold tracking-tight">
          Contrib<span className="text-accent">AI</span>
        </Link>

        {user ? (
          <div className="flex items-center gap-1">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded px-2.5 py-1.5 text-[13.5px] transition-colors ${
                  pathname === link.href
                    ? "text-foreground"
                    : "text-muted hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        ) : null}

        <div className="ml-auto flex items-center gap-3">
          {user ? (
            <>
              <span className="font-mono text-[12px] text-muted">
                @{user.username}
                {user.is_demo ? " · demo" : ""}
              </span>
              <button
                onClick={async () => {
                  await api.logout();
                  router.push("/");
                }}
                className="text-[13px] text-muted hover:text-foreground"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/onboarding" className="text-[13.5px] text-muted hover:text-foreground">
              Get started
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
