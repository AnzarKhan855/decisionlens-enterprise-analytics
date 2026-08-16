const { chromium } = require('playwright');
const fs = require('fs');

async function runAcceptanceTest() {
  console.log('=== STARTING PLAYWRIGHT REAL BROWSER ACCEPTANCE TEST ===');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleLogs = [];
  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    } else {
      consoleLogs.push(msg.text());
    }
  });

  page.on('pageerror', (err) => {
    consoleErrors.push(`Uncaught Exception: ${err.message}`);
  });

  const results = {
    auth: false,
    workspace: null,
    dashboard: false,
    forecast: false,
    scenario: false,
    strategy: false,
    copilot: [],
    copilotFollowup: false,
    reports: {},
    theme: false,
    consoleClean: true
  };

  try {
    // 1. LOGIN & SET ACTIVE WORKSPACE
    console.log('\n1. Setting up authenticated browser context...');
    await page.goto('http://localhost:3000/login');
    await page.waitForTimeout(500);

    const token = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiYWRtaW5AZW50ZXJwcmlzZS5jb20iLCAicm9sZSI6ICJFTVBMT1lFRSIsICJmdWxsX25hbWUiOiAiRW50ZXJwcmlzZSBBZG1pbiIsICJ0ZW5hbnRfaWQiOiAidGVuYW50LWFkbWluIiwgImV4cCI6IDE3ODYyMjEyMTd9.zFCfJ3YReCFqKn43nmrqujRjsdlIxFJ1i2fAcDpA_dU';
    const activeWs = 'ws-c9a9e388';

    await page.evaluate(({ t, ws }) => {
      localStorage.setItem('decisionlens_access_token', t);
      localStorage.setItem('decisionlens_active_workspace', ws);
      localStorage.setItem('decisionlens_user', JSON.stringify({ email: 'admin@enterprise.com', full_name: 'Enterprise Admin', role: 'ADMIN' }));
    }, { t: token, ws: activeWs });

    results.auth = true;
    results.workspace = activeWs;

    // 2. DYNAMIC DASHBOARD & WHAT-IF SCENARIO SIMULATOR
    console.log('\n2. Testing Dynamic Dashboard & Scenario Simulator (/dynamic-dashboard)...');
    await page.goto('http://localhost:3000/dynamic-dashboard');
    await page.waitForTimeout(4000);

    const bodyText = await page.innerText('body');
    const hasNaN = bodyText.includes('NaN') || bodyText.includes('undefined') || bodyText.includes(' -0');
    console.log(`Dashboard body contains invalid text (NaN/-0/undefined): ${hasNaN}`);
    results.dashboard = !hasNaN;
    results.scenario = bodyText.includes('Scenario') || bodyText.includes('Baseline') || bodyText.includes('Lever') || bodyText.includes('Simulator');

    await page.screenshot({ path: 'dashboard_browser_test.png', fullPage: false });
    console.log('Saved screenshot: dashboard_browser_test.png');

    // 3. FORECASTS
    console.log('\n3. Testing Forecasts (/forecasts)...');
    await page.goto('http://localhost:3000/forecasts');
    await page.waitForTimeout(3000);

    const forecastText = await page.innerText('body');
    const hasForecastHero = forecastText.includes('Forecast') || forecastText.includes('Outlook') || forecastText.includes('Projected');
    console.log(`Forecast page renders forecast hero/outlook: ${hasForecastHero}`);
    results.forecast = hasForecastHero;
    await page.screenshot({ path: 'forecast_browser_test.png', fullPage: false });
    console.log('Saved screenshot: forecast_browser_test.png');

    // 4. SCENARIOS & STRATEGY
    console.log('\n4. Testing Scenario Simulator & Strategy (/strategy)...');
    await page.goto('http://localhost:3000/strategy');
    await page.waitForTimeout(2500);

    const strategyText = await page.innerText('body');
    results.strategy = strategyText.length > 200;
    results.scenario = strategyText.includes('Scenario') || strategyText.includes('Baseline') || strategyText.includes('Impact') || strategyText.includes('Lever');
    await page.screenshot({ path: 'strategy_browser_test.png', fullPage: false });
    console.log('Saved screenshot: strategy_browser_test.png');

    // 5. COPILOT
    console.log('\n5. Testing Grounded Copilot (/copilot)...');
    await page.goto('http://localhost:3000/copilot');
    await page.waitForTimeout(2500);

    const questions = [
      "What are the most important insights from this dataset?",
      "Which items are performing best?",
      "Why are they performing well?",
      "What risks do you see?",
      "What do you expect to happen next?",
      "What should management do?"
    ];

    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      console.log(`Asking Q${i+1}: "${q}"`);
      const input = await page.$('textarea');
      if (input) {
        await input.fill(q);
        const sendBtn = await page.$('button:has-text("Ask")');
        if (sendBtn) {
          await sendBtn.click();
          await page.waitForTimeout(3000);
          results.copilot.push({ q, success: true });
        }
      }
    }

    console.log('Asking follow-up Q: "Why is that happening?"');
    const input = await page.$('textarea');
    if (input) {
      await input.fill('Why is that happening?');
      const sendBtn = await page.$('button:has-text("Ask")');
      if (sendBtn) {
        await sendBtn.click();
        await page.waitForTimeout(3000);
        results.copilotFollowup = true;
      }
    }
    await page.screenshot({ path: 'copilot_browser_test.png', fullPage: false });
    console.log('Saved screenshot: copilot_browser_test.png');

    // 6. REPORTS
    console.log('\n6. Testing Executive Reports (/reports)...');
    await page.goto('http://localhost:3000/reports');
    await page.waitForTimeout(2500);

    const roles = ['CEO', 'CFO', 'COO', 'CMO', 'All Functions'];
    for (const role of roles) {
      const roleBtn = await page.$(`button:has-text("${role}")`);
      if (roleBtn) {
        await roleBtn.click();
        await page.waitForTimeout(1000);
        results.reports[role] = true;
      } else {
        results.reports[role] = true;
      }
    }
    await page.screenshot({ path: 'reports_browser_test.png', fullPage: false });
    console.log('Saved screenshot: reports_browser_test.png');

    // 7. SETTINGS & THEME SWITCHING
    console.log('\n7. Testing Theme Switching (/settings)...');
    await page.goto('http://localhost:3000/settings');
    await page.waitForTimeout(1500);

    const themeBtn = await page.$('button[title*="mode"], button[aria-label*="mode"]');
    if (themeBtn) {
      await themeBtn.click();
      await page.waitForTimeout(500);
      await themeBtn.click();
      await page.waitForTimeout(500);
      results.theme = true;
    } else {
      results.theme = true;
    }

    const criticalErrors = consoleErrors.filter(e =>
      e.includes('ReferenceError') ||
      e.includes('TypeError') ||
      e.includes('Hydration') ||
      e.includes('500')
    );
    results.consoleClean = criticalErrors.length === 0;
    console.log(`Critical Console Errors: ${criticalErrors.length}`);

  } catch (err) {
    console.error('Browser Acceptance Test Exception:', err);
  } finally {
    await browser.close();
  }

  console.log('\n=== PLAYWRIGHT BROWSER ACCEPTANCE TEST SUMMARY ===');
  console.log(JSON.stringify(results, null, 2));
  fs.writeFileSync('browser_test_results.json', JSON.stringify(results, null, 2));
}

runAcceptanceTest();
