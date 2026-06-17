"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

type LogoutButtonProps = {
  onLoggedOut?: () => void;
};

export function LogoutButton({ onLoggedOut }: LogoutButtonProps) {
  const router = useRouter();

  async function handleLogout() {
    try {
      await api<void>("/auth/logout", {
        method: "POST",
      });

      onLoggedOut?.();
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
