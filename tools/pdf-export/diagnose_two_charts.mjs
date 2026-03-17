import path from 'node:path';
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const src = path.resolve('product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan.html');

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1800, height: 2200 } });
await page.goto(pathToFileURL(src).href, { waitUntil: 'networkidle' });

const result = await page.evaluate(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  if (typeof initializeAllChartsForPrint === 'function') {
    try { initializeAllChartsForPrint(); } catch (_e) {}
  }

  if (typeof showPage === 'function') {
    showPage('investor');
  }
  await wait(1200);

  const investorCanvas = document.getElementById('investorReturnsChart');
  const investorChart = (window.Chart && typeof window.Chart.getChart === 'function')
    ? window.Chart.getChart(investorCanvas)
    : null;
  let investorDataUrl = '';
  try {
    investorDataUrl = investorCanvas ? investorCanvas.toDataURL('image/png') : '';
  } catch (_e) {
    investorDataUrl = '';
  }

  if (typeof showPage === 'function') {
    showPage('competitive');
  }
  if (typeof initializeCompetitiveMoatChart === 'function') {
    try { initializeCompetitiveMoatChart(); } catch (_e) {}
  }
  await wait(1200);

  const moatCanvas = document.getElementById('competitiveMoatChart');
  const moatChart = (window.Chart && typeof window.Chart.getChart === 'function')
    ? window.Chart.getChart(moatCanvas)
    : null;
  let moatDataUrl = '';
  try {
    moatDataUrl = moatCanvas ? moatCanvas.toDataURL('image/png') : '';
  } catch (_e) {
    moatDataUrl = '';
  }

  return {
    investor: {
      canvas: Boolean(investorCanvas),
      chart: Boolean(investorChart),
      dataUrlLength: investorDataUrl.length,
      size: investorCanvas ? [investorCanvas.width, investorCanvas.height, investorCanvas.clientWidth, investorCanvas.clientHeight] : null
    },
    moat: {
      canvas: Boolean(moatCanvas),
      chart: Boolean(moatChart),
      dataUrlLength: moatDataUrl.length,
      size: moatCanvas ? [moatCanvas.width, moatCanvas.height, moatCanvas.clientWidth, moatCanvas.clientHeight] : null
    }
  };
});

console.log(JSON.stringify(result, null, 2));
await browser.close();
