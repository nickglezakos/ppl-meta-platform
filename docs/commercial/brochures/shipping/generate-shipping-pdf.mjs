#!/usr/bin/env node
/**
 * Render eyenet-for-shipping-pdf.html → eyenet-for-shipping.pdf
 * Uses Playwright + system Chrome (channel: chrome).
 *
 * Usage:
 *   node generate-shipping-pdf.mjs
 */
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { chromium } from 'playwright';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  const htmlPath = path.join(__dirname, 'eyenet-for-shipping-pdf.html');
  const pdfPath = path.join(__dirname, 'eyenet-for-shipping.pdf');
  const fileUrl = pathToFileURL(htmlPath).href;

  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  await page.goto(fileUrl, { waitUntil: 'networkidle' });

  await page.addStyleTag({ content: '.no-print { display: none !important; }' });

  await page.pdf({
    path: pdfPath,
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: `<div></div>`,
    footerTemplate: `
      <div style="width:100%;font-size:8px;color:#64748b;padding:0 14mm;
                  font-family:Avenir Next, Helvetica Neue, Helvetica, Arial, sans-serif;
                  display:flex;justify-content:space-between;">
        <span>EyeNet for Shipping · eyenet-vision.com</span>
        <span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
      </div>`,
    margin: {
      top: '12mm',
      bottom: '16mm',
      left: '12mm',
      right: '12mm',
    },
  });

  await browser.close();
  console.log(`Wrote ${pdfPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
