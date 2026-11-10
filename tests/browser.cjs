'use strict';
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    const response = await page.goto(process.argv[2], { waitUntil: 'networkidle' });
    assert.ok(response.ok());
    const output = path.resolve(__dirname, '../reports/screenshots', process.argv[4]);
    fs.mkdirSync(output, { recursive: true });
    await page.getByRole('button', {name:'Login', exact:true}).waitFor();
    await page.screenshot({path:path.join(output,'login.png'),fullPage:true});
    await page.getByLabel('Username', {exact:true}).fill('admin');
    await page.getByLabel('Password', {exact:true}).fill(fs.readFileSync(process.argv[3], 'utf8'));
    await page.getByRole('button', {name:'Login', exact:true}).click();
    await page.waitForURL(url => !url.pathname.includes('login'));
    await page.waitForLoadState('networkidle');
    assert.equal(await page.getByRole('button', {name:'Login', exact:true}).count(), 0);
    assert.match(await page.locator('body').innerText(), /Containers|Dashboard|Watchers/i);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false);
    await page.screenshot({path:path.join(output,'dashboard.png'),fullPage:true});
    assert.deepEqual(errors, []);
    console.log('PASS: browser login, dashboard, no page errors or horizontal overflow');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
