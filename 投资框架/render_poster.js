// 把《企业盈利能力评估框架》海报 HTML 渲染成 2 倍清晰度的 PNG。
// 用法：node 投资框架/render_poster.js
// 依赖：Playwright（Chromium）；字体从 Google Fonts 加载，需要能访问 fonts.googleapis.com。
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const html = path.join(__dirname, '企业盈利能力评估框架海报.html');
  const png = path.join(__dirname, '企业盈利能力评估框架海报.png');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 2 });
  await page.goto('file://' + html, { waitUntil: 'networkidle', timeout: 120000 });
  await page.evaluate(() => document.fonts.ready.then(() => true));
  await page.locator('body > div').first().screenshot({ path: png });
  await browser.close();
  console.log('已生成', png);
})();
