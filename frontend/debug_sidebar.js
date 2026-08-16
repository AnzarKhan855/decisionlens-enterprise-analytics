const { chromium } = require('playwright');

async function debugSidebar() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const token = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiYWRtaW5AZW50ZXJwcmlzZS5jb20iLCAicm9sZSI6ICJFTVBMT1lFRSIsICJmdWxsX25hbWUiOiAiRW50ZXJwcmlzZSBBZG1pbiIsICJ0ZW5hbnRfaWQiOiAidGVuYW50LWFkbWluIiwgImV4cCI6IDE3ODYyMjEyMTd9.zFCfJ3YReCFqKn43nmrqujRjsdlIxFJ1i2fAcDpA_dU';
  const activeWs = 'ws-c9a9e388';

  await page.goto('http://localhost:3000/login');
  await page.waitForTimeout(1000);

  await page.evaluate(({ t, ws }) => {
    localStorage.setItem('decisionlens_access_token', t);
    localStorage.setItem('decisionlens_active_workspace', ws);
    localStorage.setItem('decisionlens_user', JSON.stringify({ email: 'admin@enterprise.com', full_name: 'Enterprise Admin', role: 'ADMIN' }));
  }, { t: token, ws: activeWs });

  await page.goto('http://localhost:3000/dynamic-dashboard');
  await page.waitForTimeout(4000);

  // Find all aside elements
  const asides = await page.$$('aside');
  console.log(`Found ${asides.length} aside elements`);

  for (let i = 0; i < asides.length; i++) {
    const aside = asides[i];
    const isVisible = await aside.isVisible();
    const bg = await aside.evaluate(el => getComputedStyle(el).backgroundColor);
    const classes = await aside.evaluate(el => el.className);
    console.log(`Aside ${i}: visible=${isVisible}, bg=${bg}, classes=${classes.substring(0, 100)}`);
  }

  // Check the sidebar specifically
  const sidebar = await page.$('aside[aria-label="Main navigation"]');
  if (sidebar) {
    const isVisible = await sidebar.isVisible();
    const bg = await sidebar.evaluate(el => getComputedStyle(el).backgroundColor);
    console.log(`\nMain nav sidebar: visible=${isVisible}, bg=${bg}`);
  }

  await browser.close();
}

debugSidebar().catch(console.error);
