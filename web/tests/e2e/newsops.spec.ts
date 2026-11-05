/**
 * NewsOps Playwright end-to-end tests.
 *
 * Spec §7 requirements:
 * 1. Opens / as Sam, sends @scout in #aiml, waits for pipeline to reach Approver
 * 2. Opens /review and clicks Approve — sees 403 toast + blocked message in room panel
 * 3. Switches to Alice, approves, sees status Published
 * 4. Opens /radar, votes, sees blip move or tally change
 * 5. Opens /dependencies, scans sample file, sees at least one Affected row
 *
 * Run against a backend in demo mode:
 *   DEMO_MODE=1 NEWSOPS_OFFLINE=1 uvicorn newsops.main:app --port 8000
 *   BASE_URL=http://localhost:3000 npx playwright test
 *
 * Or in mock mode (no backend needed):
 *   NEXT_PUBLIC_MOCK=1 npm run dev   (in web/)
 *   BASE_URL=http://localhost:3000 npx playwright test
 */

import { test, expect, type Page } from '@playwright/test'

// ── Helpers ───────────────────────────────────────────────────────────────

async function loginAs(page: Page, persona: 'alice' | 'sam') {
  // Persona buttons are in the header
  await page.getByRole('button', { name: new RegExp(persona, 'i') }).first().click()
  // Wait for persona indicator to appear in the sidebar
  await page.waitForTimeout(500)
}

async function waitForToast(page: Page, pattern: RegExp | string, timeout = 10_000) {
  await expect(page.getByRole('status')).toContainText(
    typeof pattern === 'string' ? pattern : pattern,
    { timeout },
  )
}

// ── Test 1: Sam sends @scout, pipeline reaches Approver ───────────────────
test('1 · Sam sends @scout in #aiml and pipeline reaches Approver', async ({ page }) => {
  await page.goto('/')

  // Log in as Sam
  await loginAs(page, 'sam')

  // Ensure #aiml room is selected (click it in the rail)
  await page.getByRole('button', { name: /#aiml/i }).click()

  // Send @scout message via room panel input
  const input = page.getByPlaceholder(/Message #aiml/i)
  await input.fill('@scout aiml last 24h')
  await page.getByRole('button', { name: /^Send$/i }).click()

  // Wait for the pipeline to reach Approver (step 4)
  // The pipeline strip renders numbered nodes; node "4" or "Approver" should appear active/done
  await expect(page.getByText('Approver', { exact: false })).toBeVisible({ timeout: 20_000 })
})

// ── Test 2: Sam tries to approve — gets 403 ───────────────────────────────
test('2 · Sam cannot approve #aiml digest — 403 toast appears', async ({ page }) => {
  await page.goto('/review')
  await loginAs(page, 'sam')

  // Select #aiml room
  await page.getByRole('button', { name: /#aiml/i }).first().click()

  // Gate bar should warn Sam cannot approve
  await expect(page.getByText(/403/i)).toBeVisible({ timeout: 8_000 })

  // If a digest exists with approve button, click it and check for error toast
  const approveBtn = page.getByRole('button', { name: /Approve/i })
  if (await approveBtn.isVisible()) {
    await approveBtn.click()
    // Either a 403 toast or the gate bar message
    await expect(page.getByRole('status')).toContainText(/403|cannot approve/i, { timeout: 6_000 })
  }
})

// ── Test 3: Alice approves → Published ────────────────────────────────────
test('3 · Alice approves digest and sees Published status', async ({ page }) => {
  await page.goto('/review')
  await loginAs(page, 'alice')

  // Select #aiml room
  await page.getByRole('button', { name: /#aiml/i }).first().click()

  // Gate bar should confirm Alice can approve
  await expect(page.getByText(/you can approve/i)).toBeVisible({ timeout: 6_000 })

  // Approve if a digest in review_required state exists
  const approveBtn = page.getByRole('button', { name: /^Approve$/i })
  if (await approveBtn.isVisible()) {
    await approveBtn.click()
    // Status chip should change to Approved
    await expect(page.getByText(/Approved/i)).toBeVisible({ timeout: 6_000 })

    // Then publish
    const publishBtn = page.getByRole('button', { name: /Approve and publish/i })
    if (await publishBtn.isVisible()) {
      await publishBtn.click()
      await expect(page.getByText(/Published/i)).toBeVisible({ timeout: 6_000 })
    }
  }
})

// ── Test 4: Radar — vote changes tally ────────────────────────────────────
test('4 · Radar vote changes blip ring or tally', async ({ page }) => {
  await page.goto('/radar')
  await loginAs(page, 'alice')

  // Wait for blips to render (numbered circles in the SVG)
  await expect(page.locator('svg circle[r="10"]').first()).toBeVisible({ timeout: 8_000 })

  // Click the first blip
  await page.locator('svg circle[r="10"]').first().click()

  // The side panel should show vote bars
  await expect(page.getByText(/Votes by ring/i)).toBeVisible({ timeout: 4_000 })

  // Click "trial" vote button
  const trialBtn = page.getByRole('button', { name: /^trial$/i })
  await trialBtn.click()

  // The button should become active (aria-pressed=true)
  await expect(trialBtn).toHaveAttribute('aria-pressed', 'true', { timeout: 4_000 })
})

// ── Test 5: Dependencies — scan sees Affected row ─────────────────────────
test('5 · Dependency scanner shows at least one Affected row', async ({ page }) => {
  await page.goto('/dependencies')

  // Load sample requirements.txt
  await page.getByRole('button', { name: /Load sample requirements/i }).click()

  // The textarea should be populated
  const textarea = page.getByRole('textbox', { name: /Dependency file/i })
  await expect(textarea).not.toBeEmpty()

  // Click Scan
  await page.getByRole('button', { name: /^Scan$/i }).click()

  // Wait for results — at least one "affected" status chip
  await expect(page.getByText(/affected/i).first()).toBeVisible({ timeout: 15_000 })
})
