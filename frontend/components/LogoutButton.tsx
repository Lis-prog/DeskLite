"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();

  async function handleLogout() {
    try {
      await api("/auth/logout", {
        method: "POST",
      });

      router.push("/login");
      router.refresh();
    } catch (error) {
      console.error("Logout failed", error);
    }
  }

  return (
    <Button type="button" onClick={handleLogout}>
      Logout
    </Button>
  );
}