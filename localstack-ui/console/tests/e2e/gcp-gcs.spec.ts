import { test, expect } from "@playwright/test";

test.describe("GCP · Cloud Storage", () => {
  test("list page renders", async ({ page }) => {
    await page.goto("/gcp/storage");
    await expect(page.getByText(/GCP · Cloud Storage/)).toBeVisible();
  });
});
