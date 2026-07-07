"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { tokens } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(tokens.access ? "/chat" : "/login");
  }, [router]);
  return null;
}
