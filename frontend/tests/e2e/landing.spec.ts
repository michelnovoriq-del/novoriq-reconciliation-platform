import { expect, test } from "@playwright/test";

test("landing page shows primary workflow", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /controlled reconciliation workflows/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /create account/i }).first()).toBeVisible();
  await expect(page.getByText("Drop files")).toBeVisible();
  await expect(page.getByText("Map columns")).toBeVisible();
});

test("auth pages render forms", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /welcome back/i })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();

  await page.goto("/register");
  await expect(page.getByRole("heading", { name: /create your workspace/i })).toBeVisible();
  await expect(page.getByLabel("Organization")).toBeVisible();
});
