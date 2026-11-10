#!/bin/bash
# README'yi GitHub'ın markdown API'siyle işler, GitHub görünümüne benzer bir sayfaya koyar,
# açık+koyu ekran görüntüsü alır.  →  uretim/onizleme/{acik,koyu}.png
set -e
cd "$(dirname "$0")/../.."
T=$(cat /root/.github-token)
python3 - "$T" <<'PY'
import json,sys,urllib.request
T=sys.argv[1]
md=open('README.md').read()
r=urllib.request.Request('https://api.github.com/markdown',data=json.dumps({'text':md,'mode':'gfm','context':'pexatasoy/pexatasoy'}).encode(),headers={'Authorization':'Bearer '+T,'Accept':'application/vnd.github+json'})
html=urllib.request.urlopen(r).read().decode()
html=html.replace('src="https://github.com/pexatasoy/pexatasoy/raw/main/','src="../../').replace('srcset="https://github.com/pexatasoy/pexatasoy/raw/main/','srcset="../../')
html=html.replace('src="assets/','src="../../assets/').replace('srcset="assets/','srcset="../../assets/')
sayfa=f'''<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.8.1/github-markdown.min.css">
<style>body{{margin:0;background:#fff}}@media (prefers-color-scheme:dark){{body{{background:#0d1117}}}}
.kutu{{max-width:880px;margin:24px auto;border:1px solid #d0d7de;border-radius:6px;padding:24px}}
@media (prefers-color-scheme:dark){{.kutu{{border-color:#30363d}}}}</style></head>
<body><div class="kutu markdown-body">{html}</div></body></html>'''
open('uretim/onizleme/index.html','w').write(sayfa)
PY
cat > /tmp/claude-0/-root/ec691374-eb2e-46cd-9d53-7c5244c437fb/scratchpad/oniz.cjs <<'JS'
const { chromium } = require('/root/faceless/node_modules/playwright');
(async () => {
  const b = await chromium.launch({ args: ['--no-sandbox', '--disable-gpu'] });
  for (const [tema, ad] of [['light','acik'],['dark','koyu']]) {
    const p = await b.newPage({ viewport: { width: 1000, height: 900 }, colorScheme: tema, deviceScaleFactor: 1 });
    await p.goto('file:///root/github-profil/uretim/onizleme/index.html', { waitUntil: 'load' });
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `/root/github-profil/uretim/onizleme/${ad}.png`, fullPage: true });
    await p.close();
  }
  await b.close();
})();
JS
node /tmp/claude-0/-root/ec691374-eb2e-46cd-9d53-7c5244c437fb/scratchpad/oniz.cjs
