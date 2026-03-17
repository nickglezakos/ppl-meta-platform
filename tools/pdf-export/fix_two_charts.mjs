import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const srcHtml = path.resolve(root, 'product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan.html');
const interimHtml = path.resolve(root, 'product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan-interim-print.html');

async function captureChartDataUrl(page, chartId, pageId, width, height) {
  return page.evaluate(async ({ chartId, pageId, width, height }) => {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));

    if (typeof window.showPage === 'function') {
      window.showPage(pageId);
      await wait(350);
    }

    if (chartId === 'investorReturnsChart' && typeof window.initializeCharts === 'function') {
      window.initializeCharts();
      await wait(500);
    }
    if (chartId === 'competitiveMoatChart' && typeof window.initializeCompetitiveMoatChart === 'function') {
      window.initializeCompetitiveMoatChart();
      await wait(600);
    }

    const canvas = document.getElementById(chartId);
    if (!canvas) {
      return null;
    }

    // Keep capture path passive here to avoid Chart.js scriptable-option runtime errors.
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    await wait(1000);

    try {
      const dataUrl = canvas.toDataURL('image/png');
      if (typeof dataUrl === 'string' && dataUrl.startsWith('data:image/png;base64,') && dataUrl.length > 256) {
        return dataUrl;
      }
    } catch (_err) {
      return null;
    }

    return null;
  }, { chartId, pageId, width, height });
}

function replaceSrc(htmlText, id, dataUrl) {
  const re = new RegExp(`(alt=\\"${id}\\"\\s+src=\\")data:image\\/png;base64,[^\\"]*(\\")`);
  if (!re.test(htmlText)) {
    throw new Error(`Could not find img src for ${id}`);
  }
  return htmlText.replace(re, `$1${dataUrl}$2`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1800, height: 2200 } });
  await page.goto(pathToFileURL(srcHtml).href, { waitUntil: 'networkidle' });

  const investorDataUrl = await captureChartDataUrl(page, 'investorReturnsChart', 'investor', 1400, 800);
  const moatDataUrl = await captureChartDataUrl(page, 'competitiveMoatChart', 'competitive', 1200, 1200);

  await browser.close();

  if (!investorDataUrl) {
    throw new Error('Failed to capture investorReturnsChart data URL');
  }
  if (!moatDataUrl) {
    throw new Error('Failed to capture competitiveMoatChart data URL');
  }

  let html = fs.readFileSync(interimHtml, 'utf8');
  html = replaceSrc(html, 'investorReturnsChart', investorDataUrl);
  html = replaceSrc(html, 'competitiveMoatChart', moatDataUrl);
  fs.writeFileSync(interimHtml, html, 'utf8');

  console.log('Updated interim HTML with recaptured charts (dataURL): investorReturnsChart, competitiveMoatChart');
}

main().catch((err) => {
  console.error(err?.message || err);
  process.exit(1);
});
