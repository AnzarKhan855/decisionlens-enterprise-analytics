const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const OUT_DIR = path.join(__dirname, 'audit_results');
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const ROUTES = [
  { path: '/', name: 'landing_or_home' },
  { path: '/login', name: 'login' },
  { path: '/register', name: 'register' },
  { path: '/forgot-password', name: 'forgot_password' },
  { path: '/reset-password', name: 'reset_password' },
  { path: '/verify-otp', name: 'verify_otp' },
  { path: '/dynamic-dashboard', name: 'dynamic_dashboard' },
  { path: '/forecasts', name: 'forecasts' },
  { path: '/scenario', name: 'scenario' },
  { path: '/strategy', name: 'strategy' },
  { path: '/copilot', name: 'copilot' },
  { path: '/datasets', name: 'datasets' },
  { path: '/upload', name: 'upload' },
  { path: '/explorer', name: 'explorer' },
  { path: '/data-quality', name: 'data_quality' },
  { path: '/lineage', name: 'lineage' },
  { path: '/catalog', name: 'catalog' },
  { path: '/investigate', name: 'investigate' },
  { path: '/decisions', name: 'decisions' },
  { path: '/impact', name: 'impact' },
  { path: '/diagnostics', name: 'diagnostics' },
  { path: '/cybersecurity', name: 'cybersecurity' },
  { path: '/audit', name: 'audit' },
  { path: '/reports', name: 'reports' },
  { path: '/search', name: 'search' },
  { path: '/settings', name: 'settings' },
  { path: '/profile', name: 'profile' },
  { path: '/help', name: 'help' },
  { path: '/architecture', name: 'architecture' },
  { path: '/workspace-structure', name: 'workspace_structure' }
];

const VIEWPORTS = {
  ultrawide: { width: 2560, height: 1440 },
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 375, height: 812 }
};

const TEST_USER = {
  email: 'fortune500_cfo@enterprise.com',
  full_name: 'Sarah Jenkins CFO',
  role: 'ORGANIZATION_ADMIN',
  tenant_id: 'tenant-fortune500_cfo'
};

const TEST_TOKEN = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiZm9ydHVuZTUwMF9jZm9AZW50ZXJwcmlzZS5jb20iLCAicm9sZSI6ICJPUkdBTklaQVRJT05fQURNSU4iLCAiZnVsbF9uYW1lIjogIlNhcmFoIEplbmtpbnMgQ0ZPIiwgInRlbmFudF9pZCI6ICJ0ZW5hbnQtZm9ydHVuZTUwMF9jZm8iLCAiZXhwIjogMTc4ODQyMjc1MX0.0eGCc67u1DqbY53fviTBo8Y4ou5BdP5FClT2hJpOIec';
const TEST_WS = 'test-orlys-enterprise';

async function auditPages() {
  console.log('🚀 Starting DecisionLens Comprehensive Page Audit...');
  const browser = await chromium.launch({ headless: true });
  const auditReport = [];

  for (const route of ROUTES) {
    console.log(`\n======================================================`);
    console.log(`🔍 Inspecting: ${route.path} (${route.name})`);
    console.log(`======================================================`);

    const pageReport = {
      route: route.path,
      name: route.name,
      unauthenticated: {},
      authenticated: {},
      responsiveness: {},
      issues: []
    };

    // --- 1. UNAUTHENTICATED TEST ---
    {
      const context = await browser.newContext({ viewport: VIEWPORTS.desktop });
      const page = await context.newPage();
      const consoleErrors = [];
      const consoleWarns = [];
      const networkFailures = [];

      page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
        if (msg.type() === 'warning') consoleWarns.push(msg.text());
      });
      page.on('pageerror', err => consoleErrors.push(`Uncaught: ${err.message}`));
      page.on('response', resp => {
        if (resp.status() >= 400) {
          networkFailures.push({ url: resp.url(), status: resp.status() });
        }
      });

      const startTime = Date.now();
      let response;
      try {
        response = await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'load', timeout: 10000 });
      } catch (err) {
        console.log(`  [UNAUTH] Navigation timeout or error: ${err.message}`);
      }
      const loadTimeMs = Date.now() - startTime;
      await page.waitForTimeout(1000);

      const currentUrl = page.url();
      const redirectedToLogin = currentUrl.includes('/login');
      const bodyText = await page.innerText('body').catch(() => '');
      const title = await page.title().catch(() => '');

      pageReport.unauthenticated = {
        statusCode: response ? response.status() : 0,
        finalUrl: currentUrl,
        redirectedToLogin,
        loadTimeMs,
        title,
        consoleErrors,
        consoleWarns,
        networkFailures
      };

      await context.close();
    }

    // --- 2. AUTHENTICATED AUDIT (at Desktop 1440x900) ---
    {
      const context = await browser.newContext({ viewport: VIEWPORTS.desktop });
      const page = await context.newPage();
      const consoleErrors = [];
      const consoleWarns = [];
      const networkRequests = [];
      const networkFailures = [];

      page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
        if (msg.type() === 'warning') consoleWarns.push(msg.text());
      });
      page.on('pageerror', err => consoleErrors.push(`Uncaught: ${err.message}`));
      page.on('request', req => networkRequests.push({ url: req.url(), method: req.method() }));
      page.on('response', resp => {
        if (resp.status() >= 400) {
          networkFailures.push({ url: resp.url(), status: resp.status() });
        }
      });

      // Pre-seed auth & workspace in localStorage before navigation
      await page.goto(`${BASE_URL}/login`);
      await page.evaluate(({ token, user, ws }) => {
        localStorage.setItem('decisionlens_access_token', token);
        localStorage.setItem('decisionlens_user', JSON.stringify(user));
        localStorage.setItem('decisionlens_active_workspace', ws);
      }, { token: TEST_TOKEN, user: TEST_USER, ws: TEST_WS });

      const startTime = Date.now();
      let response;
      try {
        response = await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'load', timeout: 12000 });
      } catch (err) {
        console.log(`  [AUTH] Navigation timeout or error: ${err.message}`);
      }
      const loadTimeMs = Date.now() - startTime;
      await page.waitForTimeout(2000); // allow async data fetching

      const screenshotPath = path.join(OUT_DIR, `${route.name}_desktop.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });

      // Deep DOM Inspection
      const pageInspection = await page.evaluate(() => {
        const body = document.body;
        const bodyText = body.innerText || '';

        // Anomaly indicators
        const hasNaN = bodyText.includes('NaN');
        const hasUndefined = bodyText.includes('undefined');
        const hasNull = bodyText.includes('null') && !bodyText.toLowerCase().includes('null hypothesis');
        const hasObjectObject = bodyText.includes('[object Object]');
        const hasTODO = bodyText.includes('TODO') || bodyText.includes('FIXME');

        // Scroll / overflow inspection
        const hasHorizontalScroll = document.documentElement.scrollWidth > document.documentElement.clientWidth;

        // Button inspection
        const buttons = Array.from(document.querySelectorAll('button'));
        const buttonSummary = buttons.map(b => ({
          text: (b.innerText || '').trim().slice(0, 30),
          ariaLabel: b.getAttribute('aria-label'),
          disabled: b.disabled,
          classes: b.className.slice(0, 40)
        }));

        // Link inspection
        const links = Array.from(document.querySelectorAll('a'));
        const linkSummary = links.map(l => ({
          text: (l.innerText || '').trim().slice(0, 30),
          href: l.getAttribute('href')
        }));

        // Input inspection
        const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
        const inputSummary = inputs.map(i => ({
          type: i.getAttribute('type') || i.tagName.toLowerCase(),
          placeholder: i.getAttribute('placeholder'),
          name: i.getAttribute('name'),
          id: i.getAttribute('id'),
          hasLabel: !!document.querySelector(`label[for="${i.id}"]`) || !!i.closest('label')
        }));

        // Chart / SVG / Canvas inspection
        const svgCount = document.querySelectorAll('svg').length;
        const canvasCount = document.querySelectorAll('canvas').length;

        // Heading hierarchy
        const h1Count = document.querySelectorAll('h1').length;
        const h2Count = document.querySelectorAll('h2').length;
        const h3Count = document.querySelectorAll('h3').length;

        // Images missing alt
        const imagesMissingAlt = Array.from(document.querySelectorAll('img:not([alt])')).length;

        return {
          bodyTextLength: bodyText.length,
          hasNaN,
          hasUndefined,
          hasNull,
          hasObjectObject,
          hasTODO,
          hasHorizontalScroll,
          totalButtons: buttons.length,
          buttonSummary: buttonSummary.slice(0, 15),
          totalLinks: links.length,
          linkSummary: linkSummary.slice(0, 15),
          totalInputs: inputs.length,
          inputsMissingLabels: inputSummary.filter(i => !i.hasLabel && i.type !== 'hidden').length,
          svgCount,
          canvasCount,
          h1Count,
          h2Count,
          h3Count,
          imagesMissingAlt
        };
      });

      pageReport.authenticated = {
        statusCode: response ? response.status() : 0,
        loadTimeMs,
        consoleErrors,
        consoleWarns,
        networkRequestsCount: networkRequests.length,
        networkFailures,
        inspection: pageInspection,
        screenshot: `${route.name}_desktop.png`
      };

      console.log(`  ✓ Load time: ${loadTimeMs}ms | Network requests: ${networkRequests.length} | 4xx/5xx: ${networkFailures.length}`);
      console.log(`  ✓ Console errors: ${consoleErrors.length} | Text length: ${pageInspection.bodyTextLength} | Buttons: ${pageInspection.totalButtons}`);
      if (pageInspection.hasNaN) console.log(`  ⚠️ WARNING: Page contains 'NaN' in rendered text!`);
      if (pageInspection.hasUndefined) console.log(`  ⚠️ WARNING: Page contains 'undefined' in rendered text!`);
      if (pageInspection.hasHorizontalScroll) console.log(`  ⚠️ WARNING: Page has horizontal overflow!`);

      // --- 3. RESPONSIVENESS CHECK (Mobile & Tablet) ---
      for (const vpName of ['tablet', 'mobile', 'ultrawide']) {
        await page.setViewportSize(VIEWPORTS[vpName]);
        await page.waitForTimeout(500);

        const responsiveData = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
        }));

        pageReport.responsiveness[vpName] = responsiveData;

        if (responsiveData.hasHorizontalOverflow && vpName === 'mobile') {
          const mobileShot = path.join(OUT_DIR, `${route.name}_mobile_overflow.png`);
          await page.screenshot({ path: mobileShot, fullPage: false });
          pageReport.responsiveness.mobileScreenshot = `${route.name}_mobile_overflow.png`;
          console.log(`  📱 Mobile horizontal overflow detected! (${responsiveData.scrollWidth} > ${responsiveData.clientWidth})`);
        }
      }

      await context.close();
    }

    auditReport.push(pageReport);
  }

  await browser.close();

  const reportFile = path.join(OUT_DIR, 'page_audit_summary.json');
  fs.writeFileSync(reportFile, JSON.stringify(auditReport, null, 2));
  console.log(`\n🎉 Page audit complete! Saved full results to ${reportFile}`);
}

auditPages().catch(err => {
  console.error('Fatal Audit Error:', err);
  process.exit(1);
});
