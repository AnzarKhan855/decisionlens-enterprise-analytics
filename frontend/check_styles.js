const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto('http://localhost:3000/login');
  await page.waitForTimeout(2000);

  const loginCard = await page.$('form');
  const body = await page.$('body');

  async function getBg(el, label) {
    if (!el) return label + ': not found';
    return await el.evaluate((e, lbl) => {
      const s = getComputedStyle(e);
      return JSON.stringify({
        label: lbl,
        bgColor: s.backgroundColor,
        color: s.color,
        opacity: s.opacity,
        tag: e.tagName,
        className: e.className
      });
    }, label);
  }

  console.log('Form:', await getBg(loginCard, 'form'));
  console.log('Body:', await getBg(body, 'body'));

  // Also check all divs on login page
  const allDivs = await page.$$('div');
  console.log('Total divs:', allDivs.length);
  for (let i = 0; i < Math.min(allDivs.length, 20); i++) {
    const div = allDivs[i];
    const info = await div.evaluate(e => {
      const s = getComputedStyle(e);
      return JSON.stringify({
        tag: e.tagName,
        className: e.className,
        bgColor: s.backgroundColor
      });
    });
    console.log(`Div ${i}: ${info}`);
  }

  await browser.close();
})();
