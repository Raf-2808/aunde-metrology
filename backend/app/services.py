"""Zapis transakcyjny, odtwarzanie wyników i kolejka zdarzeń SPC."""
from sqlalchemy import select,func
from fastapi import HTTPException
from .models import *
from .domain import *

def audit(db,user,action,entity,payload):
    """Zapisuje autora i stan zdarzenia w tej samej transakcji biznesowej."""
    db.add(Audit(author=user.id,action=action,entity=str(entity),payload=payload))

def current_config(db,article_id):
    """Wybiera ostatnią niezmienną wersję konfiguracji artykułu."""
    c=db.scalar(select(Config).where(Config.article_id==article_id).order_by(Config.version.desc()))
    if not c: raise HTTPException(409,'Artykuł nie ma konfiguracji')
    return c

def specs_for(db,config_id):
    """Odtwarza uporządkowane charakterystyki z odniesieniem do katalogu norm."""
    out=[]
    for c in db.scalars(select(Characteristic).where(Characteristic.config_id==config_id).order_by(Characteristic.position)):
        m=db.get(Method,c.method_id)
        out.append({**c.spec,'id':c.id,'method_id':c.method_id,'method':m.code,'key':c.key})
    return out

def save_config(db,user,article,data):
    """Dodaje wersję konfiguracji bez modyfikowania istniejących tolerancji."""
    previous=db.scalar(select(func.max(Config.version)).where(Config.article_id==article.id)) or 0
    config=Config(article_id=article.id,version=previous+1,author=user.id);db.add(config);db.flush()
    for i,spec in enumerate(data.specs):
        if not db.get(Method,spec.method_id): raise HTTPException(422,'Nieznana norma')
        db.add(Characteristic(config_id=config.id,key=spec.key,position=i,method_id=spec.method_id,spec=spec.model_dump()))
    audit(db,user,'CONFIG_VERSION',article.id,{'version':config.version,'specs':[s.model_dump() for s in data.specs]})
    db.flush();return config

def plan(db,order):
    """Wyświetla przyszły cykl bez jego rezerwowania i zużywania."""
    a=db.get(Article,order.article_id);c=current_config(db,a.id)
    return {'article_id':a.id,'article':a.name,'code':a.code,'cycle':a.cycle+1,'config_id':c.id,'version':c.version,'specs':wyznacz_badania_cykliczne(specs_for(db,c.id),a.cycle+1,order.extra)}

def serialize_session(db,s,source):
    """Odtwarza pełny formularz z historyczną wersją konfiguracji."""
    a=db.get(Article,s.article_id);o=db.get(Order,s.order_id)
    data={'id':s.id,'order_id':o.id,'revision':s.revision,'article':a.name,'article_id':a.id,'code':a.code,'lot':o.lot,'roll':o.roll,'cycle':s.cycle,'test_date':s.test_date,'operator':db.get(User,s.operator).login,'source':source,'label':'SIMULATED DATA' if source=='simulated' else 'WYNIKI RZECZYWISTE','config_id':s.config_id,'metadata':s.metadata_,'correction_of':s.correction_of,'reason':s.reason,'results':[]}
    for r in db.scalars(select(Result).where(Result.session_id==s.id).order_by(Result.id)):
        c=db.get(Characteristic,r.characteristic_id);spec={**c.spec,'method':db.get(Method,c.method_id).code,'id':c.id}
        values=[];flags=[];transforms=[]
        for m in db.scalars(select(Measurement).where(Measurement.result_id==r.id).order_by(Measurement.position)):
            sim=db.get(Simulation,m.id)
            values.append(sim.value if source=='simulated' else m.value);flags.append(sim.ok if source=='simulated' else m.ok)
            transforms.append({'measurement_id':m.id,'corrected':sim.corrected,'parameters':sim.parameters,'algorithm':sim.algorithm,'source_value':m.value})
        data['results'].append({'spec':spec,'values':values,'individual_ok':flags,'average':r.simulated_average if source=='simulated' else r.average,'ok':r.simulated_ok if source=='simulated' else r.ok,'transforms':transforms if source=='simulated' else []})
    data['ok']=all(r['ok'] for r in data['results'])
    return data

def groups_for(db,characteristic_id,end_session=None,start=None,end=None):
    """Pobiera wyłącznie rzeczywiste podgrupy tej samej wersji charakterystyki."""
    query=select(Result,LabSession).join(LabSession,Result.session_id==LabSession.id).where(Result.characteristic_id==characteristic_id).order_by(LabSession.cycle)
    if end_session is not None: query=query.where(LabSession.id<=end_session)
    if start: query=query.where(LabSession.test_date>=str(start))
    if end: query=query.where(LabSession.test_date<=str(end))
    superseded=select(LabSession.correction_of).where(LabSession.correction_of.is_not(None))
    query=query.where(LabSession.id.not_in(superseded))
    groups=[];labels=[]
    for r,s in db.execute(query):
        groups.append([float(m.value) for m in db.scalars(select(Measurement).where(Measurement.result_id==r.id).order_by(Measurement.position))]);labels.append({'session_id':s.id,'lot':db.get(Order,s.order_id).lot,'date':s.test_date,'cycle':s.cycle})
    return groups,labels

def enqueue_alerts(db,s):
    """Rejestruje unikalne alarmy i odbiorców atomowo z wynikiem rzeczywistym."""
    for r in db.scalars(select(Result).where(Result.session_id==s.id)):
        config=db.scalar(select(SpcConfig).where(SpcConfig.characteristic_id==r.characteristic_id).order_by(SpcConfig.id.desc()))
        if not config: continue
        c=db.get(Characteristic,r.characteristic_id)
        groups,labels=groups_for(db,c.id,s.id)
        if any(len(g)!=config.limits['n'] for g in groups): continue
        for hit in wykryj_przekroczenia_spc(groups,config.limits,c.spec):
            existing=db.scalar(select(Alert).where(Alert.session_id==s.id,Alert.spc_config_id==config.id,Alert.event==hit['type']))
            if existing: continue
            a=db.get(Article,s.article_id);o=db.get(Order,s.order_id)
            event=Alert(session_id=s.id,spc_config_id=config.id,event=hit['type'],payload={**hit,'article':a.name,'code':a.code,'lot':o.lot,'date':s.test_date,'characteristic':c.spec['name'],'link':f'/spc?characteristic={c.id}'})
            db.add(event);db.flush()
            recipients={rule.email for rule in db.scalars(select(NotificationRule).where(NotificationRule.characteristic_id==c.id,NotificationRule.enabled==True)) if hit['type'] in rule.events}
            for email in recipients: db.add(Outbox(alert_id=event.id,recipient=email))

def zapisz_wyniki(db,user,data):
    """Blokuje licznik artykułu, waliduje pełny zakres i zapisuje atomową sesję."""
    order=db.get(Order,data.order_id)
    if data.started_on and data.ended_on and data.started_on>data.ended_on:raise HTTPException(422,'Data zakończenia nie może poprzedzać rozpoczęcia')
    if not order: raise HTTPException(404,'Nieznane zlecenie')
    article=db.scalar(select(Article).where(Article.id==order.article_id).with_for_update())
    order=db.scalar(select(Order).where(Order.id==data.order_id).with_for_update().execution_options(populate_existing=True))
    if order.status=='HELD': raise HTTPException(409,'Partia wstrzymana')
    correction=None
    if data.correction_of:
        if user.role not in ('admin','manager') or len(data.reason.strip())<3: raise HTTPException(403,'Korekta wymaga kierownika i uzasadnienia')
        correction=db.get(LabSession,data.correction_of)
        if not correction or correction.order_id!=order.id: raise HTTPException(422,'Korygowana sesja innej partii')
        if db.scalar(select(LabSession.id).where(LabSession.correction_of==correction.id)): raise HTTPException(409,'Sesja już skorygowana')
    elif order.status=='TESTED': raise HTTPException(409,'Zlecenie zakończone')
    config=db.get(Config,correction.config_id) if correction else current_config(db,article.id)
    expected_cycle=correction.cycle if correction else article.cycle+1
    if data.cycle!=expected_cycle or data.config_id!=config.id: raise HTTPException(409,'Plan zmienił się. Odśwież formularz przed zapisem.')
    if correction:
        required_ids=set(db.scalars(select(Result.characteristic_id).where(Result.session_id==correction.id)))
        specs=[s for s in specs_for(db,config.id) if s['id'] in required_ids]
    else:
        specs=wyznacz_badania_cykliczne(specs_for(db,config.id),data.cycle,order.extra)
    if not specs or set(data.values)!=set(s['key'] for s in specs): raise HTTPException(422,'Zakres wyników różni się od obowiązkowego planu')
    try: evaluated=[(spec,ocen_charakterystyke(data.values[spec['key']],spec)) for spec in specs]
    except ValueError as e: raise HTTPException(422,str(e))
    if any(r['warning'] for _,r in evaluated) and not data.acknowledged: raise HTTPException(422,'Potwierdź ostrzeżenia o przekroczeniu tolerancji')
    s=LabSession(article_id=article.id,order_id=order.id,config_id=config.id,cycle=data.cycle,revision=correction.revision+1 if correction else 0,operator=user.id,test_date=data.test_date.isoformat(),metadata_={'delivery_note':data.delivery_note,'production_level':data.production_level,'notes':data.notes,'device':data.device,'started_on':data.started_on.isoformat() if data.started_on else '', 'ended_on':data.ended_on.isoformat() if data.ended_on else ''},ok=all(r['ok'] for _,r in evaluated),acknowledged=data.acknowledged,correction_of=data.correction_of,reason=data.reason)
    db.add(s);db.flush()
    for spec,e in evaluated:
        sims=[generuj_symulacje(v,spec) for v in e['values']];se=ocen_charakterystyke([x[0] for x in sims],spec)
        result=Result(session_id=s.id,characteristic_id=spec['id'],average=e['average'],ok=e['ok'],simulated_average=se['average'],simulated_ok=se['ok']);db.add(result);db.flush()
        for i,v in enumerate(e['values']):
            m=Measurement(result_id=result.id,position=i,value=v,ok=e['individual_ok'][i]);db.add(m);db.flush()
            db.add(Simulation(measurement_id=m.id,value=sims[i][0],ok=se['individual_ok'][i],corrected=sims[i][1],parameters={'spec':spec,'outcome':sims[i][2],'fraction':'0.05'}))
    if not correction: article.cycle=data.cycle
    count=db.scalar(select(func.count()).select_from(LabSession).where(LabSession.order_id==order.id,LabSession.correction_of.is_(None)))
    order.status='TESTED' if count>=order.required_sessions else 'IN_PROGRESS'
    if order.status=='TESTED': order.completed=teraz()
    db.flush();enqueue_alerts(db,s)
    audit(db,user,'SAVE_RESULTS',s.id,{'cycle':s.cycle,'ok':s.ok,'reason':data.reason,'correction_of':data.correction_of});db.commit()
    return {'id':s.id,'cycle':s.cycle,'ok':s.ok,'order_status':order.status}
