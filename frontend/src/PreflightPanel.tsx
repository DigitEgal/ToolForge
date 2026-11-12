import {useState} from 'react';
import type {Preflight, Settings, SourcesInfo} from './pilotTypes';

type OptionModel = {key:string; max_context_length?:number; selected_variant?:string; source?:string; source_label?:string};
type Options = {models:OptionModel[]; candidates:string[]; judge:string; sources?:{source:string;blocked:boolean}[]; blocked_message?:string; prefix?:boolean};
type SnapshotLite = {busy:boolean;phase:string;error?:string;preflight?:Preflight|null;state?:{status?:string;plan_file?:string;plan?:{version:number}}|null};
const PAUSE=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));
const SOURCE_LABELS:Record<string,string>={local:'Lokal (LM Studio)',free:'OpenCode Free',api:'API (bezahlt)'};
const MODE_LABELS:Record<string,string>={local:'Nur Lokal',free:'Nur Free',api:'Nur API',free_local:'Free & Lokal',local_api:'Lokal & API',free_api:'Free & API'};
const PREFERENCE_LABELS:Record<string,string>={max_quality:'MAX Quality',balanced:'Preis/Leistung',cost_saving:'Kostensparend'};

function splitKey(key:string,prefix:boolean|undefined):[string|null,string]{
  const index=key.indexOf('::');
  if(prefix&&index>0){
    const source=key.slice(0,index);const model=key.slice(index+2);
    if(SOURCE_LABELS[source]&&model)return[source,model];
  }
  return[null,key];
}

export default function PreflightPanel({base,goal,busy,report,settings,sourcesInfo,request,action,saveSettings,refresh,onStarted}:{base:string;goal:string;busy:boolean;report?:Preflight|null;settings?:Settings|null;sourcesInfo?:SourcesInfo|null;request:<T>(url:string,data?:unknown)=>Promise<T>;action:(fn:()=>Promise<void>)=>Promise<void>;saveSettings:()=>Promise<void>;refresh:()=>Promise<void>;onStarted?:()=>void}) {
  const [kind,setKind]=useState('coding'); const [options,setOptions]=useState<Options|null>(null);
  const [candidates,setCandidates]=useState<string[]>([]); const [judge,setJudge]=useState('');
  const [context,setContext]=useState(20000);const [two,setTwo]=useState(true);
  const [count,setCount]=useState(3);const [auto,setAuto]=useState('');
  const labels=sourcesInfo?.labels||SOURCE_LABELS;
  const modes=sourcesInfo?.modes||MODE_LABELS;
  const preferences=sourcesInfo?.preferences||PREFERENCE_LABELS;
  const prefix=report?.source_prefix??options?.prefix;
  function sourceText(key:string,knownPrefix=prefix){
    const[source,model]=splitKey(key,knownPrefix);
    return source?`${labels[source]||source} · ${model}`:model;
  }
  function sourceOf(key:string){
    const[source,model]=splitKey(key,prefix);
    return{source,model};
  }
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
  const staleGoal=!!report?.goal&&report.goal.trim()!==goal.trim();
  const stalePreset=!!report&&((!!report.source_mode&&report.source_mode!==settings?.source_mode)||(!!report.preference&&report.preference!==settings?.preference));
  const stale=staleGoal||stalePreset;
  const reportMode=report?.source_mode?modes[report.source_mode]||report.source_mode:'';
  const reportPreference=report?.preference?preferences[report.preference]||report.preference:'';
  const recSource=report?.recommendation?(report.recommendation.source||sourceOf(report.recommendation.model).source):null;
  const freeRecommendation=recSource==='free'||(!recSource&&report?.provider==='opencode');
  const quotaReported=!!report&&(/rate.?limit|quota|kontingent|tageslimit|429/i.test(report.error||'')||(report.skipped_sources||[]).length>0);
  async function rerun(){
    if(!report) return;
    if(!goal.trim()) throw Error('Für den erneuten Vorabcheck zuerst eine Aufgabe beschreiben.');
    await saveSettings();
    let list=[...new Set((report.candidates?.length?report.candidates:report.samples.map(sample=>sample.model)).filter(Boolean))];
    let judgeValue=report.judge||options?.judge||'';
    const testKind=report.kind||kind;
    const testContext=report.context_tokens||context;
    if(stalePreset||!list.length||!judgeValue){
      // A changed preset invalidates prefixed model keys. Refresh the options
      // instead of sending old source keys into the new profile.
      const data=await request<Options>(base+'/preflight/options',{kind:testKind});
      setOptions(data);setCandidates(data.candidates.slice(0,count));setJudge(data.judge);
      list=data.candidates;judgeValue=data.judge;
      if(!list.length||!judgeValue) throw Error('Für den erneuten Vorabcheck zuerst Kandidaten und Auswertungsmodell wählen.');
    }
    setAuto('Vorabcheck wird erneut gestartet …');
    await request(base+'/preflight',{goal,kind:testKind,candidates:list,judge:judgeValue,context_tokens:testContext,two_temperatures:false});
    await refresh();
    setAuto('Vorabcheck erneut gestartet. Der bisherige Bericht bleibt bis zum neuen Ergebnis sichtbar.');
  }
  return <section className="panel preflight-panel"><h2>1 · Modell-Vorabcheck</h2><p>Aufgabe oben beschreiben, Kandidaten vorschlagen lassen und Arbeitsproben vergleichen. {report?.sources?.includes('free')?'OpenCode Free lädt keine Modelle in den Arbeitsspeicher; die Arbeitsproben laufen nacheinander über den lokalen kostenlosen Dienst. Alle Free-Modelle teilen sich dabei ein Tageskontingent.':'Währenddessen werden lokale Modelle am eingestellten LM-Studio-Server entladen. Andere Anwendungen dort bitte pausieren.'}</p>
    <div className="settings-grid"><label className="field">Testprofil<select disabled={busy} value={kind} onChange={e=>{setKind(e.target.value);setOptions(null);setCandidates([]);setJudge('');}}><option value="coding">Coding & Tests</option><option value="presentation">Präsentationen: Struktur & Verständlichkeit</option><option value="context">Großer Kontext / Quellenabgleich</option><option value="general">Allgemeine Aufgaben</option></select></label><label className="field">Kontext für diesen Vergleich<input type="number" min={4096} max={200000} value={context} disabled={busy} onChange={e=>setContext(Number(e.target.value))}/><small>20.000 als Ausgangswert; wird beim Laden geprüft. Kleine Abweichungen werden als geprüfter Ist-Wert übernommen.</small></label></div>
    <button className="button secondary" disabled={busy||!goal.trim()} onClick={()=>void action(async()=>{await saveSettings();const data=await request<Options>(base+'/preflight/options',{kind});setOptions(data);setCandidates(data.candidates.slice(0,count));setJudge(data.judge);})}>Installierte Modelle prüfen & Kandidaten vorschlagen</button>
    {options&&<><p>Drei bis sechs Kandidaten wählbar. Vorauswahl nach Modellfamilie, kein bereits gemessenes Qualitätsurteil. {options.prefix?'Kandidaten sind mit ihrer Quelle gekennzeichnet.':'Quantisierung laut Quelle beachten.'}</p>{options.blocked_message&&<p className="field-error" role="status">{options.blocked_message}</p>}<div className="settings-grid"><label className="field">Anzahl Kandidaten<select disabled={busy} value={count} onChange={e=>changeCount(Number(e.target.value))}>{[3,4,5,6].map(n=><option key={n} value={n}>{n} Kandidaten</option>)}</select></label>{Array.from({length:count},(_,i)=><label className="field" key={i}>Kandidat {i+1}<select disabled={busy} value={candidates[i]||''} onChange={e=>setCandidates(old=>{const next=[...old];while(next.length<count)next.push('');next[i]=e.target.value;return next;})}><option value="">Keiner</option>{options.models.map(m=><option key={m.key} value={m.key}>{m.source_label?m.source_label+' · ':''}{m.key}{m.selected_variant?' · '+m.selected_variant:''}</option>)}</select></label>)}<label className="field">Allgemeines Auswertungsmodell<select disabled={busy} value={judge} onChange={e=>setJudge(e.target.value)}><option value="">Auswählen</option>{options.models.map(m=><option key={m.key} value={m.key}>{m.source_label?m.source_label+' · ':''}{m.key}</option>)}</select></label></div><label className="check-label"><input type="checkbox" checked={two} disabled={busy} onChange={e=>setTwo(e.target.checked)}/>Zwei Temperaturen testen (höherer Zeitbedarf; bei Free-Kontingent sparsam einsetzen)</label><div className="inline-actions"><button className="button primary" disabled={busy||!judge||!candidates.some(Boolean)||!goal.trim()} onClick={()=>void action(async()=>{await saveSettings();await request(base+'/preflight',{goal,kind,candidates:[...new Set(candidates.filter(Boolean))],judge,context_tokens:context,two_temperatures:two});await refresh();})}>Vorabcheck starten</button><button className="button primary" disabled={busy||!judge||!candidates.some(Boolean)||!goal.trim()} onClick={()=>void action(autopilot)}>Automatisch: Vorabcheck → Empfehlung → Plan → Start</button></div>{auto&&<p role="status" className="field-hint">{auto}</p>}</>}
    {report&&<><div className="preflight-status"><p role="status">Status: {report.status==='ready'?'Ausgewertet':report.status==='running'?'Läuft':'Angehalten'}{report.accepted?' · übernommen':''}{report.status==='error'?' · Fehler':''}{reportMode?` · Profil ${reportMode}`:''}{reportPreference?` · ${reportPreference}`:''}</p><div className="inline-actions"><button className="button secondary" disabled={busy||report.status==='running'||!goal.trim()} onClick={()=>void action(rerun)}>Vorabcheck erneut ausführen</button><button className="button secondary" disabled={busy||!goal.trim()} onClick={()=>void action(async()=>{await saveSettings();const data=await request<Options>(base+'/preflight/options',{kind:report.kind||kind});setOptions(data);setCandidates((report.candidates?.length?report.candidates:data.candidates).slice(0,count));setJudge(report.judge||data.judge);setAuto('Kandidaten aus dem letzten Bericht geladen; Auswahl kann geändert werden.');})}>Kandidaten erneut laden</button></div></div>
      {staleGoal&&<p className="field-error" role="alert">Die Aufgabe wurde seit diesem Vorabcheck geändert. Bericht ist veraltet; bitte erneut ausführen.</p>}
      {!staleGoal&&stalePreset&&<p className="field-error" role="alert">Quellen-Vorauswahl oder Reihenfolge wurde geändert. Der Bericht gilt für {reportMode||'die bisherige Vorauswahl'}{reportPreference?` · ${reportPreference}`:''}. Bitte erneut ausführen.</p>}
      {quotaReported&&<p className="field-hint" role="note"><strong>Free-Kontingent:</strong> Alle OpenCode-Free-Modelle teilen sich das Tageslimit. Ein anderer Free-Modellname schafft kein neues Kontingent. Für einen erneuten Lauf eine im Profil erlaubte lokale oder bezahlte API-Quelle wählen oder auf den Reset warten.</p>}
      {report.error&&<p role="alert" className="field-error">{report.error}</p>}
      {!!report.skipped_sources?.length&&<details open><summary>Übersprungene Kandidaten ({report.skipped_sources.length})</summary><ul>{report.skipped_sources.map(key=><li key={key}>{sourceText(key)}</li>)}</ul><small>Die Quelle war beim Lauf vorübergehend gesperrt. Der Bericht bleibt für ungesperrte Kandidaten auswertbar.</small></details>}
      {report.samples.map(s=><details key={s.id}><summary>{s.id} · {sourceText(s.model)} · T {s.temperature} · {s.seconds??'—'} s · {s.valid?'Format gültig':'Ungültig'}{report.verdict?.scores[s.id]!==undefined?' · Bewertung '+report.verdict.scores[s.id]+'/100':''}</summary><pre style={{whiteSpace:'pre-wrap'}}>{s.response||s.error}</pre></details>)}
      {!!report.alternatives?.length&&<details><summary>Gemessene Ausweichquellen ({report.alternatives.length})</summary><div className="table-wrap"><table><thead><tr><th>Quelle</th><th>Modell</th><th>Temperatur</th><th>Kontext</th><th>Bewertung</th></tr></thead><tbody>{report.alternatives.map(row=><tr key={row.model}><td>{labels[row.source||'']||sourceOf(row.model).source||'—'}</td><td>{sourceOf(row.model).model}</td><td>{row.temperature}</td><td>{row.context_tokens}</td><td>{row.score??'—'}</td></tr>)}</tbody></table></div><small>Nur gemessene Kandidaten aus genau diesem Lauf. Bei einem späteren Quellenwechsel kann eine bereits geprüfte Alternative übernommen werden.</small></details>}
      {report.recommendation&&<><h3>Empfehlung: {sourceText(report.recommendation.model)}</h3><p>Temperatur {report.recommendation.temperature} · Kontext {report.recommendation.context_tokens} Tokens{report.recommendation.score!==undefined?` · Bewertung ${report.recommendation.score}/100`:''}</p><p>{report.recommendation.reason}</p><button className="button primary" disabled={busy||report.status!=='ready'||stale} onClick={()=>void action(async()=>{await request(base+'/preflight/accept',{goal});await refresh();})}>{freeRecommendation?'Empfehlung übernehmen':'Empfehlung übernehmen & Modell laden'}</button></>}
      {report.accepted_settings&&<p className="field-hint">Übernommen: {labels[report.accepted_settings.source||'']||report.accepted_settings.source||report.accepted_settings.provider||'—'} · {report.accepted_settings.model||'—'} · {report.accepted_settings.context_tokens??'—'} Tokens</p>}
      <p className="field-hint">{report.note} Ergebnisse werden im Projekt unter .toolforge/preflight-history gespeichert; der letzte Bericht bleibt auch nach einem Fehler sichtbar.</p>
    </>}
  </section>;
}
