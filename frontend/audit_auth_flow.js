const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const OUT_DIR = path.join(__dirname, 'audit_results');

async function testAuthFlow() {
  console.log('\n🔒 Starting Deep Authentication & Session Security Audit...');
  const browser = await chromium.launch({ headless: true });
  const results = {
    login_validation: {},
    login_valid_admin: {},
    remember_me: {},
    registration_edge_cases: {},
    forgot_password: {},
    logout_flow: {},
    route_protection: {}
  };

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => consoleErrors.push(`Uncaught: ${err.message}`));

  // 1. LOGIN FORM VALIDATION
  console.log('1. Testing Login Form Validation & Bad Credentials...');
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(1000);

  // Submit empty
  const submitBtn = page.locator('button[type="submit"]');
  if (await submitBtn.count() > 0) {
    await submitBtn.click();
    await page.waitForTimeout(500);
    const bodyEmpty = await page.innerText('body');
    results.login_validation.empty_submit_handled = bodyEmpty.includes('required') || bodyEmpty.includes('Invalid') || bodyEmpty.includes('Enter');
  }

  // Submit invalid email
  const emailInput = page.locator('input[type="email"], input[name="email"]');
  const pwdInput = page.locator('input[type="password"], input[name="password"]');

  if (await emailInput.count() > 0) {
    await emailInput.fill('invalid-email-string');
    await pwdInput.fill('somepass');
    await submitBtn.click();
    await page.waitForTimeout(500);
    const html5Valid = await emailInput.evaluate(el => el.checkValidity());
    results.login_validation.html5_email_validation = !html5Valid;
  }

  // Submit wrong credentials
  if (await emailInput.count() > 0) {
    await emailInput.fill('nonexistent_user@enterprise.com');
    await pwdInput.fill('WrongPassword123!');
    await submitBtn.click();
    await page.waitForTimeout(1500);
    const bodyWrong = await page.innerText('body');
    results.login_validation.wrong_credentials_error_shown = bodyWrong.includes('Invalid') || bodyWrong.includes('credentials') || bodyWrong.includes('401');
    const shot = path.join(OUT_DIR, 'login_wrong_credentials.png');
    await page.screenshot({ path: shot });
  }

  // 2. VALID LOGIN (ORGANIZATION ADMIN)
  console.log('2. Testing Valid Login for Organization Admin...');
  // Click Org Admin role toggle
  const orgAdminBtn = page.locator('button:has-text("Org Admin")');
  if (await orgAdminBtn.count() > 0) {
    await orgAdminBtn.click();
  }
  await emailInput.fill('fortune500_cfo@enterprise.com');
  await pwdInput.fill('Fortune500Secure!2026');
  await Promise.all([
    page.waitForURL('**/dynamic-dashboard', { timeout: 8000 }).catch(() => null),
    submitBtn.click()
  ]);
  await page.waitForTimeout(1500);

  const postLoginUrl = page.url();
  console.log(`  Redirected after login to: ${postLoginUrl}`);
  results.login_valid_admin.redirect_url = postLoginUrl;
  results.login_valid_admin.success = !postLoginUrl.includes('/login');

  // Check storage tokens
  const storageState = await page.evaluate(() => ({
    token: localStorage.getItem('decisionlens_access_token'),
    user: localStorage.getItem('decisionlens_user'),
    workspace: localStorage.getItem('decisionlens_active_workspace')
  }));
  results.login_valid_admin.token_stored = !!storageState.token;
  results.login_valid_admin.user_stored = !!storageState.user;
  results.login_valid_admin.active_workspace = storageState.workspace;

  // 3. LOGOUT FLOW
  console.log('3. Testing Logout Flow & State Clearance...');
  const logoutBtn = page.locator('button:has-text("Logout"), button:has-text("Sign Out"), a:has-text("Logout"), a:has-text("Sign Out")');
  if (await logoutBtn.count() > 0) {
    await logoutBtn.first().click();
    await page.waitForTimeout(2000);
    const postLogoutUrl = page.url();
    const postLogoutStorage = await page.evaluate(() => ({
      token: localStorage.getItem('decisionlens_access_token'),
      user: localStorage.getItem('decisionlens_user')
    }));
    results.logout_flow.redirect_url = postLogoutUrl;
    results.logout_flow.token_cleared = !postLogoutStorage.token;
    results.logout_flow.user_cleared = !postLogoutStorage.user;
  } else {
    results.logout_flow.button_found = false;
    console.log('  ⚠️ Logout button not immediately visible in main view.');
  }

  // 4. ROUTE PROTECTION CHECK (UNAUTHENTICATED)
  console.log('4. Checking Route Protection for Unauthenticated Visitors...');
  // Explicitly clear all storage
  await page.evaluate(() => localStorage.clear());

  const protectedRoutes = ['/dynamic-dashboard', '/datasets', '/settings', '/reports', '/strategy', '/cybersecurity'];
  for (const r of protectedRoutes) {
    await page.goto(`${BASE_URL}${r}`);
    await page.waitForTimeout(1500);
    const currentUrl = page.url();
    const body = await page.innerText('body').catch(() => '');
    const isLeakingData = body.includes('Revenue') || body.includes('Audit Log') || body.includes('Workspace');
    results.route_protection[r] = {
      finalUrl: currentUrl,
      redirectedToLogin: currentUrl.includes('/login'),
      leakedData: isLeakingData
    };
    if (!currentUrl.includes('/login')) {
      console.log(`  🚨 SECURITY CONCERN: Route ${r} did NOT redirect to /login! Final URL: ${currentUrl}`);
    }
  }

  // 5. REGISTRATION VALIDATION
  console.log('5. Testing Registration Page Validation...');
  await page.goto(`${BASE_URL}/register`);
  await page.waitForTimeout(1000);

  const regSubmit = page.locator('button[type="submit"]');
  if (await regSubmit.count() > 0) {
    await regSubmit.click();
    await page.waitForTimeout(500);
    const regBody = await page.innerText('body');
    results.registration_edge_cases.empty_submit_blocked = regBody.includes('required') || regBody.includes('fill') || regBody.includes('enter');
  }

  // 6. FORGOT PASSWORD FLOW
  console.log('6. Testing Forgot Password Page...');
  await page.goto(`${BASE_URL}/forgot-password`);
  await page.waitForTimeout(1000);

  const fpEmail = page.locator('input[type="email"], input[name="email"]');
  const fpSubmit = page.locator('button[type="submit"]');
  if (await fpEmail.count() > 0 && await fpSubmit.count() > 0) {
    await fpEmail.fill('fortune500_cfo@enterprise.com');
    await fpSubmit.click();
    await page.waitForTimeout(2000);
    const fpBody = await page.innerText('body');
    results.forgot_password.response_handled = fpBody.includes('sent') || fpBody.includes('link') || fpBody.includes('reset') || fpBody.includes('email');
    const shot = path.join(OUT_DIR, 'forgot_password_result.png');
    await page.screenshot({ path: shot });
  }

  await browser.close();

  const reportFile = path.join(OUT_DIR, 'auth_audit_summary.json');
  fs.writeFileSync(reportFile, JSON.stringify(results, null, 2));
  console.log(`🎉 Auth audit complete! Results saved to ${reportFile}`);
}

testAuthFlow().catch(err => {
  console.error('Fatal Auth Audit Error:', err);
  process.exit(1);
});
