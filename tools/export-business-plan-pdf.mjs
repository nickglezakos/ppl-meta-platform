#!/usr/bin/env node
import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs/promises';
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
const sectionedMode = process.argv.includes('--sectioned');

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

  if (!sectionedMode) {
    await page.pdf({
      path: outputPath,
      format: 'A4',
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: `<div style="width:100%;font-size:9pt;font-family:Georgia,serif;color:#111;font-weight:600;padding:0 14mm;height:14mm;display:flex;align-items:center;justify-content:space-between;box-sizing:border-box;-webkit-print-color-adjust:exact;"><span>EyeNet Vision - Business Plan 2026</span><span>Full Document</span></div>`,
      footerTemplate: `<div style="width:100%;font-size:9pt;font-family:Georgia,serif;color:#111;padding:0 14mm;height:10mm;display:flex;align-items:center;justify-content:space-between;box-sizing:border-box;-webkit-print-color-adjust:exact;"><span>Confidential - EyeNet Vision</span><span>Page <span class="pageNumber"></span></span></div>`,
      margin: {
        top: '18mm',
        right: '10mm',
        bottom: '14mm',
        left: '10mm'
      }
    });
    console.log(`PDF generated: ${outputPath}`);
  } else {
    const outDir = outputPath.replace(/\.pdf$/i, '') + '_sections';
    await fs.mkdir(outDir, { recursive: true });

    // Export TOC-only PDF first.
    await page.evaluate(() => {
      const style = document.createElement('style');
      style.id = 'section-export-style';
      style.textContent = `
        @media print {
          .page { display: none !important; }
          .print-toc { display: block !important; }
        }
      `;
      document.head.appendChild(style);
    });

    await page.pdf({
      path: path.join(outDir, '00-table-of-contents.pdf'),
      format: 'A4',
      printBackground: true,
      margin: {
        top: '10mm',
        right: '10mm',
        bottom: '12mm',
        left: '10mm'
      }
    });

    for (let i = 0; i < pageIds.length; i += 1) {
      const sectionId = pageIds[i];
      await page.evaluate((id) => {
        if (typeof window.showPage === 'function') {
          window.showPage(id);
        }

        const prev = document.getElementById('section-export-style');
        if (prev) prev.remove();

        const style = document.createElement('style');
        style.id = 'section-export-style';
        style.textContent = `
          @media print {
            .print-toc { display: none !important; }
            .page { display: none !important; }
            #${id}.page { display: block !important; break-before: auto !important; page-break-before: auto !important; }
          }
        `;
        document.head.appendChild(style);
      }, sectionId);

      await sleep(180);
      await page.pdf({
        path: path.join(outDir, `${String(i + 1).padStart(2, '0')}-${sectionId}.pdf`),
        format: 'A4',
        printBackground: true,
        margin: {
          top: '10mm',
          right: '10mm',
          bottom: '12mm',
          left: '10mm'
        }
      });
    }

    console.log(`Section PDFs generated in: ${outDir}`);
    console.log('Tip: review section PDFs to identify layout issues before final combined export.');
  }

  await browser.close();
}

run().catch((err) => {
  console.error('Failed to generate PDF.');
  console.error(err && err.message ? err.message : err);
  process.exit(1);
});
