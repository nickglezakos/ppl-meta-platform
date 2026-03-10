#!/usr/bin/env node
import { chromium } from 'playwright';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const workspaceRoot = process.cwd();
const defaultInput = path.resolve(
  workspaceRoot,
  'product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/index.html'
);

const inputPath = process.argv[2] ? path.resolve(process.argv[2]) : defaultInput;
const outputPath = process.argv[3]
  ? path.resolve(process.argv[3])
  : path.resolve(workspaceRoot, 'product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/EyeNet_BusinessPlan_2026.pdf');

const pageIds = [
  'home',
  'executive',
  'personas',
  'competitive',
  'functionalities',
  'business-better',
  'revenue',
  'investor',
  'roadmap'
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function initializeAllSections(page) {
  await page.evaluate(async (ids) => {
    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    for (const id of ids) {
      if (typeof window.showPage === 'function') {
        window.showPage(id);
        await wait(240);
      }
    }
    if (typeof window.showPage === 'function') {
      window.showPage('home');
      await wait(150);
    }
  }, pageIds);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 2200 } });
  const page = await context.newPage();

  const targetUrl = pathToFileURL(inputPath).href;
  await page.goto(targetUrl, { waitUntil: 'networkidle' });

  await initializeAllSections(page);
  await sleep(350);

  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: outputPath,
    format: 'A4',
    printBackground: true,
    margin: {
      top: '10mm',
      right: '10mm',
      bottom: '12mm',
      left: '10mm'
    }
  });

  await browser.close();
  console.log(`PDF generated: ${outputPath}`);
}

run().catch((err) => {
  console.error('Failed to generate PDF.');
  console.error(err && err.message ? err.message : err);
  process.exit(1);
});
