import { expect, test } from "@playwright/test";

/**
 * Sprint 4 smoke flow: app loads, auth pages render, API health reachable.
 * Extend with login → create ticket once demo seed credentials are stable.
 */
test.describe("DeskLite smoke", () => {
  test("home page loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
  });

  test("login page renders", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test("register page renders", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByLabel(/email/i)).toBeVisible();
  });

  test("API health endpoint responds", async ({ request }) => {
    const apiBase = process.env.API_URL ?? "http://localhost:8000";
    const res = await request.get(`${apiBase}/api/v1/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe("ok");
  });
});
