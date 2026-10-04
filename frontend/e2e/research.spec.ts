import { expect, test } from '@playwright/test'
import { existsSync } from 'node:fs'
test.skip(
  !existsSync('public/data/manifest.json'),
  'Local preserved artifacts must be exported; no network research acquisition.',
)
test('real artifacts render every view without browser errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'DipSignal V1', exact: true })).toBeVisible()
  await expect(
    page.getByText('Registered breadth criterion: failed.', { exact: true }),
  ).toBeVisible()
  await page.getByText('Year-by-year results', { exact: true }).click()
  await expect(page.getByRole('table', { name: 'Annual walk-forward evidence' })).toContainText(
    '−0.246%'.replace('−', '-'),
  )
  await page.screenshot({ path: 'test-results/overview-desktop.png', fullPage: true })
  for (const [route, heading] of [
    ['robustness', 'How broadly does the behavior survive?'],
    ['backtest', 'Outcomes, with execution assumptions'],
    ['exit-research', 'How Should We Exit a Dip?'],
    ['research-diagnosis', "Why isn't V1 stronger yet?"],
    ['hypotheses', 'What deserves a fresh test?'],
    ['experiments', 'What did we learn?'],
    ['paper-archive', 'Paper-signal archive'],
    ['data-quality', 'Small discrepancies. Real research consequences.'],
    ['research-log', 'Research log'],
    ['roadmap', 'What exists. What remains open.'],
    ['signals', 'Signals in context'],
  ]) {
    await page.goto(`/#${route}`)
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  }
  await page.goto('/#paper-archive')
  await expect(
    page.getByRole('heading', {
      name: 'Prospective archive initialized — awaiting first eligible completed session.',
    }),
  ).toBeVisible()
  await page.getByRole('tab', { name: 'Historical replay' }).click()
  await expect(page.getByText('Retrospective records.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'ABBV', exact: true }).click()
  await expect(page.getByText('Configuration SHA-256', { exact: true })).toBeVisible()
  expect(errors).toEqual([])
})
test('signal detail, feature filtering and mobile navigation', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto('/#signal-explorer?experiment=EXP-002&ticker=ABBV')
  await expect(
    page.getByRole('table', { name: 'Filtered historical signal observations' }),
  ).toBeVisible()
  await expect(
    page.getByText('Information known at signal time · after session close', { exact: true }),
  ).toBeVisible()
  await expect(page.getByRole('table', { name: 'Future fixed-horizon outcomes' })).toBeVisible()
  await page.getByRole('combobox', { name: 'Ticker', exact: true }).selectOption('BLK')
  await expect(page.getByRole('heading', { name: 'BLK · adjusted close' })).toBeVisible()
  await page.getByRole('combobox', { name: 'Components', exact: true }).selectOption('4')
  await expect(
    page.getByRole('table', { name: 'Filtered historical signal observations' }),
  ).toBeVisible()
  await page.screenshot({ path: 'test-results/explorer-desktop.png', fullPage: true })
  await page.goto('/#features')
  await expect(page.getByRole('combobox', { name: 'Feature', exact: true })).toBeVisible()
  await page.getByRole('combobox', { name: 'Feature', exact: true }).selectOption('atr_14')
  await expect(page.getByText('Wilder-smoothed absolute movement scale.')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/#overview')
  await page.getByRole('button', { name: 'Menu', exact: true }).click()
  await page.locator('nav a[href="#paper-archive"]').click()
  await expect(
    page.getByRole('heading', { name: 'Paper-signal archive', exact: true }),
  ).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: 'test-results/archive-mobile.png', fullPage: true })
  expect(errors).toEqual([])
})

test('exit comparison and exploratory diagnosis retain unfavorable evidence', async ({ page }) => {
  await page.goto('/#exit-research')
  await expect(
    page.getByRole('table', { name: 'Fixed adaptive and time-only comparison' }),
  ).toContainText('+0.754%')
  await expect(page.getByRole('table', { name: 'Yearly net EV heatmap' })).toContainText('-0.148%')
  await page.getByText('Full-window capture and post-stop recovery', { exact: true }).click()
  await expect(
    page.getByRole('table', { name: 'Exit capture and recovery diagnostics' }),
  ).toBeVisible()
  await page.screenshot({ path: 'test-results/exit-research-desktop.png', fullPage: true })
  await page.goto('/#research-diagnosis')
  await page.getByRole('combobox', { name: 'Question', exact: true }).selectOption('support_group')
  await expect(page.getByRole('table', { name: 'Exploratory diagnostic groups' })).toContainText(
    '-0.070 pp',
  )
  await page.screenshot({ path: 'test-results/diagnosis-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/#exit-research')
  await expect(
    page.getByRole('heading', { name: 'How Should We Exit a Dip?', exact: true }),
  ).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('brief experiments keep negative evidence and offer optional learning on desktop and mobile', async ({
  page,
}) => {
  await page.goto('/#experiments')
  const brief = page.getByRole('region', { name: 'EXP-002 short summary' })
  await expect(brief).toContainText('stock-breadth test failed')
  await expect(brief).toContainText('2022 trade result was negative')
  await expect(page.locator('.document')).toHaveCount(0)
  await expect(
    page.getByRole('table', { name: 'Event and baseline forward-return comparison' }),
  ).toHaveCount(0)
  await page.getByRole('button', { name: 'Explain Expectancy', exact: true }).click()
  await expect(page.getByRole('note')).toContainText('Example only')
  await page.getByRole('button', { name: 'Explain Expectancy', exact: true }).click()
  await page.screenshot({ path: 'test-results/experiments-brief-desktop.png', fullPage: true })
  await page.getByText('Explore the numbers', { exact: true }).click()
  await page.getByText('Exact returns and baseline differences', { exact: true }).click()
  await expect(
    page.getByRole('table', { name: 'Event and baseline forward-return comparison' }),
  ).toContainText('+1.066%')
  await page.getByText('Full research record', { exact: true }).click()
  await expect(page.locator('.document')).toBeVisible()
  await page.getByRole('tab', { name: /EXP-001/ }).click()
  await expect(page.locator('.document')).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'EXP-001 short summary' })).toContainText(
    'Some stocks lost money',
  )
  await page.getByRole('tab', { name: /EXP-002/ }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Explain Expectancy', exact: true }).click()
  await expect(page.getByRole('note')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/experiments-brief-mobile.png', fullPage: true })
  await page.getByRole('tab', { name: /EXP-004/ }).click()
  await expect(page.getByRole('region', { name: 'EXP-004 short summary' })).toContainText(
    'Adaptive exits allowed larger losses',
  )
  await expect(page.getByRole('table', { name: 'Yearly net EV heatmap' })).toHaveCount(0)
  await expect(
    page.getByRole('link', { name: 'Compare expected profit and downside →' }),
  ).toBeVisible()
})
