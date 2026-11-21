// 用无头浏览器打开参考网页（与普通访客看到的一致），展开所有「本季 N 次申报」明细，输出渲染后的全文。
// 用法：node fetch_page.js > data/masterstao_masters4_<日期>_expanded.txt
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 2400 }, locale: 'zh-CN' });
  await p.goto('https://masterstao.com/zh/masters/4?quarter=latest&page=1&action=%E5%85%A8%E9%83%A8', { waitUntil: 'networkidle', timeout: 60000 });
  await p.waitForTimeout(2500);
  const btns = p.locator('button', { hasText: /本季 \d+ 次申报/ });
  const n = await btns.count();
  for (let i = 0; i < n; i++) { await btns.nth(i).click(); await p.waitForTimeout(700); }
  process.stdout.write(await p.evaluate(() => document.body.innerText));
  await b.close();
})();
