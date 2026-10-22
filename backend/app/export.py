"""Eksport XLSX bez makr i wykonywalnych formuł pochodzących z danych."""
import io
import xlsxwriter

def eksportuj_raport_excel(rows,source,form=False):
    """Zachowuje każdy pomiar, średnią i tolerancję wersji historycznej."""
    stream=io.BytesIO();w=xlsxwriter.Workbook(stream,{'in_memory':True,'strings_to_formulas':False,'strings_to_urls':False})
    title=w.add_format({'bold':True,'font_size':18,'font_color':'#12364a'})
    header=w.add_format({'bold':True,'bg_color':'#e8eef2','text_wrap':True,'border':1})
    normal=w.add_format({'border':1});blue=w.add_format({'bg_color':'#eaf5ff','border':1})
    red=w.add_format({'bg_color':'#ffc9ce','border':1})
    formats={}
    def numeric_style(sp,ok,measurement=False):
        """Współdzieli formaty liczbowe i nie zmienia wartości dla celów prezentacji."""
        key=(sp['decimals'],ok,measurement)
        if key not in formats:formats[key]=w.add_format({'num_format':'0'+('.'+'0'*sp['decimals'] if sp['decimals'] else ''),'border':1,'bg_color':'#ffc9ce' if not ok else '#eaf5ff' if measurement else '#ffffff'})
        return formats[key]
    label='SIMULATED DATA' if source=='simulated' else 'WYNIKI RZECZYWISTE'
    if form and rows:
        d=rows[0];s=w.add_worksheet('test');s.hide_gridlines(2);s.set_landscape();s.fit_to_pages(1,0);s.set_paper(9)
        s.merge_range('A1:N2','AUNDE | Laboratory Performance Test Results',title)
        s.merge_range('A3:N3',label,header)
        for i,(key,value) in enumerate([('Artykuł',d['code']+' '+d['article']),('Lotto',d['lot']),('Bela',d['roll']),('Data badania',d['test_date']),('Operator',d['operator']),('Cykl',d['cycle']),('WZ',d['metadata']['delivery_note']),('Poziom produkcji',d['metadata']['production_level']),('Urządzenie',d['metadata'].get('device','')),('Data rozpoczęcia',d['metadata'].get('started_on','')),('Data zakończenia',d['metadata'].get('ended_on',''))]):
            s.write(4+i,0,key,header);s.merge_range(4+i,1,4+i,13,value,normal)
        s.set_column(0,0,34);s.set_column(1,3,16);s.set_column(4,13,10)
        start=17
        for col,x in enumerate(['Charakterystyka','Norma','Tolerancja / ocena','Jednostka']+[f'Pomiar {i+1}' for i in range(10)]):s.write(start,col,x,header)
        for i,r in enumerate(d['results']):
            spec=r['spec'];row=start+1+i*3
            for col,v in enumerate([spec['name'],spec['method'],f"{spec.get('lsl')} .. {spec.get('usl')}" if spec['kind']=='numeric' else ', '.join(spec['passing']),spec['unit']]):s.write(row,col,v,normal)
            for j,v in enumerate(r['values']):
                s.write(row,4+j,float(v) if spec['kind']=='numeric' else v,numeric_style(spec,r['individual_ok'][j],True) if spec['kind']=='numeric' else red if not r['individual_ok'][j] else blue)
                s.write(row+1,4+j,spec['labels'][j],normal)
            s.write(row+2,0,'Średnia',header)
            if r['average'] is not None: s.write(row+2,1,float(r['average']),numeric_style(spec,r['ok']))
            s.write(row+2,2,'OK' if r['ok'] else 'NOK',normal)
        s.repeat_rows(start,start)
    else:
        s=w.add_worksheet('statistic');s.freeze_panes(4,4);s.set_column(0,3,20)
        s.merge_range('A1:D1',label,title)
        keys=[];specs={}
        for d in rows:
            for r in d['results']:
                key=(d['config_id'],r['spec']['key'])
                if key not in specs: keys.append(key);specs[key]=r['spec']
        headers=['Artykuł','Lotto','Data','Cykl'];columns=[]
        for key in keys:
            sp=specs[key]
            for j in range(sp['count']): columns.append((key,j));headers.append(sp['name']+' / '+sp['labels'][j])
            columns.append((key,'average'));headers.append(sp['name']+' / Średnia')
        for j,h in enumerate(headers):s.write(1,j,h,header)
        for j,(key,_) in enumerate(columns,4):
            sp=specs[key];s.write(2,j,f"{sp['method']} | {sp['unit']} | {sp.get('lsl')} .. {sp.get('usl')} | cfg {key[0]}",header);s.set_column(j,j,20)
        for i,d in enumerate(rows,4):
            for j,v in enumerate([d['code'],d['lot'],d['test_date'],d['cycle']]):s.write(i,j,v,normal)
            rr={(d['config_id'],r['spec']['key']):r for r in d['results']}
            for j,(key,pos) in enumerate(columns,4):
                if key not in rr:continue
                r=rr[key];sp=r['spec'];v=r['average'] if pos=='average' else r['values'][pos]
                ok=r['ok'] if pos=='average' else r['individual_ok'][pos]
                if v is not None:s.write(i,j,float(v) if sp['kind']=='numeric' else v,numeric_style(sp,ok) if sp['kind']=='numeric' else normal if ok else red)
        if rows:s.autofilter(1,0,len(rows)+3,len(headers)-1)
        s.set_row(1,60);s.set_row(2,54)
    w.close();return stream.getvalue()

def eksportuj_spc(data):
    """Eksportuje średnie, rozstępy, specyfikacje i zatwierdzone granice SPC."""
    out=io.BytesIO();w=xlsxwriter.Workbook(out,{'in_memory':True,'strings_to_formulas':False});s=w.add_worksheet('SPC')
    columns=['Lotto','Data','Cykl','Średnia','Rozstęp','CL','LCL','UCL','R CL','R LCL','R UCL','LSL','USL']
    s.write_row(0,0,columns);s.freeze_panes(1,3);s.set_column(0,12,18)
    l=data['limits']
    for i,label in enumerate(data['labels'],1): s.write_row(i,0,[label['lot'],label['date'],label['cycle'],data['means'][i-1],data['ranges'][i-1],l['cl'],l['lcl'],l['ucl'],l['rcl'],l['rlcl'],l['rucl'],data['spec'].get('lsl'),data['spec'].get('usl')])
    w.close();return out.getvalue()
