// e2e for the site: open site/index.html from disk, count what is actually drawn,
// and compare it with out/results.json. Exit code is the verdict.
// playwright lives in another project on this machine; point PLAYWRIGHT_PATH at
// its index.js (a file:// URL) when the package is not installed next to this one.
const PW = process.env.PLAYWRIGHT_PATH || 'playwright';
const pw = await import(PW);
const chromium = pw.chromium ?? (pw.default && pw.default.chromium);
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const root = path.resolve(process.cwd());
const url = pathToFileURL(path.join(root, 'site', 'index.html')).href;
const res = JSON.parse(fs.readFileSync(path.join(root, 'out', 'results.json'), 'utf8'));
const byN = new Map(res.puzzles.map((r) => [r.n, r]));

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ': ' + detail : ''}`);
}

const browser = await chromium.launch(
  process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}
);
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const consoleErrors = [];
const offsite = [];
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('request', (r) => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:')) offsite.push(r.url()); });

await page.goto(url, { waitUntil: 'load' });

check('title carries the work name', (await page.title()).includes('方寸之间'), await page.title());
check('h1 is the short title', (await page.locator('h1').innerText()).trim().includes('方寸之间'));
const sections = await page.locator('section').count();
check('at least 6 sections', sections >= 6, `${sections} sections`);

const cards = page.locator('figure.card');
const cardCount = await cards.count();
check('gallery has 12 packings', cardCount === 12, `${cardCount} cards`);

// every card draws exactly n squares, and the caption quotes the side from results.json
let mismatch = [];
for (let i = 0; i < cardCount; i++) {
  const card = cards.nth(i);
  const n = parseInt((await card.locator('figcaption b').innerText()).replace(/\D/g, ''), 10);
  const squares = await card.locator('path.sq').count();
  const caption = await card.locator('figcaption .side').innerText();
  const want = byN.get(n);
  if (!want || squares !== n || !caption.includes(want.side.toFixed(4))) {
    mismatch.push({ n, squares, caption, want: want && want.side.toFixed(4) });
  }
}
check('every card draws n squares and quotes the measured L', mismatch.length === 0, JSON.stringify(mismatch.slice(0, 3)));

const bandRects = await page.locator('svg rect.bg').count();
check('band chart has 31 bands', bandRects === 31, `${bandRects} bands`);
const bandBars = await page.locator('svg rect.bo').count();
check('band chart has a bar per band', bandBars === 31, `${bandBars} bars`);

const bodyText = await page.locator('body').innerText();
check('total score appears on the page', bodyText.includes(res.total_score.toFixed(4)), res.total_score.toFixed(4));
check('grid baseline appears on the page', bodyText.includes(res.grid_total.toFixed(4)), res.grid_total.toFixed(4));

const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
check('no horizontal overflow at 1280px', overflow <= 1, `${overflow}px`);

const small = await browser.newPage({ viewport: { width: 390, height: 844 } });
await small.goto(url, { waitUntil: 'load' });
const overflowSmall = await small.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
check('no horizontal overflow at 390px', overflowSmall <= 1, `${overflowSmall}px`);
const smallCards = await small.locator('figure.card').count();
check('mobile layout keeps all cards', smallCards === 12, `${smallCards} cards`);

check('no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 2).join(' | '));
check('no off-site requests', offsite.length === 0, offsite.slice(0, 3).join(' | '));

await page.screenshot({ path: path.join(root, 'out', 'figures', 'site-1280.png'), fullPage: true });
await small.screenshot({ path: path.join(root, 'out', 'figures', 'site-390.png'), fullPage: true });

await browser.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
