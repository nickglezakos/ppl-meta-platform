const { chromium } = require('playwright');

async function main() {
  const baseUrl = process.env.AUTHORITY_E2E_BASE_URL || 'http://127.0.0.1:8011';
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    deviceScaleFactor: 3,
  });

  const request = context.request;
  const bootstrapResponse = await request.post(`${baseUrl}/api/v1/auth/bootstrap-admin`);
  if (!bootstrapResponse.ok() && bootstrapResponse.status() !== 400) {
    throw new Error(`Bootstrap admin failed with status ${bootstrapResponse.status()}`);
  }

  const page = await context.newPage();
  await page.goto(`${baseUrl}/admin/console`, { waitUntil: 'networkidle' });
  await page.locator('#login_email').fill('admin@authority.local');
  await page.locator('#login_password').fill('change-this-admin-password');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.waitForURL(`${baseUrl}/admin/console*`);
  await page.waitForLoadState('networkidle');

  await page.locator('[data-console-filter="users"]').click();
  const firstActions = page.locator('.console-action-menu summary').first();
  await firstActions.waitFor({ state: 'visible' });

  const layoutState = await page.evaluate(() => {
    const tableWrap = document.querySelector('.table-wrap');
    const thead = document.querySelector('thead');
    const firstCell = document.querySelector('tbody td');
    if (!tableWrap || !thead || !firstCell) {
      throw new Error('Console table elements are missing');
    }
    return {
      innerWidth: window.innerWidth,
      media640: window.matchMedia('(max-width: 640px)').matches,
      overflowX: getComputedStyle(tableWrap).overflowX,
      theadDisplay: getComputedStyle(thead).display,
      cellDisplay: getComputedStyle(firstCell).display,
      scrollWidth: tableWrap.scrollWidth,
      clientWidth: tableWrap.clientWidth,
    };
  });

  if (!layoutState.media640) {
    throw new Error(`Mobile media query did not apply: ${JSON.stringify(layoutState)}`);
  }
  if (layoutState.theadDisplay !== 'none') {
    throw new Error(`Table header should be hidden on mobile: ${JSON.stringify(layoutState)}`);
  }
  if (layoutState.cellDisplay !== 'grid') {
    throw new Error(`Mobile table cells should render as grid rows: ${JSON.stringify(layoutState)}`);
  }
  if (layoutState.scrollWidth > layoutState.clientWidth + 1) {
    throw new Error(`Mobile console still overflows horizontally: ${JSON.stringify(layoutState)}`);
  }

  const actionsBox = await firstActions.boundingBox();
  if (!actionsBox) {
    throw new Error('Actions trigger is missing on mobile');
  }
  if (actionsBox.x < 0 || actionsBox.x + actionsBox.width > 390) {
    throw new Error(`Actions trigger is off-screen on mobile: ${JSON.stringify(actionsBox)}`);
  }

  await firstActions.click();
  const firstActionPanel = page.locator('.console-action-menu-panel').first();
  await firstActionPanel.waitFor({ state: 'visible' });
  const panelText = (await firstActionPanel.textContent()) || '';
  if (!panelText.includes('Audit')) {
    throw new Error(`Expected mobile actions panel to include Audit. Got: ${panelText}`);
  }

  console.log('Authority console mobile E2E validation passed.');
  console.log(JSON.stringify({ layoutState, actionsBox, panelText }));

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});