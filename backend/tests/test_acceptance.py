"""Testy reguł akceptacyjnych od formularza API do relacyjnego zapisu."""
import io,zipfile
from decimal import Decimal
from sqlalchemy import select,func
from app.domain import ocen_charakterystyke,generuj_symulacje,wyznacz_badania_cykliczne,oblicz_granice_kontrolne
from app.models import *
from app.services import enqueue_alerts
from app.security import hasher
from conftest import setup_order,save,authorize
import pytest,openpyxl

def test_three_measurements(client,spec):
    a,o,p=setup_order(client,spec);r=save(client,o,p,['3.1','3.4','3.5']);assert r.status_code==200,r.text;assert r.json()['ok'] is True
    with Session() as db:
        result=db.scalar(select(Result));assert abs(Decimal(result.average)-Decimal(10)/3)<Decimal('1e-25');assert db.scalar(select(func.count()).select_from(Measurement))==3

def test_ten_measurements_rejects_nine(client,spec):
    spec={**spec,'count':10,'labels':[str(i) for i in range(10)]};a,o,p=setup_order(client,spec)
    assert save(client,o,p,['3.5']*9).status_code==422
    with Session() as db:assert db.scalar(select(func.count()).select_from(LabSession))==0;assert db.get(Article,a['id']).cycle==0
    assert save(client,o,p,['3.5']*10).status_code==200

def test_individual_warning_mean_ok(client,spec):
    a,o,p=setup_order(client,spec)
    assert save(client,o,p,['3.1','3.4','3.5'],False).status_code==422
    assert save(client,o,p,['3.1','3.4','3.5']).json()['ok'] is True
    authorize(client,'real');r=client.get('/api/results/real').json()[0]['results'][0]
    assert r['individual_ok']==[False,True,True] and r['ok'] is True

def test_nok_can_be_saved(client,spec):
    a,o,p=setup_order(client,spec)
    assert save(client,o,p,['4','4','4'],False).status_code==422
    r=save(client,o,p,['4','4','4']);assert r.status_code==200 and r.json()['ok'] is False

def test_tenth_cycle_mandatory(client,spec):
    extra={**spec,'key':'adhesion','name':'Adhezja','frequency':'nth','every_n':10,'count':10,'labels':[str(i) for i in range(10)]}
    a=client.post('/api/articles',json={'code':'CYCLE','name':'Cyclic','specs':[spec,extra]}).json()
    with Session() as db:db.get(Article,a['id']).cycle=9;db.commit()
    o=client.post('/api/orders',json={'article_id':a['id'],'lot':'TEN'}).json();p=client.get(f"/api/orders/{o['id']}/plan").json()
    assert p['cycle']==10 and len(p['specs'])==2
    assert save(client,o,p,['3.5']*3).status_code==422
    data={'order_id':o['id'],'config_id':p['config_id'],'cycle':10,'test_date':'2026-10-22','values':{'thickness':['3.5']*3,'adhesion':['3.5']*9}}
    assert client.post('/api/sessions',json=data).status_code==422
    data['values']['adhesion'].append('3.5');assert client.post('/api/sessions',json=data).status_code==200

def test_order_multiple_sessions(client,spec):
    a,o,p=setup_order(client,spec,required_sessions=2);assert save(client,o,p,['3.5']*3).json()['order_status']=='IN_PROGRESS'
    p=client.get(f"/api/orders/{o['id']}/plan").json();assert save(client,o,p,['3.5']*3).json()['order_status']=='TESTED'

def test_hold_preserves_laboratory_result(client,spec):
    a,o,p=setup_order(client,spec);save(client,o,p,['3.5']*3)
    r=client.post(f"/api/orders/{o['id']}/disposition",json={'held':True,'reason':'Kontrola dyspozycji'});assert r.json()['status']=='HELD'
    with Session() as db:assert db.scalar(select(LabSession)).ok is True;assert db.scalar(select(Disposition)).reason=='Kontrola dyspozycji'
    assert client.post(f"/api/orders/{o['id']}/disposition",json={'held':False,'reason':'Weryfikacja zakończona'}).json()['status']=='TESTED'

def test_simulation_individual_and_mean(client,spec):
    a,o,p=setup_order(client,spec);save(client,o,p,['3.5','3.9','3.1']);authorize(client,'simulated')
    r=client.get('/api/results/simulated').json()[0]
    assert r['label']=='SIMULATED DATA';assert r['results'][0]['values']==['3.5','3.770','3.230']
    assert Decimal(r['results'][0]['average'])==Decimal('3.5')
    with Session() as db:assert [m.value for m in db.scalars(select(Measurement).order_by(Measurement.position))]==['3.5','3.9','3.1']

def test_recover_sources_and_protection(client,spec):
    a,o,p=setup_order(client,spec);s=save(client,o,p,['3.1']*3).json()
    for src in ('real','simulated'):
        assert client.get(f"/api/results/{src}/{s['id']}").status_code==428
        authorize(client,src);r=client.get(f"/api/results/{src}/{s['id']}").json();assert r['source']==src and r['lot']=='LOT-01'

def test_roles_block_api_export_and_spc(client,spec):
    with Session() as db:db.add(User(login='tech',password=hasher.hash('Test_password_123'),role='technician'));db.commit()
    r=client.post('/api/login',json={'login':'tech','password':'Test_password_123'});client.headers['x-csrf-token']=r.json()['csrf']
    for endpoint in ('/api/results/real','/api/results/simulated','/api/export/real','/api/history','/api/spc/configs'):
        assert client.get(endpoint).status_code==403
    assert client.post('/api/reauth',json={'scope':'real','password':'Test_password_123'}).status_code==403

def test_spc_alert_outbox_deduplication(client,spec):
    a,o,p=setup_order(client,spec);cid=p['specs'][0]['id'];authorize(client,'spc')
    r=client.post('/api/spc/configs',json={'characteristic_id':cid,'sampling_plan':'Trzy próbki pobrane w jednym cyklu po walidacji planu.','n':3,'cl':3.4,'lcl':3.3,'ucl':3.6,'rcl':.1,'rlcl':0,'rucl':.3});assert r.status_code==200,r.text
    assert client.post('/api/notifications',json={'characteristic_id':cid,'email':'qa@example.invalid','events':['UCL'],'enabled':True}).status_code==200
    r=save(client,o,p,['3.7']*3);assert r.status_code==200,r.text
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Alert))==1;assert db.scalar(select(func.count()).select_from(Outbox))==1
        enqueue_alerts(db,db.get(LabSession,r.json()['id']));db.commit();assert db.scalar(select(func.count()).select_from(Outbox))==1

def test_simulated_never_alerts_or_changes_order(client,spec):
    a,o,p=setup_order(client,spec);r=save(client,o,p,['4']*3);authorize(client,'simulated');client.get('/api/results/simulated')
    with Session() as db:
        assert db.scalar(select(LabSession)).ok is False;assert db.get(Order,o['id']).status=='TESTED';assert db.scalar(select(func.count()).select_from(Outbox))==0

def test_excel_export_highlight_no_suffix(client,spec):
    a,o,p=setup_order(client,spec);sid=save(client,o,p,['3.1','3.4','3.5']).json()['id'];authorize(client,'real')
    for path in ('/api/export/real',f'/api/export/real?session_id={sid}'):
        r=client.get(path);assert r.status_code==200
        w=openpyxl.load_workbook(io.BytesIO(r.content),data_only=False);cells=[c for ws in w for row in ws for c in row if c.value is not None]
        assert any(c.value==3.1 and c.fill.fgColor.rgb=='FFFFC9CE' for c in cells)
        assert not any(isinstance(c.value,str) and '3.1 NOK' in c.value for c in cells)

def test_concurrent_stale_plan_does_not_consume_cycle(client,spec):
    a,o,p=setup_order(client,spec,required_sessions=2)
    assert save(client,o,p,['3.5']*3).status_code==200
    assert save(client,o,p,['3.5']*3).status_code==409
    with Session() as db:assert db.get(Article,a['id']).cycle==1

def test_configuration_history_immutable(client,spec):
    a,o,p=setup_order(client,spec);save(client,o,p,['3.5']*3)
    data={'code':'TEST','name':'Artykuł testowy','specs':[{**spec,'lsl':'4','usl':'5'}]}
    assert client.post(f"/api/articles/{a['id']}/config",json=data).status_code==200
    authorize(client,'real');assert client.get('/api/results/real').json()[0]['results'][0]['spec']['lsl']=='3.2'

def test_qualitative_has_no_mean(client,spec):
    s={**spec,'kind':'qualitative','allowed':['OK','NOK'],'passing':['OK']}
    a,o,p=setup_order(client,s);assert save(client,o,p,['OK','NOK','OK']).json()['ok'] is False
    with Session() as db:assert db.scalar(select(Result)).average is None

def test_boundaries_and_precision(spec):
    assert ocen_charakterystyke(['3.2']*3,spec)['ok']
    assert not ocen_charakterystyke(['3.2']*3,{**spec,'lower_inclusive':False})['ok']
    assert not ocen_charakterystyke(['3.8001']*3,spec)['ok']
    for x in ('NaN','Infinity','',None):
        with pytest.raises(ValueError):ocen_charakterystyke([x]*3,spec)

def test_one_sided_without_rule_retains_source(spec):
    s={**spec,'lsl':None,'usl':'3.8'}
    assert generuj_symulacje('4',s)==('4',False,'NO_RULE')
    assert generuj_symulacje('4',{**s,'simulation_offset':'0.1'})[0]=='3.7'

def test_spc_coefficients_and_imr():
    r=oblicz_granice_kontrolne([[1,2,3],[2,3,4]])
    assert r['cl']==2.5 and r['ucl']==pytest.approx(4.546) and r['rucl']==pytest.approx(5.15)
    assert oblicz_granice_kontrolne([[1],[2],[3]])['kind']=='I-MR'
    with pytest.raises(ValueError):oblicz_granice_kontrolne([[1],[2,3]])

def test_csrf_and_origin(client):
    assert client.post('/api/logout',headers={'x-csrf-token':''}).status_code==403
    assert client.post('/api/logout',headers={'origin':'https://attacker.invalid'}).status_code==403

def test_history_import_idempotent_and_no_approval(client):
    w=openpyxl.Workbook();s=w.active;s.title='statistic';s['A4']='HIST';s['E4']='NR';out=io.BytesIO();w.save(out)
    for expected in (1,0):
        r=client.post('/api/import/history',files={'file':('test.xlsx',out.getvalue(),'application/octet-stream')});assert r.status_code==200,r.text;assert r.json()['inserted']==expected
    with Session() as db:assert db.scalar(select(func.count()).select_from(LabSession))==0

def test_correction_preserves_original_and_cycle(client,spec):
    a,o,p=setup_order(client,spec);sid=save(client,o,p,['3.5']*3).json()['id']
    r=save(client,o,p,['3.6']*3,correction_of=sid,reason='Korekta błędu odczytu');assert r.status_code==200,r.text
    with Session() as db:
        assert db.get(Article,a['id']).cycle==1
        assert db.get(LabSession,sid).revision==0
        assert db.get(LabSession,r.json()['id']).revision==1
        assert db.scalar(select(func.count()).select_from(Measurement))==6
    assert save(client,o,p,['3.7']*3,correction_of=sid,reason='Ponowna korekta').status_code==409

def test_scope_independence_and_expiry(client,spec):
    a,o,p=setup_order(client,spec);save(client,o,p,['3.5']*3);authorize(client,'real')
    assert client.get('/api/results/real').status_code==200
    assert client.get('/api/results/simulated').status_code==428
    with Session() as db:
        s=db.scalar(select(LoginSession));s.scopes={'real':0};db.commit()
    assert client.get('/api/export/real').status_code==428

def test_admin_updates_account_without_exposing_password(client):
    r=client.post('/api/users',json={'login':'reader','password':'Test_password_123','role':'reader'});assert r.status_code==200
    uid=r.json()['id'];r=client.patch(f'/api/users/{uid}',json={'role':'technician','active':False,'password':'Another_test_password'});assert r.status_code==200
    with Session() as db:assert db.get(User,uid).active is False;assert db.get(User,uid).password!='Another_test_password'
    assert client.patch('/api/users/1',json={'role':'reader','active':False}).status_code==422

def test_dates_and_device_saved(client,spec):
    a,o,p=setup_order(client,spec)
    assert save(client,o,p,['3.5']*3,started_on='2026-10-22',ended_on='2026-10-21').status_code==422
    r=save(client,o,p,['3.5']*3,started_on='2026-10-21',ended_on='2026-10-22',device='QA device');assert r.status_code==200,r.text
    with Session() as db:assert db.scalar(select(LabSession)).metadata_['device']=='QA device'

def test_postgres_parallel_sessions(client,spec):
    """Dwie transakcje konkurują o ten sam numer artykułu na PostgreSQL."""
    import os,threading
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException
    from app.schemas import SaveInput
    from app.services import zapisz_wyniki
    if not os.getenv('TEST_DATABASE_URL','').startswith('postgresql'):pytest.skip('Wymaga PostgreSQL; wykonywany w CI')
    a,o,p=setup_order(client,spec)
    o2=client.post('/api/orders',json={'article_id':a['id'],'lot':'PARALLEL'}).json()
    barrier=threading.Barrier(2)
    def transaction(order_id):
        """Rozpoczyna niezależną transakcję z identycznym starym planem."""
        with Session() as db:
            u=db.scalar(select(User).where(User.login=='admin'));barrier.wait(timeout=10)
            try:
                zapisz_wyniki(db,u,SaveInput(order_id=order_id,config_id=p['config_id'],cycle=1,test_date='2026-10-22',values={'thickness':['3.5']*3}));return 200
            except HTTPException as exc:db.rollback();return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:statuses=sorted(executor.map(transaction,[o['id'],o2['id']]))
    assert statuses==[200,409]
    with Session() as db:assert db.get(Article,a['id']).cycle==1;assert db.scalar(select(func.count()).select_from(LabSession))==1
