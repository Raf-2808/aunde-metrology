"""Proces wysyłki outbox. Nie wysyła ponownie zdarzeń o niepewnym wyniku SMTP."""
import os,time,smtplib,ssl,json
from email.message import EmailMessage
from sqlalchemy import select,text
from .models import Session,Outbox,Alert,teraz

def wykres_svg(alert):
    """Tworzy opcjonalny załącznik graficzny z kartami średniej i rozstępu."""
    import html
    from .models import SpcConfig
    from .services import groups_for
    with Session() as db:
        config=db.get(SpcConfig,alert.spc_config_id)
        groups,labels=groups_for(db,config.characteristic_id,end_session=alert.session_id)
    means=[sum(g)/len(g) for g in groups]
    ranges=[max(g)-min(g) for g in groups] if config.limits['n']>1 else [abs(means[i]-means[i-1]) for i in range(1,len(means))]
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650" viewBox="0 0 1000 650"><rect width="1000" height="650" fill="white"/>',f'<text x="40" y="30" font-size="18">AUNDE SPC: {html.escape(alert.payload["code"])} / {html.escape(alert.payload["lot"])}</text>']
    for offset,series,keys,title in [(60,means,['cl','lcl','ucl'],'Mean'),(360,ranges,['rcl','rlcl','rucl'],'Range / MR')]:
        limits=[float(config.limits[k]) for k in keys];low=min(series+limits);high=max(series+limits);span=high-low or 1
        y=lambda v:offset+220-200*(v-low)/span
        parts.append(f'<text x="40" y="{offset+5}" font-size="14">{title}</text>')
        for k,v in zip(keys,limits):parts.append(f'<line x1="80" x2="950" y1="{y(v)}" y2="{y(v)}" stroke="#b6515e" stroke-dasharray="5 4"/><text x="5" y="{y(v)}" font-size="10">{k.upper()} {v:.3f}</text>')
        points=' '.join(f'{80+870*i/max(1,len(series)-1):.2f},{y(v):.2f}' for i,v in enumerate(series))
        parts.append(f'<polyline fill="none" stroke="#147b84" stroke-width="2" points="{points}"/>')
    parts.append('</svg>');return ''.join(parts).encode()

def wyslij_powiadomienie_email(item,alert):
    """Wysyła rzeczywisty alarm przez SMTP z TLS i stabilnym Message-ID."""
    p=alert.payload;msg=EmailMessage();msg['From']=os.environ['SMTP_FROM'];msg['To']=item.recipient
    msg['Subject']=f"AUNDE SPC {alert.event}: {p['code']} / {p['lot']}"
    msg['Message-ID']=f"<lims-alert-{alert.id}-{item.id}@{os.getenv('MAIL_ID_DOMAIN','lims.internal')}>"
    msg.set_content('\n'.join(f'{k}: {v}' for k,v in p.items() if k!='link')+'\n'+os.environ['PUBLIC_URL'].rstrip('/')+p['link'])
    # Raport tekstowy można zachować jako załącznik bez zależności od renderera.
    msg.add_attachment(json.dumps(p,ensure_ascii=False,indent=2).encode(),maintype='application',subtype='json',filename='alarm.json')
    if os.getenv('SMTP_ATTACH_CHART','false').lower()=='true':
        msg.add_attachment(wykres_svg(alert),maintype='image',subtype='svg+xml',filename='spc.svg')
    with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=30) as server:
        server.ehlo();server.starttls(context=ssl.create_default_context());server.ehlo()
        if os.getenv('SMTP_USER'):server.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
        refused=server.send_message(msg)
        if refused:raise RuntimeError('Serwer odrzucił odbiorcę')

def process_once():
    """Przejmuje rekord przez SKIP LOCKED i trwale rejestruje zamiar wysłania."""
    if os.getenv('SMTP_ENABLED','false').lower()!='true':return False
    with Session() as db:
        item=db.scalar(select(Outbox).where(Outbox.status=='PENDING').order_by(Outbox.id).with_for_update(skip_locked=True).limit(1))
        if not item:return False
        item.status='SENDING';item.attempts+=1;db.commit()
        try:
            wyslij_powiadomienie_email(item,db.get(Alert,item.alert_id));item.status='ACCEPTED_BY_SMTP';item.sent_at=teraz();item.error=''
        except Exception as exc:
            # Po zerwaniu połączenia SMTP nie da się potwierdzić doręczenia.
            # Nie ponawiamy automatycznie, aby nie dublować powiadomień.
            item.status='UNCERTAIN';item.error=type(exc).__name__+': '+str(exc)[:500]
        db.commit();return True

if __name__=='__main__':
    while True:
        try:process_once()
        except Exception as exc:print(type(exc).__name__,flush=True)
        time.sleep(5)
