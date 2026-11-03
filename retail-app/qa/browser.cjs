// Optional reproducible browser smoke test. Requires Playwright and a running
// combined server. Native browser QA is recorded in COMBINED_DEMO_QA.md.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 let inference=0; const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/token',r=>r.fulfill({status:401,json:{}}));
 await page.route('**/api/**/scan/stream',r=>{inference++;return r.abort()});
 await page.route('**/api/scan/stream',r=>{inference++;return r.abort()});
 try{
  await page.goto(process.env.DEMO_URL||'http://127.0.0.1:8001/');
  await page.getByRole('button',{name:'Retail',exact:true}).click();
  await page.getByRole('button',{name:'Open Cereal variants & shelf gaps'}).waitFor();
  assert.equal(await page.locator('img').count(),2);
  await page.getByRole('button',{name:'Open Cereal variants & shelf gaps'}).click();
  await page.getByRole('region',{name:'Shelf product summary'}).waitFor();
  assert.match(await page.getByRole('region',{name:'Shelf product summary'}).innerText(),/21 matched \+ 1 possible \+ 3 not identified = 25/);
  await page.getByRole('textbox',{name:'Search shelf catalogue'}).fill('Chex');
  await page.getByRole('button',{name:'Open photo zoom'}).click();
  await page.getByRole('button',{name:'Zoom in',exact:true}).click();
  await page.getByRole('dialog').getByText('150%').waitFor();
  await page.getByRole('button',{name:'Close photo zoom'}).click();
  await page.getByRole('combobox',{name:'Shelf bay'}).selectOption('bay_drinks');
  await page.getByRole('heading',{name:'Soft drinks & multipacks',exact:true}).waitFor();
  assert.match(await page.getByRole('region',{name:'Shelf product summary'}).innerText(),/18 matched \+ 1 possible \+ 0 not identified = 19/);
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.getByRole('link',{name:'All demos',exact:true}).click();
  await page.getByRole('button',{name:'Bookshelf',exact:true}).click();
  await page.getByRole('button',{name:'Continue with saved samples'}).click();
  await page.getByRole('heading',{name:'Start a shelf check'}).waitFor();
  await page.getByRole('button',{name:'Explore a sample'}).click();
  await page.getByRole('region',{name:'Shelf title summary'}).waitFor();
  assert.equal(inference,0); assert.deepEqual(errors,[]);
  console.log('Combined demo smoke checks passed; zero inference requests.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
