import { expect, test } from "@playwright/test";

test("registration has the required order, labels, links, and accessible validation", async ({ page }) => {
  await page.goto("/register");
  await expect(page.getByRole("heading", { level: 1, name: "Create your workspace" })).toBeVisible();
  const labels = await page.locator("form label").allTextContents();
  expect(labels.join("|")).toMatch(/Full name[\s\S]*Organization name[\s\S]*Work email[\s\S]*Password[\s\S]*Confirm password[\s\S]*Terms of Service/);
  await expect(page.getByRole("button", { name: "Create Free Workspace" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Terms of Service" })).toHaveAttribute("href", "/terms");
  await expect(page.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute("href", "/privacy");
  await page.getByRole("button", { name: "Create Free Workspace" }).click();
  await expect(page.getByText("Full name is required.")).toBeVisible();
  await expect(page.locator("#full_name")).toBeFocused();
});

test("registration converts a browser network failure to a friendly message", async ({ page }) => {
  await page.route("**/auth/register", (route) => route.abort("failed"));
  await page.goto("/register");
  await page.locator("#full_name").fill("Test Owner");
  await page.locator("#organization_name").fill("Test Organization");
  await page.locator("#email").fill("owner@example.com");
  await page.locator("#password").fill("password123");
  await page.locator("#confirm_password").fill("password123");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create Free Workspace" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Novoriq could not reach the server" })).toBeVisible();
  await expect(page.getByText(/NetworkError|Failed to fetch|AxiosError/)).toHaveCount(0);
});

test("login uses friendly invalid-credentials handling", async ({ page }) => {
  await page.route("**/auth/login", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "raw backend detail" }) }));
  await page.goto("/login");
  await expect(page.getByRole("heading", { level: 1, name: "Welcome back" })).toBeVisible();
  await page.locator("#email").fill("owner@example.com");
  await page.locator("#password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Email or password is incorrect." })).toBeVisible();
});

test("registration does not overflow on a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/register");
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client);
});
