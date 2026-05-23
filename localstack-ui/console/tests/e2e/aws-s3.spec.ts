import { test, expect } from "@playwright/test";

test.describe("AWS · S3", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/aws/s3");
  });

  test("list page renders", async ({ page }) => {
    await expect(page.getByText(/S3 · Buckets/)).toBeVisible();
  });

  test("create + delete bucket round-trip", async ({ page }) => {
    const name = `e2e-bucket-${Date.now()}`;
    await page.getByPlaceholder("my-bucket").fill(name);
    await page.getByRole("button", { name: /^Create$/ }).click();
    await expect(page.getByText(name)).toBeVisible();
    await page
      .getByRole("row", { name: new RegExp(name) })
      .getByRole("button", { name: "Delete" })
      .click();
    await expect(page.getByText(name)).toBeHidden({ timeout: 5000 });
  });
});
