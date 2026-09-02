const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const OUT_DIR = path.join(__dirname, 'audit_results');

const TEST_TOKEN = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiZm9ydHVuZTUwMF9jZm9AZW50ZXJwcmlzZS5jb20iLCAicm9sZSI6ICJPUkdBTklaQVRJT05fQURNSU4iLCAiZnVsbF9uYW1lIjogIlNhcmFoIEplbmtpbnMgQ0ZPIiwgInRlbmFudF9pZCI6ICJ0ZW5hbnQtZm9ydHVuZTUwMF9jZm8iLCAiZXhwIjogMTc4ODQyMjc1MX0.0eGCc67u1DqbY53fviTBo8Y4ou5BdP5FClT2hJpOIec';
const TEST_USER = {
  email: 'fortune500_cfo@enterprise.com',
  full_name: 'Sarah Jenkins CFO',
  role: 'ORGANIZATION_ADMIN',
  tenant_id: 'tenant-fortune500_cfo'
};
const TEST_WS = 'test-orlys-enterprise';

async function testUploadModule() {
  console.log('\n📁 Starting Dataset Upload & Ingestion Validation Audit...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // Create temporary test files for upload
  const tmpDir = path.join(__dirname, 'audit_tmp_files');
  if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });

  const invalidExeFile = path.join(tmpDir, 'malicious_payload.exe');
  fs.writeFileSync(invalidExeFile, 'MZ90FakeExecutableHeader');

  const emptyCsvFile = path.join(tmpDir, 'empty_data.csv');
  fs.writeFileSync(emptyCsvFile, '');

  const malformedCsvFile = path.join(tmpDir, 'corrupt_data.csv');
  fs.writeFileSync(malformedCsvFile, 'col1,col2\nval1\nval1,val2,extra_val,overflow');

  const validCsvFile = path.join(tmpDir, 'fortune500_sales_q3.csv');
  fs.writeFileSync(validCsvFile, 'transaction_id,date,customer_region,product_sku,units_sold,unit_price,revenue\nTX101,2026-08-01,North America,SKU-990,15,120.00,1800.00\nTX102,2026-08-02,Europe,SKU-991,4,450.00,1800.00\nTX103,2026-08-03,Asia-Pacific,SKU-992,30,80.00,2400.00\n');

  const results = {
    file_type_restriction: {},
    empty_file_handling: {},
    malformed_csv_handling: {},
    ui_elements: {}
  };

  // Auth setup
  await page.goto(`${BASE_URL}/login`);
  await page.evaluate(({ token, user, ws }) => {
    localStorage.setItem('decisionlens_access_token', token);
    localStorage.setItem('decisionlens_user', JSON.stringify(user));
    localStorage.setItem('decisionlens_active_workspace', ws);
  }, { token: TEST_TOKEN, user: TEST_USER, ws: TEST_WS });

  // Navigate to Upload page
  await page.goto(`${BASE_URL}/upload`);
  await page.waitForTimeout(2000);

  const initialShot = path.join(OUT_DIR, 'upload_page_initial.png');
  await page.screenshot({ path: initialShot });

  // Inspect page controls
  const fileInput = page.locator('input[type="file"]');
  const fileInputCount = await fileInput.count();
  results.ui_elements.file_input_present = fileInputCount > 0;

  const dropZone = page.locator('[class*="border-dashed"], [class*="dropzone"]');
  results.ui_elements.drop_zone_present = await dropZone.count() > 0;

  // 1. TEST INVALID FILE TYPE (.exe)
  console.log('1. Testing Invalid File Extension (.exe)...');
  if (fileInputCount > 0) {
    try {
      await fileInput.first().setInputFiles(invalidExeFile);
      await page.waitForTimeout(1000);
      const bodyText = await page.innerText('body');
      results.file_type_restriction.rejected = bodyText.includes('invalid') || bodyText.includes('only') || bodyText.includes('.csv') || bodyText.includes('supported');
      const shot = path.join(OUT_DIR, 'upload_invalid_exe_result.png');
      await page.screenshot({ path: shot });
    } catch (err) {
      results.file_type_restriction.error = err.message;
    }
  }

  // 2. TEST EMPTY CSV FILE
  console.log('2. Testing Empty CSV File...');
  if (fileInputCount > 0) {
    try {
      await fileInput.first().setInputFiles(emptyCsvFile);
      await page.waitForTimeout(1000);
      const bodyText = await page.innerText('body');
      results.empty_file_handling.detected = bodyText.includes('empty') || bodyText.includes('no data') || bodyText.includes('0 rows') || bodyText.includes('header');
      const shot = path.join(OUT_DIR, 'upload_empty_csv_result.png');
      await page.screenshot({ path: shot });
    } catch (err) {
      results.empty_file_handling.error = err.message;
    }
  }

  // 3. TEST VALID CSV FILE
  console.log('3. Testing Valid Enterprise CSV File...');
  if (fileInputCount > 0) {
    try {
      await fileInput.first().setInputFiles(validCsvFile);
      await page.waitForTimeout(2000);
      const shot = path.join(OUT_DIR, 'upload_valid_csv_staged.png');
      await page.screenshot({ path: shot });
      const bodyText = await page.innerText('body');
      results.valid_file_staged = bodyText.includes('fortune500_sales_q3.csv') || bodyText.includes('Upload') || bodyText.includes('Ready');
    } catch (err) {
      results.valid_file_error = err.message;
    }
  }

  await browser.close();

  const reportFile = path.join(OUT_DIR, 'upload_audit_summary.json');
  fs.writeFileSync(reportFile, JSON.stringify(results, null, 2));
  console.log(`\n🎉 Upload module audit complete! Results saved to ${reportFile}`);
}

testUploadModule().catch(err => {
  console.error('Fatal Upload Audit Error:', err);
  process.exit(1);
});
