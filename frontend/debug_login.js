const { chromium } = require('playwright');

async function debugLogin() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto('http://localhost:3000/login');
  await page.waitForTimeout(2000);

  // Force dark mode
  await page.evaluate(() => {
    document.documentElement.classList.add('dark');
  });
  await page.waitForTimeout(500);

  // Find the login card (rounded-2xl with p-8)
  const card = await page.$('.rounded-2xl');
  if (card) {
    const bg = await card.evaluate(el => getComputedStyle(el).backgroundColor);
    const classes = await card.evaluate(el => el.className);
    console.log(`Login card: bg=${bg}`);
    console.log(`Classes: ${classes.substring(0, 200)}`);
  }

  // Check body background
  const bodyBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  console.log(`Body background: ${bodyBg}`);

  await browser.close();
}

debugLogin().catch(console.error);
