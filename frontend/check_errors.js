const { chromium } = require('playwright');

async function checkErrors() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    bypassCSP: true
  });
  const page = await context.newPage();

  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', (err) => {
    errors.push(`Uncaught: ${err.message}`);
  });

  const token = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiYWRtaW5AZW50ZXJwcmlzZS5jb20iLCAicm9sZSI6ICJFTVBMT1lFRSIsICJmdWxsX25hbWUiOiAiRW50ZXJwcmlzZSBBZG1pbiIsICJ0ZW5hbnRfaWQiOiAidGVuYW50LWFkbWluIiwgImV4cCI6IDE3ODYyMjEyMTd9.zFCfJ3YReCFqKn43nmrqujRjsdlIxFJ1i2fAcDpA_dU';
  const activeWs = 'ws-c9a9e388';

  await page.goto('http://localhost:3000/login');
  await page.waitForTimeout(1000);

  await page.evaluate(({ t, ws }) => {
    localStorage.setItem('decisionlens_access_token', t);
    localStorage.setItem('decisionlens_active_workspace', ws);
    localStorage.setItem('decisionlens_user', JSON.stringify({ email: 'admin@enterprise.com', full_name: 'Enterprise Admin', role: 'ADMIN' }));
  }, { t: token, ws: activeWs });

  const pages = ['/dynamic-dashboard', '/forecasts', '/strategy', '/copilot', '/reports', '/settings'];

  for (const route of pages) {
    console.log(`\nChecking ${route}...`);
    errors.length = 0;
    await page.goto(`http://localhost:3000${route}`);
    await page.waitForTimeout(4000);

    const criticalErrors = errors.filter(e =>
      e.includes('ReferenceError') ||
      e.includes('TypeError') ||
      e.includes('Hydration') ||
      e.includes('500') ||
      e.includes('Error')
    );

    console.log(`  Console errors: ${errors.length}`);
    console.log(`  Critical errors: ${criticalErrors.length}`);
    for (const err of criticalErrors.slice(0, 10)) {
      console.log(`    - ${err}`);
    }
  }

  await browser.close();
}

checkErrors().catch(console.error);
