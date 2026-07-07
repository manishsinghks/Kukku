"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { tokens, apiJson } from "./api";

type AuthState = { user: string | null; loading: boolean; logout: () => void };
const Ctx = createContext<AuthState>({ user: null, loading: true, logout: () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let alive = true;
    (async () => {
      if (!tokens.access) {
        if (alive) setLoading(false);
        if (pathname !== "/login") router.replace("/login");
        return;
      }
      try {
        const me = await apiJson<{ user: string }>("/api/auth/me");
        if (alive) setUser(me.user);
      } catch {
        tokens.clear();
        if (pathname !== "/login") router.replace("/login");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [pathname, router]);

  const logout = () => {
    tokens.clear();
    setUser(null);
    router.replace("/login");
  };

  return <Ctx.Provider value={{ user, loading, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
