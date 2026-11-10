"""Typed local workflow graph and dependency-free CSV → XLSX acceptance pipeline."""
import csv
import io
import json
import math
from pathlib import Path
import re
import uuid
import zipfile
from xml.sax.saxutils import escape
from toolforge_pilot.core import contained,safe_relative,SKIP_DIRS,atomic_json,run_process

KINDS={'csv','validate','deduplicate','excel','python'}

def example():
    return {'version':1,'nodes':[
      {'id':'read','kind':'csv','input':None,'config':{'path':'data/input.csv','delimiter':','}},
      {'id':'validate','kind':'validate','input':'read','config':{'required':['name','email'],'numeric':[]}},
      {'id':'unique','kind':'deduplicate','input':'validate','config':{'keys':['email']}},
      {'id':'export','kind':'excel','input':'unique','config':{'path':'output/clean.xlsx','overwrite':False}}]}

def local(root,name):
    path=safe_relative(name)
    if any(p in SKIP_DIRS or p.startswith('.env') for p in path.parts):raise ValueError('Interner Pfad ist im Workflow gesperrt.')
    return contained(root,name)

def validate_workflow(value):
    if not isinstance(value,dict) or value.get('version')!=1:raise ValueError('Workflow-Version muss 1 sein.')
    nodes=value.get('nodes')
    if not isinstance(nodes,list) or not 1<=len(nodes)<=30:raise ValueError('Workflow benötigt 1 bis 30 Knoten.')
    ids=set()
    for node in nodes:
        if not isinstance(node,dict) or not re.fullmatch(r'[A-Za-z][\w-]{0,39}',str(node.get('id',''))):raise ValueError('Ungültige Knoten-ID.')
        if node['id'] in ids:raise ValueError('Doppelte Knoten-ID.')
        ids.add(node['id'])
        if node.get('kind') not in KINDS or not isinstance(node.get('config'),dict):raise ValueError('Unbekannter Knotentyp oder Konfiguration.')
    for node in nodes:
        source=node.get('input')
        if node['kind']=='csv' and source is not None:raise ValueError('CSV-Quelle darf keinen Eingang besitzen.')
        if node['kind'] not in ('csv','python') and not source:raise ValueError('Knoten benötigt einen Eingang.')
        if source is not None and source not in ids:raise ValueError('Eingang verweist auf unbekannten Knoten.')
        cfg=node['config']
        for field in ('required','numeric','keys'):
            if field in cfg and (not isinstance(cfg[field],list) or not all(isinstance(x,str) and x for x in cfg[field])):raise ValueError(field+' muss eine Liste von Spaltennamen sein.')
        if node['kind'] in ('csv','excel','python'):
            safe_relative(cfg.get('path',''))
        if node['kind']=='excel' and type(cfg.get('overwrite',False))!=bool:raise ValueError('overwrite muss boolesch sein.')
    pending=list(nodes);ordered=[];done=set()
    while pending:
        ready=[n for n in pending if n.get('input') is None or n['input'] in done]
        if not ready:raise ValueError('Workflow enthält einen Zyklus.')
        for node in ready:ordered.append(node);done.add(node['id']);pending.remove(node)
    return {'version':1,'nodes':ordered}

def table(data):
    if not isinstance(data,dict) or not isinstance(data.get('columns'),list) or not isinstance(data.get('rows'),list):raise ValueError('Knoten benötigt eine Tabelle mit columns und rows.')
    cols=data['columns'];rows=data['rows']
    if not cols or len(cols)>256 or not all(isinstance(c,str) and c.strip() for c in cols) or len(set(cols))!=len(cols):raise ValueError('Spalten müssen eindeutig und nicht leer sein (maximal 256).')
    if len(rows)>50000 or any(not isinstance(row,list) or len(row)!=len(cols) for row in rows):raise ValueError('Ungültige Zeilenbreite oder mehr als 50.000 Zeilen.')
    for row in rows:
        if any(not isinstance(x,(str,int,float,bool,type(None))) or isinstance(x,float) and not math.isfinite(x) for x in row):raise ValueError('Ungültiger Zellwert.')
    return data

def xlsx_bytes(data):
    table(data)
    def column(i):
        out=''
        while i:i,r=divmod(i-1,26);out=chr(65+r)+out
        return out
    xml=[]
    for ri,row in enumerate([data['columns'],*data['rows']],1):
        cells=[]
        for ci,value in enumerate(row,1):
            ref=column(ci)+str(ri)
            if type(value) in (int,float):cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text='' if value is None else str(value)
                if len(text)>32767 or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',text):raise ValueError('Zellinhalt ist nicht Excel-/XML-kompatibel.')
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>')
        xml.append(f'<row r="{ri}">'+''.join(cells)+'</row>')
    files={
     '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
     '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
     'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Daten" sheetId="1" r:id="rId1"/></sheets></workbook>',
     'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
     'xl/worksheets/sheet1.xml':'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(xml)+'</sheetData></worksheet>'}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,text in files.items():z.writestr(name,'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+text)
    return buf.getvalue()

def execute(root,workflow,python,stop,log,settings=None):
    workflow=validate_workflow(workflow);values={};report=[]
    run=Path(root)/'.toolforge/workflow-runs'/uuid.uuid4().hex;run.mkdir(parents=True)
    try:
        for node in workflow['nodes']:
            if stop.is_set():return {'code':1,'reason':'STOP','nodes':report}
            kind=node['kind'];cfg=node['config'];data=values.get(node.get('input'));log(node['id']+' · '+kind+'\n')
            if kind=='csv':
                path=local(root,cfg['path'])
                if path.stat().st_size>10000000:raise ValueError('CSV-Limit: 10 MB.')
                delimiter=cfg.get('delimiter',',')
                if not isinstance(delimiter,str) or len(delimiter)!=1:raise ValueError('Trennzeichen muss genau ein Zeichen sein.')
                with path.open(encoding='utf-8-sig',newline='') as f:
                    from itertools import islice
                    rows=list(islice(csv.reader(f,delimiter=delimiter,strict=True),50002))
                    if len(rows)>50001:raise ValueError('CSV-Limit: 50.000 Datenzeilen.')
                data=table({'columns':rows[0] if rows else [],'rows':rows[1:]})
            elif kind=='validate':
                data=table(json.loads(json.dumps(data)))
                for column in cfg.get('required',[]):
                    if column not in data['columns']:raise ValueError('Pflichtspalte fehlt: '+column)
                    idx=data['columns'].index(column)
                    for number,row in enumerate(data['rows'],2):
                        if row[idx] is None or not str(row[idx]).strip():raise ValueError(f'Leerer Pflichtwert: {column}, Zeile {number}.')
                for column in cfg.get('numeric',[]):
                    if column not in data['columns']:raise ValueError('Zahlenspalte fehlt: '+column)
                    idx=data['columns'].index(column)
                    for row in data['rows']:row[idx]=float(row[idx])
                table(data)
            elif kind=='deduplicate':
                data=table(data);keys=cfg.get('keys') or data['columns']
                if any(k not in data['columns'] for k in keys):raise ValueError('Unbekannte Duplikat-Schlüsselspalte.')
                indexes=[data['columns'].index(k) for k in keys];seen=set();rows=[]
                for row in data['rows']:
                    key=tuple(row[i] for i in indexes)
                    if key not in seen:seen.add(key);rows.append(row)
                data={'columns':data['columns'],'rows':rows}
            elif kind=='excel':
                path=local(root,cfg['path'])
                if path.suffix.lower()!='.xlsx':raise ValueError('Excel-Ziel benötigt .xlsx.')
                content=xlsx_bytes(table(data));path.parent.mkdir(parents=True,exist_ok=True)
                if cfg.get('overwrite',False):
                    if path.exists():shutil_copy(path,run/(node['id']+'-before.xlsx'))
                    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_bytes(content);tmp.replace(path)
                else:
                    with path.open('xb') as f:f.write(content)
                data={**data,'artifact':path.relative_to(root).as_posix()}
            elif kind=='python':
                script=local(root,cfg['path'])
                if script.suffix!='.py' or not script.is_file():raise ValueError('Python-Knoten benötigt eine vorhandene .py-Datei.')
                source=run/(node['id']+'-input.json');target=run/(node['id']+'-output.json');atomic_json(source,data)
                from backend.sandbox import run as sandbox_run
                result=sandbox_run(root,[python,'-u',str(script),'--input',str(source),'--output',str(target)],root,min(600,max(5,int(cfg.get('timeout',120)))),stop,log,settings or {})
                if result['code'] or result['reason']:raise ValueError('Python-Knoten fehlgeschlagen: '+result['reason'])
                if target.stat().st_size>10000000:raise ValueError('Python-Ausgabe zu groß.')
                data=json.loads(target.read_text(encoding='utf-8'))
            values[node['id']]=data
            report.append({'id':node['id'],'kind':kind,'rows':len(data.get('rows',[])) if isinstance(data,dict) else None,'artifact':data.get('artifact') if isinstance(data,dict) else None})
            atomic_json(run/'report.json',report)
        return {'code':0,'reason':'','nodes':report,'report':str(run/'report.json')}
    except Exception as exc:
        log('FEHLER: '+str(exc)+'\n');atomic_json(run/'error.json',{'error':str(exc),'nodes':report})
        return {'code':1,'reason':'STOP' if stop.is_set() else str(exc),'nodes':report}

def shutil_copy(source,target):
    import shutil
    shutil.copy2(source,target)


def acceptance(root,python,stop,log):
    """Runs an actual isolated example in the selected project; verifies exported XML."""
    import xml.etree.ElementTree as ET
    folder='acceptance-demo/'+uuid.uuid4().hex
    source=local(root,folder+'/input.csv');source.parent.mkdir(parents=True)
    source.write_text('name,email\nAda,ada@example.test\nAda,ada@example.test\nLinus,linus@example.test\n',encoding='utf-8')
    flow=example();flow['nodes'][0]['config']['path']=folder+'/input.csv';flow['nodes'][-1]['config']['path']=folder+'/clean.xlsx'
    result=execute(root,flow,python,stop,log)
    if result['code']:return result
    try:
        assert [n['rows'] for n in result['nodes']]==[3,3,2,2],'Zeilenzahlen stimmen nicht.'
        with zipfile.ZipFile(local(root,folder+'/clean.xlsx')) as z:
            sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            assert len(sheet.findall('s:sheetData/s:row',ns))==3,'Excel enthält nicht zwei Datenzeilen.'
            assert sheet.find('.//s:f',ns) is None,'Unerwartete Excel-Formel.'
        result['acceptance']='PASS: CSV gelesen und validiert, 1 Duplikat entfernt, 2 Datenzeilen in gültigem XLSX exportiert.'
        log(result['acceptance']+'\n');return result
    except Exception as exc:return {'code':1,'reason':'Abnahme fehlgeschlagen: '+str(exc),'nodes':result['nodes']}
