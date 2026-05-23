import { test, expect } from "@playwright/test";

test.describe("Azure · Resource Groups", () => {
  test("list page renders", async ({ page }) => {
    await page.goto("/azure/resource-groups");
    await expect(page.getByText(/Azure · Resource Groups/)).toBeVisible();
  });
});
