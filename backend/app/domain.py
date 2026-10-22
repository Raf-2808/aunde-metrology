"""Reguły oceny laboratoryjnej, symulacji i kart kontrolnych."""
from decimal import Decimal, InvalidOperation, localcontext
from statistics import mean

# Źródło tabeli: NIST/SEMATECH e-Handbook, rozdział 6.3.2.1.
WSPOLCZYNNIKI = {2:(1.880,0,3.267),3:(1.023,0,2.575),4:(.729,0,2.282),5:(.577,0,2.115),6:(.483,0,2.004),7:(.419,.076,1.924),8:(.373,.136,1.864),9:(.337,.184,1.816),10:(.308,.223,1.777)}

def liczba(value):
    """Odrzuca puste, nieskończone i nienumeryczne pomiary."""
    try:
        x=Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise ValueError('Wymagana skończona liczba')
    if not x.is_finite() or len(x.as_tuple().digits)>28 or abs(x)>Decimal('1e15') or x.as_tuple().exponent < -12:
        raise ValueError('Liczba poza zakresem: do 28 cyfr, 12 miejsc po przecinku')
    return x

def sprawdz_tolerancje(x, spec):
    """Stosuje osobne operatory granic, bez zaokrąglania do prezentacji."""
    x=liczba(x)
    lo,hi=spec.get('lsl'),spec.get('usl')
    return (lo is None or (x>=liczba(lo) if spec.get('lower_inclusive',True) else x>liczba(lo))) and (hi is None or (x<=liczba(hi) if spec.get('upper_inclusive',True) else x<liczba(hi)))

def ocen_charakterystyke(values,spec):
    """Weryfikuje kompletność i ocenia średnią lub zatwierdzoną regułę jakościową."""
    if len(values)!=spec['count'] or any(v is None or str(v).strip()=='' for v in values):
        raise ValueError(f"Wymagane {spec['count']} kompletne pomiary: {spec['name']}")
    if spec['kind']=='numeric':
        nums=[liczba(x) for x in values]
        # Kontekst o dużej precyzji chroni ocenę przed zaokrągleniem prezentacyjnym.
        with localcontext() as ctx:
            ctx.prec=80
            total=sum(nums); avg=total/len(nums)
            # Granice porównujemy z sumą, aby uniknąć błędu rozwinięcia okresowego.
            scaled={**spec,'lsl': None if spec.get('lsl') is None else str(liczba(spec['lsl'])*len(nums)), 'usl':None if spec.get('usl') is None else str(liczba(spec['usl'])*len(nums))}
            ok=(scaled['lsl'] is None or (total>=Decimal(scaled['lsl']) if spec.get('lower_inclusive',True) else total>Decimal(scaled['lsl']))) and (scaled['usl'] is None or (total<=Decimal(scaled['usl']) if spec.get('upper_inclusive',True) else total<Decimal(scaled['usl'])))
        flags=[sprawdz_tolerancje(x,spec) for x in nums]
        return {'values':[str(x) for x in nums],'average':str(avg),'ok':ok,'individual_ok':flags,'warning':not all(flags) or not ok}
    allowed=spec.get('allowed',[])
    if not allowed or any(str(x) not in allowed for x in values):
        raise ValueError('Wynik spoza katalogu metody')
    passing=spec.get('passing',[])
    flags=[str(x) in passing for x in values]
    return {'values':[str(x) for x in values],'average':None,'ok':all(flags),'individual_ok':flags,'warning':not all(flags)}

def generuj_symulacje(value,spec):
    """Przekształca pojedynczy pomiar; brak reguły pozostawia oryginał."""
    if spec['kind']!='numeric': return str(value),False,'NOT_NUMERIC'
    x=liczba(value)
    if sprawdz_tolerancje(x,spec): return str(x),False,'UNCHANGED'
    lo,hi=spec.get('lsl'),spec.get('usl')
    if lo is not None and hi is not None:
        lo,hi=liczba(lo),liczba(hi)
        y=lo+Decimal('.05')*(hi-lo) if x<=lo else hi-Decimal('.05')*(hi-lo)
    elif spec.get('simulation_offset'):
        offset=liczba(spec['simulation_offset'])
        y=liczba(lo)+offset if lo is not None else liczba(hi)-offset
    else: return str(x),False,'NO_RULE'
    return str(y),True,'CORRECTED'

def wyznacz_badania_cykliczne(specs,cycle,extra=()):
    """Włącza pełny obowiązkowy zakres oraz jawnie zlecone badania dodatkowe."""
    return [s for s in specs if s['frequency']=='every' or (s['frequency']=='nth' and cycle%s['every_n']==0) or s['key'] in extra]

def oblicz_granice_kontrolne(groups):
    """Wyznacza propozycję granic do późniejszego zatwierdzenia planu SPC."""
    if len(groups)<2: raise ValueError('Co najmniej dwie podgrupy')
    n=len(groups[0])
    if any(len(g)!=n for g in groups) or not 1<=n<=10: raise ValueError('Niejednorodna liczność podgrup')
    means=[mean(g) for g in groups]; cl=mean(means)
    if n==1:
        ranges=[abs(means[i]-means[i-1]) for i in range(1,len(means))]
        r=mean(ranges)
        return dict(kind='I-MR',cl=cl,lcl=cl-2.66*r,ucl=cl+2.66*r,rcl=r,rlcl=0,rucl=3.267*r,n=n)
    ranges=[max(g)-min(g) for g in groups]; r=mean(ranges); a,d3,d4=WSPOLCZYNNIKI[n]
    return dict(kind='Xbar-R',cl=cl,lcl=cl-a*r,ucl=cl+a*r,rcl=r,rlcl=d3*r,rucl=d4*r,n=n)

def wykryj_przekroczenia_spc(groups,config,spec):
    """Oddziela alarm średniej, rozstępu, specyfikacji i serii po stronie CL."""
    if not groups: return []
    if any(len(g)!=config['n'] for g in groups): raise ValueError('Niezgodny plan próbkowania')
    means=[mean(g) for g in groups]; m=means[-1]; alarms=[]
    for name,test in [('UCL',m>config['ucl']),('LCL',m<config['lcl']),('SPECIFICATION',not sprawdz_tolerancje(m,spec))]:
        if test: alarms.append({'type':name,'value':m,'limit':config.get(name.lower(),{'lsl':spec.get('lsl'),'usl':spec.get('usl')})})
    r=(max(groups[-1])-min(groups[-1])) if config['n']>1 else (abs(means[-1]-means[-2]) if len(means)>1 else None)
    if r is not None:
        for typ,limit,hit in [('R_UCL',config['rucl'],r>config['rucl']),('R_LCL',config['rlcl'],r<config['rlcl'])]:
            if hit: alarms.append({'type':typ,'value':r,'limit':limit})
    run=config.get('run_length',8)
    if run and len(means)>=run and (all(x>config['cl'] for x in means[-run:]) or all(x<config['cl'] for x in means[-run:])):
        alarms.append({'type':'RUN','value':m,'limit':config['cl']})
    return alarms
