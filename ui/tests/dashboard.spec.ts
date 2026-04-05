import { test, expect } from '@playwright/test';

// Test the base authentication flow and visual dashboard mounting
test.describe('Dashboard Authentication & Navigation', () => {
  test('Bypasses auth if no pin is provided, loading the default game interface', async ({ page }) => {
    // Navigate to the frontpage
    await page.goto('/');

    // Check that we aren't seeing the lock screen (assuming tests run without VITE_DASHBOARD_PIN set in pipeline initially)
    const secureHeading = page.getByText('SECURE ACCESS');
    await expect(secureHeading).toHaveCount(0);

    // Verify the primary Navigation tabs exist
    await expect(page.getByText('Live Overview')).toBeVisible();
    await expect(page.getByText('Squad Builder')).toBeVisible();
    await expect(page.getByText('Process Map')).toBeVisible();
    await expect(page.getByText('History')).toBeVisible();
  });

  test('Settings Gear toggles the settings panel', async ({ page }) => {
    await page.goto('/');
    
    // Target the settings cog (represented in the header)
    const settingsButton = page.locator('header').locator('svg.lucide-settings').first();
    await settingsButton.click();

    // Verify that the settings modal popped up via scale-in
    await expect(page.getByText('System Preferences')).toBeVisible();
    await expect(page.getByText('Security')).toBeVisible();
    await expect(page.getByText('Dashboard PIN Protection')).toBeVisible();

    // Close the settings
    await page.locator('.lucide-x').first().click();
    await expect(page.getByText('System Preferences')).not.toBeVisible();
  });

  test('Tab navigation effectively switches DOM content', async ({ page }) => {
    await page.goto('/');

    // Navigate to Squad Builder
    await page.getByText('Squad Builder').click();
    await expect(page.getByText('AI Squad Builder')).toBeVisible();
    
    // Navigate to Process Map
    await page.getByText('Process Map').click();
    await expect(page.getByText('NO SQUAD SELECTED')).toBeVisible();

    // Navigate to History
    await page.getByText('History').click();
    await expect(page.getByText('NO SQUAD SELECTED')).toBeVisible();
  });
});
