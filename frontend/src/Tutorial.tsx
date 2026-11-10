import {useEffect,useLayoutEffect,useState} from 'react';
import type {CSSProperties} from 'react';

export type TourMode='main'|'developer';

type Step={selector?:string;title:string;text:string};
const tours:Record<TourMode,Step[]>={
 main:[
  {selector:'[data-tour="nav-projects"]',title:'Projekte',text:'Hier liegen alle Projekte. Die Kachelansicht eignet sich für wenige, die Listenansicht für viele Projekte. Projektgruppen sortieren den Bestand zusätzlich.'},
  {selector:'[data-tour="new-project"]',title:'Neues Projekt',text:'Lege ein Projekt an und gib ihm einen Namen. Die Beschreibung ist optional und dient später als Ausgangspunkt für den Aufgabenplan.'},
  {selector:'[data-tour="project-toolbar"]',title:'Ansicht & Gruppen',text:'Wechsle zwischen Kacheln und Liste. Über Gruppen ordnest du Projekte thematisch; ein Projekt lässt sich jederzeit in eine andere Gruppe oder zurück in „Ohne Gruppe“ verschieben.'},
  {selector:'[data-tour="pilot-open"]',title:'Pilot öffnen',text:'Im Entwicklungscockpit verbindest du einen Arbeitsordner. ToolForge liest den vorhandenen Stand ein und führt danach Aufgabenplan, Vorabcheck und Ausführung zusammen.'},
  {selector:'[data-tour="nav-roadmap"]',title:'Entwicklungspfad',text:'Der Entwicklungspfad zeigt die zehn integrierten Etappen von der Projektverwaltung bis zu Sandbox-Netzwerken.'},
  {selector:'[data-tour="nav-help"]',title:'Hilfe',text:'Die Hilfe enthält Bedienungsdokumente, einen dokumentgestützten Hilfechat und die beiden Tutorials. Beide Tutorials lassen sich hier jederzeit erneut starten.'},
  {selector:'[data-tour="topbar-actions"]',title:'Ton & Design',text:'Neben dem Designwechsel liegt der Hinweiston. Fahre mit der Maus über das Lautsprechersymbol, um die Lautstärke einzustellen.'},
  {selector:'[data-tour="shutdown"]',title:'Sauber beenden',text:'ToolForge beenden stoppt laufende Aufträge und den Server. Ein von ToolForge geöffnetes Chrome-/Edge-App-Fenster wird dabei automatisch geschlossen.'}
 ],
 developer:[
  {selector:'[data-tour="dev-tabs"]',title:'Entwicklungsbereich',text:'Die Tabs führen in dieser Reihenfolge durch den Arbeitsablauf: Verbesserungen, Dateien & Editor, KI-Änderungen, Ausführen & Prüfen, Git und Workflows.'},
  {selector:'[data-tour="dev-tab-improvements"]',title:'Verbesserungen',text:'Auch nach dem ersten Lauf kannst du Erweiterungen einreichen oder KI-Vorschläge anfordern. Bestehende Aufgaben und Prüfnachweise bleiben erhalten.'},
  {selector:'[data-tour="dev-tab-editor"]',title:'Dateien & Editor',text:'Dateibaum und Codeeditor arbeiten mit Versionsprüfung und Sicherungen. Ungespeicherte Entwürfe überstehen einen versehentlichen Tab-Wechsel.'},
  {selector:'[data-tour="dev-tab-ai"]',title:'KI-Änderungen',text:'Eine einzelne Datei ändern lassen, den Diff prüfen und den Vorschlag ausdrücklich übernehmen. Das ist getrennt vom automatischen Aufgabenplan.'},
  {selector:'[data-tour="dev-tab-run"]',title:'Ausführen & Prüfen',text:'Projektumgebung anlegen, Python starten, Tests, Linting und Typprüfung ausführen. Die Live-Ausgabe und der Abbruch bleiben unter dem aktiven Tab sichtbar.'},
  {selector:'[data-tour="dev-tab-git"]',title:'Git',text:'Status, Diff und Historie prüfen. Commits benötigen eine ausdrückliche Dateiauswahl und erfassen keine ungewollt vorgemerkten Dateien.'},
  {selector:'[data-tour="dev-tab-workflow"]',title:'Workflows',text:'Visuelle Knoten verbinden, konfigurieren und speichern. Python-, CSV-, Validierungs-, Duplikat- und Excel-Knoten teilen sich definierte Ein- und Ausgaben.'},
  {selector:'[data-tour="dev-output"]',title:'Live-Ausgabe',text:'Aufträge protokollieren hier und im Projektordner. Bei Problemen zeigt die Ausgabe den konkreten Grund; Abbruch beendet nur den aktuellen Auftrag.'}
 ]
};

function bounds(selector?:string){
 if(!selector)return null;
 const element=document.querySelector(selector);
 if(!element)return null;
 return element.getBoundingClientRect();
}

export default function Tutorial({mode,onClose}:{mode:TourMode;onClose:()=>void}){
 const steps=tours[mode];
 const [index,setIndex]=useState(0);
 const [rect,setRect]=useState<DOMRect|null>(null);
 const step=steps[index];
 useEffect(()=>{const handler=(event:KeyboardEvent)=>{if(event.key==='Escape')onClose();};window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);},[onClose]);
 useLayoutEffect(()=>{
  let frame=0;
  const target=step.selector?document.querySelector<HTMLElement>(step.selector):null;
  target?.scrollIntoView({block:'center',inline:'nearest',behavior:'smooth'});
  const update=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>setRect(bounds(step.selector)));};
  update();
  const delayed=window.setTimeout(update,350);
  window.addEventListener('resize',update);window.addEventListener('scroll',update,true);
  return()=>{window.clearTimeout(delayed);window.removeEventListener('resize',update);window.removeEventListener('scroll',update,true);cancelAnimationFrame(frame);};
 },[index,step.selector]);
 const last=index===steps.length-1;
 const viewport={width:window.innerWidth,height:window.innerHeight};
 const cardWidth=Math.min(360,viewport.width-28);
 let cardStyle:CSSProperties={left:Math.max(14,(viewport.width-cardWidth)/2),bottom:24};
 if(rect){
  const below=rect.bottom+18;
  const above=rect.top-18-220;
  const top=below+230<viewport.height?below:above>16?above:Math.max(16,viewport.height/2-110);
  cardStyle={left:Math.max(14,Math.min(viewport.width-cardWidth-14,rect.left+rect.width/2-cardWidth/2)),top,width:cardWidth};
 }
 return <div className="tour-layer">
  <div className="tour-blocker" aria-hidden="true" />
  {rect?<div className="tour-spotlight" aria-hidden="true" style={{top:Math.max(4,rect.top-6),left:Math.max(4,rect.left-6),width:rect.width+12,height:rect.height+12}}/>:<div className="tour-dim" aria-hidden="true"/>}
  <button className="tour-abort" onClick={onClose}>✕ Tutorial abbrechen</button>
  <section className="tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-title" style={cardStyle}>
   <div className="tour-top"><span className="tour-count">Tutorial {index+1} / {steps.length}</span><button className="text-button" onClick={onClose}>Tutorial beenden</button></div>
   <h2 id="tour-title">{step.title}</h2>
   <p>{step.text}</p>
   <div className="tour-actions">
    <button className="button secondary" disabled={index===0} onClick={()=>setIndex(index-1)}>Zurück</button>
    <button className="button primary" onClick={()=>last?onClose():setIndex(index+1)}>{last?'Tutorial abschließen':'Weiter'}</button>
   </div>
  </section>
 </div>;
}

export function TutorialWelcome({onStart,onSkip}:{onStart:()=>void;onSkip:()=>void}){
 return <div className="tour-layer welcome-layer">
  <div className="tour-dim" aria-hidden="true"/>
  <section className="tour-card welcome-card" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
   <span className="brand-mark welcome-mark" aria-hidden="true"><i/><i/><i/></span>
   <span className="eyebrow">WILLKOMMEN BEI TOOLFORGE</span>
   <h2 id="welcome-title">In wenigen Schritten zur eigenen Workbench.</h2>
   <p>Das kurze UI-Tutorial zeigt dir Projekte, Gruppen, Ansichten, den Pilot, den Entwicklungspfad, die Hilfe und das saubere Beenden. Das Entwickler-Tutorial startet beim ersten Besuch des Entwicklungsbereichs und ist jederzeit über die Hilfe erreichbar.</p>
   <div className="tour-actions"><button className="button secondary" onClick={onSkip}>Später</button><button className="button primary" onClick={onStart}>Tutorial starten</button></div>
  </section>
 </div>;
}
