// Kullanım: node ekran.cjs <çıktı.png> <adres> [genişlik] [yükseklik]
const { chromium } = require('/root/faceless/node_modules/playwright');
(async () => {
  const [out, url, w = 1600, h = 1000] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--no-sandbox', '--disable-gpu'] });
  try {
    const p = await b.newPage({ viewport: { width: +w, height: +h } });
    await p.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p.waitForTimeout(3500);
    await p.screenshot({ path: out });
  } finally { await b.close(); }
})().catch(e => { console.error(e.message); process.exit(1); });
