// Local recorded-response UI check. No company requests or new inference.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const url = process.env.SHELF_CHECK_URL || 'http://127.0.0.1:8905';
const output = path.join(root, 'qa/clear-results');
fs.mkdirSync(output, { recursive: true });
(async () => {
 const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
 try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1100 } });
  const errors = []; let inference = 0;
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/token', r => r.fulfill({ json: {} }));
  await page.route('**/api/scan/stream', r => { inference++; return r.abort(); });
  const upload = await page.request.post(`${url}/api/uploads?filename=recorded-shelf.jpg`, { headers: { 'Content-Type': 'image/jpeg' }, data: fs.readFileSync(path.join(root, 'app/public/photos/e.jpg')) });
  assert.equal(upload.status(), 201);
  const photo = await upload.json();
  for (const firstPass of [false, true]) {
   const expected = JSON.parse(execFileSync(process.env.PYTHON || path.join(root,'.venv/bin/python'), ['-c', `
import json,sys
from pathlib import Path
from server.main import get_store
from server.recognition import reprocess_audit
from server.comparison import compare_books
from server.uploads import save_analysis
photo=json.loads(sys.argv[1]); first=sys.argv[2]=='true'
store=get_store(); bay=next(b for b in store['bays'] if b['id']=='bay_f1')
audit=json.loads(Path('qa/fixtures/live_e_replies.json').read_text())['audit']
result=dict(bay_id=bay['id'],bay_code=bay['code'],bay_name=bay['name'],photo_url=photo['photo_url'],photo_filename='recorded-shelf.jpg',upload_id=photo['upload_id'],source_kind='upload',mode='live',model='recorded-fixture',effort='high',scanned_at=None,inference_duration_seconds=None,tokens_used=None,estimated_cost_usd=None,**compare_books(store,bay,reprocess_audit(audit,first_pass_only=first),reading_mode='single_pass' if first else 'verified'))
save_analysis(photo['upload_id'],bay['id'],result)
assigned={x['sku'] for x in result['planogram_items']}
matched={x['sku'] for x in result['shelf_items'] if x.get('sku') in assigned and x['status']=='matched'}
possible={x['sku'] for x in result['shelf_items'] if x.get('sku') in assigned and x.get('catalogue_status')=='matched'}-matched
print(json.dumps([len(matched),len(possible),len(assigned-matched-possible),len(assigned)]))
`, JSON.stringify(photo), String(firstPass)], { cwd: root, encoding: 'utf8' }));
   await page.goto(`${url}/analysis?bay=bay_f1&upload=${photo.upload_id}`);
   const gate = page.getByRole('button', { name: 'Continue with saved samples' });
   if (await gate.isVisible()) await gate.click();
   // The auth gate may still be resolving its mocked session.
   await Promise.race([page.getByLabel('Shelf title summary').waitFor(), gate.waitFor().then(() => gate.click())]);
   const summary = page.getByLabel('Shelf title summary');
   await summary.waitFor();
   assert.deepEqual(await summary.locator('dd').allTextContents(), expected.slice(0,3).map(String));
   assert.equal(expected.slice(0,3).reduce((a,b)=>a+b,0), expected[3]);
   assert.doesNotMatch(await page.locator('body').innerText(), /\d+ open checks|title candidates|\d+%|units\/day|SKU-/);
   const before = await summary.innerText();
   await page.locator('article button').first().click();
   assert.equal(await summary.innerText(), before);
   await page.getByRole('button', { name: 'Reviewed', exact: true }).click();
   await page.getByText('Reviewed in this demo session', { exact: true }).waitFor();
   await page.getByRole('button', { name: 'All', exact: true }).last().click();
   for (const [name,width,height] of [['desktop',1500,1100],['mobile',390,844]]) {
    await page.setViewportSize({width,height});
    await page.evaluate(() => window.scrollTo(0,0));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    await page.screenshot({path:path.join(output,`${firstPass?'single':'verified'}-${name}.png`),fullPage:true});
   }
   await page.setViewportSize({width:1500,height:1100});
   console.log('PASS',firstPass?'single pass':'verified',expected);
  }
  assert.equal(inference,0); assert.deepEqual(errors,[]);
  console.log('PASS no paid calls, stable counts on review, desktop/mobile layout');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
