import { expect, test } from "@playwright/test";

test("homepage has primary SEO content and calls to action", async ({ page }) => {
  const response=await page.goto("/"); expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: /reconcile messy financial files/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Start Free Forever" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /see how it works/i })).toBeVisible();
});

test("main product navigation resolves", async ({ page }) => {
  for(const [path,heading] of [["/features","structured reconciliation workflow"],["/how-it-works","messy financial exports"],["/pricing","reconciliation capacity"]]){
    const response=await page.goto(path); expect(response?.status()).toBe(200); await expect(page.getByRole("heading",{level:1,name:new RegExp(heading)})).toBeVisible();
  }
});

test("use cases and trust pages have unique headings", async ({ page }) => {
  const pages=[["/use-cases/bookkeepers","workflow for bookkeepers"],["/use-cases/accounting-firms","small accounting firms"],["/use-cases/ecommerce-reconciliation","ecommerce payouts"],["/security","security controls"],["/data-retention","retention and deletion"],["/privacy","Privacy Policy"],["/terms","Terms of Service"],["/support","How can we help"]];
  for(const [path,heading] of pages){await page.goto(path);await expect(page.getByRole("heading",{level:1,name:new RegExp(heading,"i")})).toBeVisible();}
});

test("pricing preserves required prices", async ({ page }) => {await page.goto("/pricing");for(const value of ["$0","$279","$499"])await expect(page.getByText(value,{exact:true})).toBeVisible();});
test("sitemap and robots render", async ({ request }) => {expect((await request.get("/sitemap.xml")).status()).toBe(200);expect((await request.get("/robots.txt")).status()).toBe(200);});
test("private and auth routes do not expose public customer data", async ({ page }) => {await page.goto("/login");await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content",/noindex/);await page.goto("/dashboard");await expect(page).toHaveURL(/\/login/);});

test("auth pages render forms", async ({ page }) => {await page.goto("/login");await expect(page.getByRole("heading",{name:/welcome back/i})).toBeVisible();await page.goto("/register");await expect(page.getByRole("heading",{name:/create your workspace/i})).toBeVisible();});
