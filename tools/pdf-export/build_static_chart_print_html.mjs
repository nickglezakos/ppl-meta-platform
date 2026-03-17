#!/usr/bin/env node
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const workspaceRoot = process.cwd();
const defaultInput = path.resolve(
  workspaceRoot,
  'product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/index.html'
);
const defaultOutput = path.resolve(
  workspaceRoot,
  'tools/pdf-export/output/business-plan-static-charts.html'
);

const inputPath = process.argv[2] ? path.resolve(process.argv[2]) : defaultInput;
const outputPath = process.argv[3] ? path.resolve(process.argv[3]) : defaultOutput;

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
        await wait(260);
      }
    }
    if (typeof window.showPage === 'function') {
      window.showPage('home');
      await wait(150);
    }
  }, pageIds);
}

async function buildStaticHtml(page) {
  return page.evaluate(async () => {
    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => resolve()));
    const compactChartIds = new Set([
      'featureComparisonChart',
      'competitiveMoatChart'
    ]);
    const staticRenderChartIds = new Set([
      'revenueChart',
      'investorReturnsChart',
      'featureComparisonChart',
      'competitiveMoatChart'
    ]);
    const strictBaselineChartIds = new Set([
      'revenueChart',
      'investorReturnsChart'
    ]);
    const isValidDataUrl = (value) => (
      typeof value === 'string'
      && value.startsWith('data:image/')
      && value.length > 128
    );

    const createStaticChartImage = async (chartId, targetWidth, targetHeight) => {
      // Extract data from the original chart and create a fresh static instance
      const originalChart = (typeof window.Chart?.getChart === 'function')
        ? window.Chart.getChart(document.getElementById(chartId))
        : null;
      
      if (!originalChart) {
        console.log(`[static] No chart found for ${chartId}, skipping`);
        return null;
      }

      // Clone the chart config from the original
      const config = JSON.parse(JSON.stringify(originalChart.config));
      
      // Create a temporary container and canvas for the static render
      const container = document.createElement('div');
      container.style.position = 'fixed';
      container.style.top = '-9999px';
      container.style.left = '-9999px';
      container.style.width = `${targetWidth}px`;
      container.style.height = `${targetHeight}px`;
      document.body.appendChild(container);

      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = targetWidth;
      tempCanvas.height = targetHeight;
      tempCanvas.style.width = `${targetWidth}px`;
      tempCanvas.style.height = `${targetHeight}px`;
      container.appendChild(tempCanvas);

      try {
        const ctx = tempCanvas.getContext('2d');
        
        // Remove interactive options for static render
        config.options = config.options || {};
        config.options.responsive = false;
        config.options.maintainAspectRatio = false;
        config.options.plugins = config.options.plugins || {};
        config.options.plugins.tooltip = { enabled: false };
        config.options.plugins.filler = config.options.plugins.filler || {};
        
        // Create the static chart
        const staticChart = new window.Chart(ctx, config);
        
        // Render and capture
        await new Promise(resolve => setTimeout(resolve, 50));
        const dataUrl = tempCanvas.toDataURL('image/png');
        staticChart.destroy();
        
        container.remove();
        
        if (isValidDataUrl(dataUrl)) {
          console.log(`[static] Created ${chartId}: ${targetWidth}x${targetHeight}`);
          return dataUrl;
        }
        return null;
      } catch (err) {
        console.log(`[static] Failed to create ${chartId}:`, err.message);
        container.remove();
        return null;
      }
    };

    const enforceLiveChartOptions = (chart, chartId) => {
      // Ensure chart options have baseline config from source HTML.
      // No mutation needed; source charts already have beginAtZero configured.
    };

    const removeSelectors = [
      'header',
      'nav',
      'footer',
      '.badge-nav-container',
      '#backToTop'
    ];

    removeSelectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((el) => el.remove());
    });

    const pageNodes = Array.from(document.querySelectorAll('main > .page'));
    const tocItems = pageNodes
      .map((section) => {
        const title = section.querySelector('.content-wrapper h1')?.textContent?.trim() || section.id;
        return { id: section.id, title };
      })
      .filter((x) => x.id && x.title);

    const toc = document.createElement('section');
    toc.className = 'static-toc';
    toc.innerHTML = `
      <h1>Table of Contents</h1>
      <p>EyeNet Vision Business Plan 2026</p>
      <ol>
        ${tocItems.map((item) => `<li><a href="#${item.id}">${item.title}</a></li>`).join('')}
      </ol>
    `;

    const main = document.querySelector('main');
    if (main) {
      main.prepend(toc);
    }

    pageNodes.forEach((section) => {
      section.classList.add('active');
      section.style.display = 'block';
      section.style.animation = 'none';
    });

    const canvases = Array.from(document.querySelectorAll('canvas[id$="Chart"]'));
    for (const canvas of canvases) {
      const chartId = canvas.id || 'Chart';
      
      // Set target sizes based on chart type
      const targetWidth = compactChartIds.has(chartId) ? 840 : 1280;
      const targetHeight = compactChartIds.has(chartId) ? 840 : 720;
      
      let dataUrl = null;

      // For all target charts, create fresh static instances
      if (staticRenderChartIds.has(chartId)) {
        dataUrl = await createStaticChartImage(chartId, targetWidth, targetHeight);
      }

      // If static creation failed or not a target chart, use original rendering
      if (!isValidDataUrl(dataUrl)) {
        const chart = (typeof window.Chart?.getChart === 'function')
          ? window.Chart.getChart(canvas)
          : null;
        
        // Use CSS sizing (not intrinsic canvas.width/height) to avoid clearing the canvas
        canvas.style.width = `${targetWidth}px`;
        canvas.style.height = `${targetHeight}px`;

        // Force a render pass so charts paint at new size.
        if (chart && typeof chart.update === 'function') {
          try {
            if (typeof chart.resize === 'function') {
              chart.resize();
            }
            chart.update('none');
            await nextFrame();
            await wait(20);
          } catch (_err) {
            // Ignore chart update failures
          }
        }

        if (chart) {
          try {
            // Final render pass
            if (typeof chart.resize === 'function') {
              chart.resize();
            }
            if (typeof chart.update === 'function') {
              chart.update('none');
            }
            if (typeof chart.render === 'function') {
              chart.render();
            }
            await nextFrame();
            await wait(40);
            
            // Try Chart.js's toBase64Image() first (often higher quality)
            if (typeof chart.toBase64Image === 'function') {
              dataUrl = chart.toBase64Image();
            }
          } catch (_err) {
            // Ignore render failures
          }
        }
        
        // Fall back to canvas.toDataURL() if toBase64Image() didn't work
        if (!isValidDataUrl(dataUrl)) {
          try {
            dataUrl = canvas.toDataURL('image/png');
          } catch (_err) {
            dataUrl = null;
          }
        }

        if (!isValidDataUrl(dataUrl) && chart && typeof chart.toBase64Image === 'function') {
          try {
            dataUrl = chart.toBase64Image();
          } catch (_err) {
            dataUrl = null;
          }
        }
      }

      const img = document.createElement('img');
      img.className = 'static-chart-image';
      if (compactChartIds.has(chartId)) {
        img.classList.add('static-chart-image-compact');
      }
      img.alt = chartId;
      if (isValidDataUrl(dataUrl)) {
        img.src = dataUrl;
      }

      const fallback = !isValidDataUrl(dataUrl);
      if (fallback) {
        const placeholder = document.createElement('div');
        placeholder.className = 'static-chart-fallback';
        placeholder.textContent = `${chartId} (chart image unavailable)`;
        canvas.replaceWith(placeholder);
      } else {
        canvas.replaceWith(img);
      }
    }

    // Remove accidental duplicate figure captions and keep only one per chart id.
    const seenFigureIds = new Set();
    document.querySelectorAll('.figure-caption[data-figure-for]').forEach((caption) => {
      const figureId = (caption.getAttribute('data-figure-for') || '').trim();
      if (!figureId) {
        return;
      }
      if (seenFigureIds.has(figureId)) {
        caption.remove();
        return;
      }
      seenFigureIds.add(figureId);
    });

    document.querySelectorAll('script').forEach((el) => el.remove());

    const style = document.createElement('style');
    style.id = 'static-print-style';
    style.textContent = `
      @page {
        size: A4;
        margin: 14mm;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: #1a1a1a;
        background: #ffffff;
        line-height: 1.45;
      }

      main {
        margin: 0;
        padding: 0;
        min-height: auto;
      }

      .static-toc {
        border: 1px solid #d7d7d7;
        padding: 16px 20px;
        margin: 0 0 20px 0;
        break-after: page;
        page-break-after: always;
      }

      .static-toc h1 {
        margin: 0 0 8px 0;
        font-size: 28px;
        border-bottom: 2px solid #333;
        padding-bottom: 6px;
      }

      .static-toc p {
        margin: 0 0 10px 0;
        color: #444;
      }

      .static-toc ol {
        margin: 0;
        padding-left: 20px;
      }

      .static-toc li { margin: 4px 0; }
      .static-toc a { color: #111; text-decoration: none; }

      .page {
        display: block !important;
        animation: none !important;
        break-after: auto;
        page-break-after: auto;
      }

      .page + .page {
        break-before: page;
        page-break-before: always;
      }

      .content-wrapper {
        max-width: 100%;
        border: 1px solid #d7d7d7;
        border-radius: 0;
        box-shadow: none;
        background: #ffffff;
        padding: 16px 18px;
      }

      h1, h2, h3, h4 {
        break-after: avoid-page;
        page-break-after: avoid;
        margin-top: 14px;
        margin-bottom: 7px;
        color: #111;
      }

      h1 {
        font-size: 24px;
        border-bottom: 2px solid #333;
        padding-bottom: 6px;
        margin-top: 0;
      }

      h2 {
        font-size: 20px;
        border-bottom: 1px solid #999;
        padding-bottom: 4px;
      }

      h3 { font-size: 16px; }
      h4 { font-size: 14px; }

      p, li, td, th {
        font-size: 11.5px;
        color: #222;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        page-break-inside: auto;
      }

      thead { display: table-header-group; }

      tr {
        break-inside: avoid;
        page-break-inside: avoid;
      }

      th, td {
        border: 1px solid #cfcfcf;
        padding: 6px;
        vertical-align: top;
      }

      th {
        background: #efefef;
        color: #111;
      }

      .static-chart-image {
        display: block;
        width: 100%;
        max-width: 100%;
        max-height: 70vh;
        height: auto;
        object-fit: contain;
        border: 1px solid #d5d5d5;
        background: #ffffff;
        border-radius: 8px;
        padding: 8px;
        margin: 8px 0 12px 0;
        break-inside: avoid;
        page-break-inside: avoid;
      }

      .static-chart-image-compact {
        width: min(72%, 520px);
        margin: 8px auto 12px auto;
      }

      .chart-scroll-content.chart-print-block,
      .chart-print-block {
        display: flex;
        flex-direction: column;
        overflow: visible !important;
        background: linear-gradient(180deg, #f4f9ff 0%, #ffffff 100%);
        border: 1px solid #dbe6f3;
        border-radius: 10px;
        padding: 10px 12px;
      }

      .figure-caption {
        margin: 4px auto 8px auto;
        text-align: center;
        font-size: 10.5px;
        color: #364152;
        font-style: italic;
      }

      .static-chart-fallback {
        border: 1px dashed #b8b8b8;
        background: #fafafa;
        padding: 8px 10px;
        margin: 8px 0 12px 0;
        font-size: 10.5px;
        color: #555;
        font-style: italic;
      }

      .badge, .badge-nav {
        display: none !important;
      }
    `;
    document.head.appendChild(style);

    return `<!DOCTYPE html>\n${document.documentElement.outerHTML}`;
  });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 4000, height: 6000 } });
  const page = await context.newPage();

  await page.goto(pathToFileURL(inputPath).href, { waitUntil: 'networkidle' });
  await initializeAllSections(page);
  await sleep(450);

  const staticHtml = await buildStaticHtml(page);

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, staticHtml, 'utf-8');

  await browser.close();
  console.log(`Generated static-chart print HTML: ${outputPath}`);
}

run().catch((err) => {
  console.error('Failed to build static-chart print HTML.');
  console.error(err && err.message ? err.message : err);
  process.exit(1);
});
