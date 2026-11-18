// 用无头浏览器打开参考网页（与普通访客看到的一致），输出渲染后的全文。
// 用法：node fetch_page.js > data/masterstao_masters4_<日期>.txt
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 2400 }, locale: 'zh-CN' });
  await p.goto('https://masterstao.com/zh/masters/4', { waitUntil: 'networkidle', timeout: 60000 });
  await p.waitForTimeout(2500);
  process.stdout.write(await p.evaluate(() => document.body.innerText));
  await b.close();
})();
