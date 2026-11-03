"""Build two reproducible manual samples; no inference and no invented stockouts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'app/public'
DATA = ROOT / 'data'

# Coordinates are representative package regions (x0,y0,x1,y1), fractions of
# the original photo. They are manual estimates, never a physical facing count.
# None means a catalogue identity visible only in top overstock was not
# transcribed into this deliberately partial saved reading.
CEREAL = [
 ('Blueberry Chex', 'General Mills', 'Carton', (.00,.11,.10,.29)),
 ('Chocolate Chex', 'General Mills', 'Carton', (.127,.134,.225,.285)),
 ('Cinnamon Chex', 'General Mills', 'Carton', (.227,.14,.317,.285)),
 ('Honey Nut Chex', 'General Mills', 'Carton', (.318,.111,.414,.284)),
 ('Wheat Squares', 'Great Value', 'Carton', (.411,.139,.483,.284)),
 ('Wheat Chex', 'General Mills', 'Carton', (.484,.14,.554,.282)),
 ('Crispix Original', 'Kellogg’s', 'Carton', (.574,.076,.663,.282)),
 ('Cracklin’ Oat Bran', 'Kellogg’s', 'Carton', (.735,.129,.815,.283)),
 ('Wheaties', 'General Mills', 'Carton', (.895,.098,.988,.28)),
 ('Raisin Bran', 'Kellogg’s', 'Carton', (.00,.374,.06,.525)),
 ('Rice Chex', 'General Mills', 'Carton', (.155,.337,.26,.525)),
 ('Rice Squares', 'Great Value', 'Carton', (.275,.358,.363,.524)),
 ('Cheerios Oat Crunch Cinnamon', 'General Mills', 'Carton', (.457,.337,.557,.523)),
 ('Maple Cheerios', 'General Mills', 'Carton', (.681,.336,.79,.523)),
 ('Toasted O’s', 'Great Value', 'Carton', (.906,.32,1,.52)),
 ('Corn Chex', 'General Mills', 'Carton', (.007,.574,.13,.773)),
 ('Corn Squares', 'Great Value', 'Carton', (.22,.597,.312,.764)),
 ('Multi-Grain O’s', 'Great Value', 'Carton', (.484,.577,.573,.761)),
 ('Multi Grain Cheerios', 'General Mills', 'Carton', (.573,.577,.657,.744)),
 ('Rice Krispies', 'Kellogg’s', 'Carton', (.00,.791,.082,.999)),
 ('Life Original', 'Quaker', 'Carton', (.327,.807,.407,.994)),
 ('Cheerios Original', 'General Mills', 'Carton', (.69,.806,.788,.997)),
 ('Rice Crisps', 'Great Value', 'Carton', None),
 ('Crunchy Raisin Bran', 'Great Value', 'Carton', None),
 ('Life Cinnamon', 'Quaker', 'Carton', None),
]
DRINKS = [
 ('Coca-Cola Original Taste', 'Coca-Cola', 'Plastic bottle', (.273,.047,.324,.232)),
 ('Coca-Cola Cherry', 'Coca-Cola', 'Plastic bottle', (.926,.042,.984,.226)),
 ('Monster Energy Original', 'Monster Energy', 'Can', (.211,.305,.28,.348)),
 ('Monster Energy — silver can', 'Monster Energy', 'Can · variant unconfirmed', (.078,.307,.14,.347)),
 ('Coca-Cola Zero Sugar Mini', 'Coca-Cola', '10 × 7.5 fl oz cans', (.053,.449,.102,.505)),
 ('Sprite Mini', 'Sprite', '10 × 7.5 fl oz cans', (.358,.446,.407,.504)),
 ('Fanta Orange Mini', 'Fanta', '10 × 7.5 fl oz cans', (.758,.444,.809,.504)),
 ('Coca-Cola Georgia Peach', 'Coca-Cola', 'Glass bottle multipack', (.027,.673,.088,.792)),
 ('Coca-Cola California Raspberry', 'Coca-Cola', 'Glass bottle multipack', (.088,.67,.144,.791)),
 ('Coca-Cola Original Taste', 'Coca-Cola', '6-bottle glass multipack', (.145,.679,.227,.793)),
 ('Coca-Cola Life', 'Coca-Cola', 'Glass bottle multipack', (.386,.665,.448,.805)),
 ('Sprite', 'Sprite', 'Glass bottle multipack', (.511,.669,.589,.797)),
 ('Coca-Cola Original Taste', 'Coca-Cola', 'Can carton · count unconfirmed', (.358,.86,.415,.933)),
 ('Coca-Cola Life', 'Coca-Cola', 'Can carton · count unconfirmed', (.481,.863,.535,.932)),
 ('Coca-Cola Cherry', 'Coca-Cola', 'Can carton · count unconfirmed', (.581,.865,.636,.933)),
 ('Coca-Cola Orange Vanilla', 'Coca-Cola', 'Can carton · count unconfirmed', (.703,.866,.757,.931)),
 ('Coca-Cola Vanilla', 'Coca-Cola', 'Can carton · count unconfirmed', (.762,.867,.824,.948)),
 ('Coca-Cola Zero Sugar', 'Coca-Cola', 'Can carton · count unconfirmed', (.826,.865,.939,.939)),
 ('Aquafina', 'Aquafina', 'Water case · 32 bottles', (.27,.59,.501,.664)),
]

REVIEW = {
 'Raisin Bran': 'The carton is cut off at the left edge. Confirm the full product name and variant.',
 'Monster Energy — silver can': 'The can is turned sideways. The exact silver-can variant is not readable; no Ultra variant is assumed.',
}

def write(path, obj):
 path.parent.mkdir(parents=True, exist_ok=True)
 path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def build():
 catalogue = {}; bays=[]; scans={}; sources=[]; records=[]
 for bay_id, code, name, photo, section, rows in [
  ('bay_cereal','R-01','Cereal variants & shelf gaps','01_cereal_variants_and_gaps.jpg','Cereal names and variants · repeated cartons count once',CEREAL),
  ('bay_drinks','R-02','Soft drinks & multipacks','02_soft_drinks_and_multipacks.jpg','Bottles, mini cans, glass multipacks & can cartons',DRINKS),
 ]:
  path=PUBLIC/'retail-photos'/photo
  sources.append({'filename':photo,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'width':4032,'height':3024})
  items=[]; shelf=[]; tasks=[]
  for i,(title,brand,pack,region) in enumerate(rows,1):
   sku=f'{code}-{i:03}'
   # Scenario quantities are per retail selling unit: one carton, bottle,
   # multipack, or case as listed. Never multiply them by contained cans.
   on_hand=12 if bay_id=='bay_cereal' else 8
   item=dict(sku=sku,title=f'{title} · {pack}' if bay_id=='bay_drinks' else title,author=f'{brand} · {pack}' if bay_id=='bay_cereal' else brand,
     assigned_bay_id=bay_id,price=None,sales_velocity_units_per_day=None,simulated_on_hand=on_hand,
     system_status='simulated',physically_on_shelf=None,
     brand=brand,product_name=title,package_format=pack,size=None,gtin=None,expected_facings=None,
     inventory_unit='one retail selling unit',data_mode='simulated')
   catalogue[sku]=item;items.append(item)
   reason=REVIEW.get(title)
   # Lower can cartons are partly cut by the image edge; package count stays
   # unconfirmed in the catalogue even when name + carton format are clear.
   records.append({**item,'sample_region':region,'manual_status':'not_transcribed' if region is None else 'needs_review' if reason else 'matched',
     'review_reason':reason,'evidence_scope':'Main front shelves; top overstock names are catalogue-only in this partial sample.' if bay_id=='bay_cereal' else 'Readable foreground packages and the Aquafina case. Other background items are outside the curated catalogue.'})
   if region is None:
    tasks.append(dict(id='unseen-'+sku,type='missing_item',severity='medium',badge='Not identified',title=item['title'],author=brand,sku=sku,
     headline='This product name appears in top overstock, but is not transcribed in the saved front-shelf readings. This is not a stockout.',suggested_action='Mark photo check reviewed',requires_review=True))
    continue
   x0,y0,x1,y1=region
   obs=dict(id='manual-'+sku,title=item['title'],author=brand,confidence=None,sku=sku,
     box=dict(top=y0,left=x0,width=x1-x0,height=y1-y0),box_source='manual_estimate',verification_status='manual',
     visible_text=title.replace(' — silver can',''),title_status='uncertain' if reason else 'single_read',position_status='estimated',
     catalogue_title=item['title'],catalogue_status='matched',status='needs_review' if reason else 'matched',
     status_label='Possible product match' if reason else 'Matched product name & format',review_reasons=[reason] if reason else [])
   shelf.append(obs)
   if reason:
    tasks.append(dict(id='review-'+sku,type='recognition_review',severity='medium',badge='Product identity',title=item['title'],author=brand,sku=sku,
     shelf_item_id=obs['id'],headline=reason,suggested_action='Mark identity check reviewed',requires_review=True))
  tasks.append(dict(id='gap-'+bay_id,type='record_error',severity='medium',badge='Shelf gap check',title='Visible shelf gaps',author=None,
    headline='Empty shelf space is visible. Check the intended shelf layout and nearby packages in person before assigning a missing product or changing a stock record.',suggested_action='Mark shelf gap check reviewed',requires_review=True))
  matched=sum(o['status']=='matched' for o in shelf);possible=len(shelf)-matched
  bays.append(dict(id=bay_id,code=code,name=name,photo=photo,aisle='Retail demo',section='Cereals' if bay_id=='bay_cereal' else 'Soft drinks',description=section,difficulty='retail',scannable=True,status='action_needed',
    expected_items_count=len(items),catalogue_skus=[o['sku'] for o in items]))
  scans[bay_id]=dict(bay_id=bay_id,bay_code=code,bay_name=name,photo_filename=photo,photo_url='/retail-photos/'+photo,mode='replay',source_kind='sample',
    model='Manual visual transcription',effort='Not applicable',scanned_at=None,inference_duration_seconds=None,tokens_used=None,estimated_cost_usd=None,
    disclosure='Partial manual development annotations, not an AI run or independent ground truth. Identity means visible product name, variant and package format, not a verified retailer SKU. On-hand quantities are simulated selling units. Prices, sales rates, exact sizes, slot compliance and total physical stock are unknown.',
    metrics=dict(planogram_expected_items=len(items),shelf_items_detected=len(shelf),matched_count=matched,missing_count=len(items)-len(shelf),misplaced_count=0,review_count=possible,planogram_compliance_pct=None),
    planogram_items=items,shelf_items=shelf,missing_items=[],misplaced_items=[],action_tasks=tasks)
 store=dict(store_name='Retail Shelf Check',store_id='retail-demo',description='Two supplied grocery shelf photos',disclaimer='Simulated inventory; partial manual readings. No retailer integration.',total_bays=2,scannable_bays_count=2,
   bays=bays,catalogue=catalogue,initial_inventory={sku:p['simulated_on_hand'] for sku,p in catalogue.items()},
   summary=dict(on_shelf_availability_pct=None,open_exceptions_total=sum(len(s['action_tasks']) for s in scans.values()),bays_scanned_today=0))
 write(PUBLIC/'data/retail/store.json',store)
 for bay,scan in scans.items(): write(PUBLIC/f'data/retail/scans/{bay}.json',scan)
 write(DATA/'retail-inventory.json',dict(schema_version='2.0',granularity='product name + visible variant + package format; not exact retailer SKU',
   inventory_policy='12 cereal selling units or 8 beverage selling units per internal ID, simulated uniformly for the scenario. Not derived from photograph counts. No prices or sales rates supplied.',
   annotation_policy='Partial manual transcription. One representative package location per identity. Unreadable attributes are null or explicitly unconfirmed. Repeated facings do not increase unique-product totals.',sources=sources,products=records))
 print(json.dumps({bay:scan['metrics'] for bay,scan in scans.items()},indent=2))

if __name__=='__main__': build()
