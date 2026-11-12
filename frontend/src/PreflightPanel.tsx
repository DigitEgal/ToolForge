import {useState} from 'react';
export type Preflight = {goal?:string;status:string; error?:string; accepted?:boolean; note:string; kind?:string; judge?:string; context_tokens?:number; candidates?:string[]; recommendation?:{model:string; temperature:number; context_tokens:number; reason:string}|null; verdict?:{scores:Record<string,number>}; samples:{id:string;model:string;temperature:number;valid:boolean;seconds?:number;response?:string;error?:string}[]};
type Options = {models:{key:string;max_context_length?:number;selected_variant?:string}[];candidates:string[];judge:string};
type SnapshotLite = {busy:boolean;phase:string;error?:string;preflight?:Preflight|null;state?:{status?:string;plan_file?:string;plan?:{version:number}}|null};
const PAUSE=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));
export default function PreflightPanel({base,goal,busy,report,provider,request,action,saveSettings,refresh,onStarted}:{base:string;goal:string;busy:boolean;report?:Preflight|null;provider?:string;request:<T>(url:string,data?:unknown)=>Promise<T>;action:(fn:()=>Promise<void>)=>Promise<void>;saveSettings:()=>Promise<void>;refresh:()=>Promise<void>;onStarted?:()=>void}) {
  const [kind,setKind]=useState('coding'); const [options,setOptions]=useState<Options|null>(null);
  const [candidates,setCandidates]=useState<string[]>([]); const [judge,setJudge]=useState('');
  const [context,setContext]=useState(20000);const [two,setTwo]=useState(true);
  const [count,setCount]=useState(3);const [auto,setAuto]=useState('');
  function changeCount(value:number){
    setCount(value);
    setCandidates(old=>{const next=old.slice(0,value);while(next.length<value){const pick=options?.candidates.find(key=>!next.includes(key));next.push(pick||'');}return next;});
  }
  async function waitFor(done:(snapshot:SnapshotLite)=>boolean,label:string,timeout=3600000){
    const started=Date.now();
    for(;;){
      const snapshot=await request<SnapshotLite>(base); setAuto(label+' … '+snapshot.phase);
      if(done(snapshot)) return snapshot;
      if(Date.now()-started>timeout) throw Error('Zeitlimit für „'+label+'“ überschritten.');
      await PAUSE(1200);
    }
  }
  async function autopilot(){
    if(!goal.trim()||!judge||!candidates.some(Boolean)) return;
    await saveSettings();
    const before=await request<SnapshotLite>(base);
    setAuto('Vorabcheck wird gestartet …');
    await request(base+'/preflight',{goal,kind,candidates:[...new Set(candidates.filter(Boolean))],judge,context_tokens:context,two_temperatures:two});
    const checked=await waitFor(s=>!s.busy,'Vorabcheck');
    if(checked.error||checked.preflight?.status!=='ready') throw Error(checked.error||checked.preflight?.error||'Vorabcheck ohne auswertbare Empfehlung beendet.');
    setAuto('Empfehlung wird übernommen …');
    await request(base+'/preflight/accept',{goal});
    const accepted=await waitFor(s=>!s.busy&&(!!s.preflight?.accepted||!!s.error||!!s.preflight?.error),'Modell laden');
    if(!accepted.preflight?.accepted) throw Error(accepted.error||accepted.preflight?.error||'Empfehlung konnte nicht übernommen werden.');
    setAuto('Plan wird aus der Beschreibung erstellt …');
    await request(base+'/generate',{goal});
    const generated=await waitFor(s=>!s.busy&&((s.state?.plan_file||'')!==(before.state?.plan_file||'')||!!s.error),'Planerstellung');
    if(!generated.state?.plan_file) throw Error(generated.error||'Es wurde kein Aufgabenplan erstellt.');
    setAuto('Ausführung wird gestartet …');
    await request(base+'/start',{answer:''});
    const started=await waitFor(s=>s.busy||!!s.error||(s.state?.status||'READY')!=='READY','Start');
    if(started.error) throw Error(started.error);
    setAuto('Automatischer Ablauf abgeschlossen.');
    await refresh(); onStarted?.();
  }
  async function rerun(){
    if(!report) return;
    const list=[...new Set((report.candidates?.length?report.candidates:report.samples.map(sample=>sample.model)).filter(Boolean))];
    const judge=report.judge||options?.judge||'';
    if(!goal.trim()||!list.length||!judge) throw Error('Für den erneuten Vorabcheck zuerst Kandidaten und Auswertungsmodell wählen.');
    await saveSettings();
    setAuto('Vorabcheck wird erneut gestartet …');
    await request(base+'/preflight',{goal,kind:report.kind||kind,candidates:list,judge,context_tokens:report.context_tokens||context,two_temperatures:false});
    await refresh();
    setAuto('Vorabcheck erneut gestartet. Der bisherige Bericht bleibt bis zum neuen Ergebnis sichtbar.');
  }
  const stale=!!report?.goal&&report.goal.trim()!==goal.trim();
  return <section className="panel"><h2>1 · Modell-Vorabcheck</h2><p>Aufgabe oben beschreiben, Kandidaten vorschlagen lassen und Arbeitsproben vergleichen. {provider==='opencode'?'OpenCode Free lädt keine Modelle; die Arbeitsproben laufen nacheinander über den lokalen kostenlosen Dienst.':'Währenddessen werden alle Modelle am eingestellten LM-Studio-Server entladen. Andere Anwendungen dort bitte pausieren.'}</p>
    <div className="settings-grid"><label className="field">Testprofil<select disabled={busy} value={kind} onChange={e=>{setKind(e.target.value);setOptions(null);setCandidates([]);setJudge('');}}><option value="coding">Coding & Tests</option><option value="presentation">Präsentationen: Struktur & Verständlichkeit</option><option value="context">Großer Kontext / Quellenabgleich</option><option value="general">Allgemeine Aufgaben</option></select></label><label className="field">Kontext für diesen Vergleich<input type="number" min={4096} max={200000} value={context} disabled={busy} onChange={e=>setContext(Number(e.target.value))}/><small>20.000 als Ausgangswert; wird beim Laden geprüft. Kleine Abweichungen werden als geprüfter Ist-Wert übernommen.</small></label></div>
    <button className="button secondary" disabled={busy||!goal.trim()} onClick={()=>void action(async()=>{await saveSettings();const data=await request<Options>(base+'/preflight/options',{kind});setOptions(data);setCandidates(data.candidates.slice(0,count));setJudge(data.judge);})}>Installierte Modelle prüfen & Kandidaten vorschlagen</button>
    {options&&<><p>Drei bis sechs Kandidaten wählbar. Vorauswahl nach Modellfamilie, kein bereits gemessenes Qualitätsurteil. Quantisierung laut LM Studio beachten.</p><div className="settings-grid"><label className="field">Anzahl Kandidaten<select disabled={busy} value={count} onChange={e=>changeCount(Number(e.target.value))}>{[3,4,5,6].map(n=><option key={n} value={n}>{n} Kandidaten</option>)}</select></label>{Array.from({length:count},(_,i)=><label className="field" key={i}>Kandidat {i+1}<select disabled={busy} value={candidates[i]||''} onChange={e=>setCandidates(old=>{const next=[...old];while(next.length<count)next.push('');next[i]=e.target.value;return next;})}><option value="">Keiner</option>{options.models.map(m=><option key={m.key} value={m.key}>{m.key}{m.selected_variant?' · '+m.selected_variant:''}</option>)}</select></label>)}<label className="field">Allgemeines Auswertungsmodell<select disabled={busy} value={judge} onChange={e=>setJudge(e.target.value)}><option value="">Auswählen</option>{options.models.map(m=><option key={m.key} value={m.key}>{m.key}</option>)}</select></label></div><label className="check-label"><input type="checkbox" checked={two} disabled={busy} onChange={e=>setTwo(e.target.checked)}/>Zwei Temperaturen testen (höherer Zeitbedarf)</label><div className="inline-actions"><button className="button primary" disabled={busy||!judge||!candidates.some(Boolean)||!goal.trim()} onClick={()=>void action(async()=>{await saveSettings();await request(base+'/preflight',{goal,kind,candidates:[...new Set(candidates.filter(Boolean))],judge,context_tokens:context,two_temperatures:two});await refresh();})}>Vorabcheck starten</button><button className="button primary" disabled={busy||!judge||!candidates.some(Boolean)||!goal.trim()} onClick={()=>void action(autopilot)}>Automatisch: Vorabcheck → Empfehlung → Plan → Start</button></div>{auto&&<p role="status" className="field-hint">{auto}</p>}</>}
    {report&&<>{stale&&<p className="field-error" role="alert">Die Aufgabe wurde seit diesem Vorabcheck geändert. Bericht ist veraltet; bitte erneut ausführen.</p>}<p role="status">Status: {report.status==='ready'?'Ausgewertet':report.status==='running'?'Läuft':'Angehalten'}{report.accepted?' · übernommen':''}{report.status==='error'?' · Fehler':''}</p>{report.error&&<p role="alert">{report.error}</p>}{report.samples.map(s=><details key={s.id}><summary>{s.id} · {s.model} · T {s.temperature} · {s.seconds??'—'} s · {s.valid?'Format gültig':'Ungültig'}{report.verdict?.scores[s.id]!==undefined?' · Bewertung '+report.verdict.scores[s.id]+'/100':''}</summary><pre style={{whiteSpace:'pre-wrap'}}>{s.response||s.error}</pre></details>)}{report.recommendation&&<><h3>Empfehlung: {report.recommendation.model}</h3><p>Temperatur {report.recommendation.temperature} · Kontext {report.recommendation.context_tokens} Tokens</p><p>{report.recommendation.reason}</p><button className="button primary" disabled={busy||report.status!=='ready'||stale} onClick={()=>void action(async()=>{await request(base+'/preflight/accept',{goal});await refresh();})}>{provider==='opencode'?'Empfehlung übernehmen':'Empfehlung übernehmen & Modell laden'}</button></>}<div className="inline-actions"><button className="button secondary" disabled={busy||report.status==='running'||!goal.trim()} onClick={()=>void action(rerun)}>Vorabcheck erneut ausführen</button><button className="button secondary" disabled={busy||!goal.trim()} onClick={()=>void action(async()=>{await saveSettings();const data=await request<Options>(base+'/preflight/options',{kind:report.kind||kind});setOptions(data);setCandidates((report.candidates?.length?report.candidates:data.candidates).slice(0,count));setJudge(report.judge||data.judge);setAuto('Kandidaten aus dem letzten Bericht geladen; Auswahl kann geändert werden.');})}>Kandidaten erneut laden</button></div><p className="field-hint">{report.note} Ergebnisse werden im Projekt unter .toolforge/preflight-history gespeichert. Stoppen ist über die Übersicht möglich; laufende HTTP-Abfragen enden spätestens mit dem Zeitlimit.</p></>}
  </section>;
}
