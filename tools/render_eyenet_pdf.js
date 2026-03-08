const playwright = require('playwright');

async function main() {
  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('file:///Users/nickgklezakos/Documents/ppl-meta-code/eyenet-docs/index.html', {
    waitUntil: 'networkidle',
  });

  await page.pdf({
    path: '/Users/nickgklezakos/Documents/ppl-meta-code/eyenet-docs/assets/eyenet-legal-docs.pdf',
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    margin: {
      top: '12mm',
      right: '10mm',
      bottom: '12mm',
      left: '10mm',
    },
  });

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
