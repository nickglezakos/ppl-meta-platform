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
  await page.goto(`${baseUrl}/admin`, { waitUntil: 'networkidle' });
  await page.locator('#login_email').fill('admin@authority.local');
  await page.locator('#login_password').fill('change-this-admin-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForSelector('#authenticatedShell:not(.hidden)');
  await page.waitForLoadState('networkidle');

  await page.locator('#bottomTabs [data-tab="people"]').click();
  await page.waitForSelector('#view-people.active');
  await page.waitForSelector('#peopleList .list-row, #peopleList .empty-state');

  const layoutState = await page.evaluate(() => {
    const tabs = document.querySelector('.bottom-tabs');
    const people = document.querySelector('#view-people');
    const fab = document.querySelector('#openInviteSheetButton');
    if (!tabs || !people || !fab) {
      throw new Error('Mobile shell elements are missing');
    }
    const tabsBox = tabs.getBoundingClientRect();
    const fabBox = fab.getBoundingClientRect();
    return {
      innerWidth: window.innerWidth,
      media640: window.matchMedia('(max-width: 640px)').matches,
      tabsBottom: tabsBox.bottom,
      tabsWidth: tabsBox.width,
      fabVisible: fabBox.width > 0 && fabBox.height > 0,
      shellOverflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
    };
  });

  if (!layoutState.media640) {
    throw new Error(`Mobile media query did not apply: ${JSON.stringify(layoutState)}`);
  }
  if (layoutState.tabsBottom < 800) {
    throw new Error(`Bottom tabs should sit near the viewport bottom: ${JSON.stringify(layoutState)}`);
  }
  if (layoutState.shellOverflowX) {
    throw new Error(`Mobile shell still overflows horizontally: ${JSON.stringify(layoutState)}`);
  }
  if (!layoutState.fabVisible) {
    throw new Error('Invite FAB should be visible on People for platform admin');
  }

  await page.locator('#openInviteSheetButton').click();
  await page.waitForSelector('#inviteSheet:not(.hidden)');
  const inviteTitle = await page.locator('#inviteSheetTitle').textContent();
  if (!inviteTitle || !inviteTitle.includes('Invite')) {
    throw new Error(`Expected invite sheet title. Got: ${inviteTitle}`);
  }

  console.log('Authority mobile shell E2E validation passed.');
  console.log(JSON.stringify({ layoutState, inviteTitle }));

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
