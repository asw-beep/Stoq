"use client";

import {
  LineChart,
  LogOut,
  Shield,
  TrendingUp,
  User as UserIcon,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useLogout, useMe } from "@/lib/queries";

const NAV = [
  { href: "/", label: "Market", icon: LineChart },
  { href: "/portfolios", label: "Portfolios", icon: Wallet },
  { href: "/account", label: "Account", icon: UserIcon },
];

// Shown only to admins (the backend still enforces the role on every request).
const ADMIN_NAV = [{ href: "/admin/users", label: "Users", icon: Shield }];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useLogout();
  const { data: me } = useMe();
  const [query, setQuery] = useState("");

  const nav = me?.role === "admin" ? [...NAV, ...ADMIN_NAV] : NAV;

  function isActive(href: string) {
    return href === "/" ? pathname === "/" : pathname.startsWith(href);
  }

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    const symbol = query.trim().toUpperCase();
    if (symbol) {
      router.push(`/stocks/${encodeURIComponent(symbol)}`);
      setQuery("");
    }
  }

  async function onLogout() {
    await logout.mutateAsync();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="flex min-h-screen flex-1">
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-sidebar md:flex">
        <div className="flex h-14 items-center gap-2 border-b px-5">
          <TrendingUp className="size-5 text-foreground" />
          <span className="font-heading text-xl tracking-tight">Stoq</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive(href)
                  ? "bg-secondary text-secondary-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur">
          <form onSubmit={onSearch} className="flex-1 md:max-w-xs">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search symbol (e.g. AAPL)…"
              aria-label="Search stock symbol"
            />
          </form>
          <div className="flex-1" />
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="outline" size="sm" className="gap-2" />}
            >
              <UserIcon className="size-4 shrink-0" />
              <span className="hidden whitespace-nowrap sm:inline">
                {me?.email ?? "Account"}
              </span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuGroup>
                <DropdownMenuLabel className="break-all">
                  {me?.email ?? "Signed in"}
                </DropdownMenuLabel>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/account")}>
                <UserIcon className="size-4" /> Account
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onLogout} disabled={logout.isPending}>
                <LogOut className="size-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* mobile nav */}
        <nav className="flex gap-1 border-b p-2 md:hidden">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-md px-2 py-2 text-sm font-medium",
                isActive(href)
                  ? "bg-secondary text-secondary-foreground"
                  : "text-muted-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
        </nav>

        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
