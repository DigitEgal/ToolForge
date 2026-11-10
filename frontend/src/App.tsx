import HelpPanel from './HelpPanel';
import ProjectManager from './ProjectManager';
import PilotPanel from './PilotPanel';
import QuestionSound from './QuestionSound';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';

type Project = { id: string; name: string; description: string; created_at: string; folder_path?: string | null; archived?:boolean };
type Errors = { name?: string; description?: string; general?: string };
type IconName = 'grid' | 'plus' | 'search' | 'arrow' | 'sun' | 'moon' | 'folder' | 'close' | 'pilot' | 'route' | 'check' | 'refresh' | 'info';
const paths: Record<IconName, ReactNode> = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  plus: <path d="M12 5v14M5 12h14" />, search: <><circle cx="10.6" cy="10.6" r="6.5" /><path d="m16 16 5 5" /></>,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />, sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1" /></>,
  moon: <path d="M20 15A9 9 0 0 1 9 4a8 8 0 1 0 11 11Z" />,
  folder: <path d="M3 7a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />,
  close: <path d="m6 6 12 12M6 18 18 6" />, pilot: <><path d="m12 3 9 18-9-4-9 4Z" /><path d="M12 3v14" /></>,
  route: <><circle cx="5" cy="5" r="2" /><circle cx="19" cy="19" r="2" /><path d="M7 5h7a4 4 0 0 1 0 8h-4a3 3 0 0 0 0 6h7" /></>,
  check: <path d="m5 12 4 4L19 6" />, refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6 6a8 8 0 0 1 13 3M5 15a8 8 0 0 0 13 3" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></>
};
function Icon({ name }: { name: IconName }) { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>; }
class APIError extends Error { fields: Errors; constructor(message: string, fields: Errors = {}) { super(message); this.fields = fields; } }
async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json', 'X-ToolForge-Request': '1', ...options.headers } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const fields: Errors = {};
      if (response.status === 422 && Array.isArray(data.detail)) {
        for (const error of data.detail) {
          const field = error.loc?.[1];
          if (field === 'name') fields.name = 'Bitte einen Namen mit 1 bis 100 Zeichen eingeben.';
          if (field === 'description') fields.description = 'Die Beschreibung darf höchstens 2.000 Zeichen enthalten.';
        }
      }
      throw new APIError(typeof data.detail === 'string' ? data.detail : 'Die Eingaben konnten nicht gespeichert werden.', fields);
    }
    return data as T;
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new APIError('Die Verbindung zur lokalen Workbench ist unterbrochen. Bitte prüfen, ob der Server läuft, und erneut versuchen.');
  } finally { clearTimeout(timer); }
}
function initialTheme(): 'dark' | 'light' { try { return localStorage.getItem('toolforge-theme') === 'light' ? 'light' : 'dark'; } catch { return 'dark'; } }
function date(value: string) { return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(value)); }
const stages = [
  ['Projektverwaltung', 'Projekte anlegen, durchsuchen und lokal speichern.'],
  ['Entwicklungsbereich', 'Dateibaum, Codeeditor und sicheres Speichern.'],
  ['Python ausführen', 'Projektumgebungen, Start, Abbruch und Live-Ausgaben.'],
  ['Prüfen & testen', 'Automatisierte Tests, Linting und Typprüfung.'],
  ['Git-Versionierung', 'Änderungen vergleichen, Commits und Historie.'],
  ['KI-Unterstützung', 'Modellanbindung und kontrollierte Codeänderungen.'],
  ['Visuelle Workflows', 'Tools über Ein- und Ausgaben miteinander verbinden.'],
  ['Durchgängige Abnahme', 'CSV validieren, Duplikate entfernen und Excel exportieren.'],
  ['Docker-Sandbox', 'Projektbefehle optional im Container ausführen.'],
  ['Sandbox-Netzwerke', 'Gewählte Projektcontainer in einem internen Netz verbinden.']
];

export default function App() {
  const [theme, setTheme] = useState(initialTheme);
  const [view, setView] = useState<'projects' | 'roadmap' | 'pilot' | 'help'>('projects');
  const [workspaceProject,setWorkspaceProject] = useState<Project|null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [query, setQuery] = useState('');
  const [showArchived,setShowArchived]=useState(false);
  const [modal, setModal] = useState<'create' | 'detail' | 'pilot' | null>(null);
  const [name, setName] = useState(''); const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Errors>({}); const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<Project | null>(null); const [detailError, setDetailError] = useState('');
  const [detailId, setDetailId] = useState(''); const [detailLoading, setDetailLoading] = useState(false);
  const [pilotBusy, setPilotBusy] = useState(false); const [pilotError, setPilotError] = useState('');
  const [toast, setToast] = useState('');
  const [questions, setQuestions] = useState<string[]>([]);
  const dialog = useRef<HTMLDialogElement>(null); const nameInput = useRef<HTMLInputElement>(null);
  const loadSequence = useRef(0); const detailSequence = useRef(0);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem('toolforge-theme', theme); } catch { /* Private-mode storage may be unavailable. */ } }, [theme]);
  useEffect(() => { void refresh(); }, []);
  useEffect(() => { if (modal && dialog.current && !dialog.current.open) dialog.current.showModal(); if (!modal && dialog.current?.open) dialog.current.close(); if (modal === 'create') nameInput.current?.focus(); }, [modal]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 5000); return () => clearTimeout(t); }, [toast]);
  async function refresh() {
    const sequence = ++loadSequence.current; setLoading(true); setLoadError('');
    try { const data = await api<Project[]>('/api/projects'); if (sequence === loadSequence.current) setProjects(data); }
    catch (error) { if (sequence === loadSequence.current) setLoadError((error as Error).message); }
    finally { if (sequence === loadSequence.current) setLoading(false); }
  }
  function openCreate() { setName(''); setDescription(''); setErrors({}); setModal('create'); }
  function close() { if (!saving && !pilotBusy) { detailSequence.current++; setModal(null); } }
  async function create(event: FormEvent) {
    event.preventDefault(); if (saving) return;
    const checked: Errors = {}; const trimmed = name.trim();
    if (Array.from(trimmed).length < 1 || Array.from(trimmed).length > 100) checked.name = 'Bitte einen Namen mit 1 bis 100 Zeichen eingeben.';
    if (Array.from(description).length > 2000) checked.description = 'Die Beschreibung darf höchstens 2.000 Zeichen enthalten.';
    setErrors(checked); if (Object.keys(checked).length) { nameInput.current?.focus(); return; }
    setSaving(true);
    try {
      const project = await api<Project>('/api/projects', { method: 'POST', body: JSON.stringify({ name: trimmed, description }) });
      // Prevent an older list request from discarding the newly created record.
      loadSequence.current++; setLoading(false); setLoadError('');
      setProjects(previous => [project, ...previous.filter(p => p.id !== project.id)]);
      setQuery(''); setView('projects'); setModal(null); setToast(`„${project.name}“ wurde angelegt.`);
    } catch (error) {
      const e = error as APIError; setErrors({ ...e.fields, general: Object.keys(e.fields).length ? undefined : e.message });
    } finally { setSaving(false); }
  }
  async function openDetail(id: string) {
    const sequence = ++detailSequence.current; setModal('detail'); setDetailId(id); setDetail(null); setDetailError(''); setDetailLoading(true);
    try { const data = await api<Project>(`/api/projects/${encodeURIComponent(id)}`); if (sequence === detailSequence.current) setDetail(data); }
    catch (error) { if (sequence === detailSequence.current) setDetailError((error as Error).message); }
    finally { if (sequence === detailSequence.current) setDetailLoading(false); }
  }
  async function openPilot() {
    setPilotBusy(true); setPilotError('');
    try {
      const data = await api<{ message: string }>('/api/pilot/open', { method: 'POST', body: '{}' });
      setModal(null); setToast(data.message);
    } catch (error) { setPilotError((error as Error).message); }
    finally { setPilotBusy(false); }
  }
  const filtered = projects.filter(p => !!p.archived===showArchived).filter(p => `${p.name} ${p.description}`.toLocaleLowerCase('de').includes(query.trim().toLocaleLowerCase('de')));
  return <div className="app-shell">
    <a className="skip-link" href="#main">Zum Inhalt</a>
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><div>ToolForge<span>LOCAL WORKBENCH</span></div></div>
      <div className="workspace-label">DEIN ARBEITSBEREICH</div>
      <nav aria-label="Hauptnavigation">
        <button className={view === 'projects' ? 'nav active' : 'nav'} onClick={() => setView('projects')} aria-current={view === 'projects' ? 'page' : undefined}><Icon name="grid" />Projekte<span className="nav-count">{projects.length}</span></button>
        <button className={view === 'roadmap' ? 'nav active' : 'nav'} onClick={() => setView('roadmap')} aria-current={view === 'roadmap' ? 'page' : undefined}><Icon name="route" />Entwicklungspfad</button>
        <button className={view==='help'?'nav active':'nav'} onClick={()=>setView('help')}><Icon name="info"/>Hilfe</button>
      </nav>
      <section className="pilot-card"><div className="pilot-symbol"><Icon name="pilot" /></div><h2>Dein Pilot ist dabei.</h2><p>Aufgaben planen und Aider schrittweise arbeiten lassen.</p><button className="button secondary" onClick={() => { const active=projects.find(p=>!p.archived);if(active){setWorkspaceProject(active);setView('pilot');}else{setToast('Lege zuerst ein Projekt an und verbinde einen Arbeitsordner.');} }}>Pilot öffnen<Icon name="arrow" /></button></section>
      <div className="sidebar-bottom"><span className="local-dot" />Lokal auf deinem Rechner<span className="version">v0.8 · Pilot + Workbench</span></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><button className="button secondary" onClick={()=>{if(window.confirm('ToolForge beenden? Laufende Aufträge werden gestoppt. Ungespeicherte Editorentwürfe vorher speichern.'))void api('/api/shutdown',{method:'POST',body:'{}'}).then(()=>setToast('ToolForge wird beendet. Dieses Browserfenster kann geschlossen werden.')).catch(e=>setToast(e.message));}}>ToolForge beenden</button><div><span className="breadcrumb">Workbench</span><span className="slash">/</span><strong>{view === 'projects' ? 'Projekte' : view === 'pilot' ? 'Entwicklungscockpit' : view==='help'?'Hilfe':'Entwicklungspfad'}</strong></div><div className="topbar-actions"><QuestionSound questions={questions} /><button className="icon-button" aria-label={theme === 'dark' ? 'Helles Design aktivieren' : 'Dunkles Design aktivieren'} title="Design wechseln" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button></div></header>
      <main id="main" tabIndex={-1}>
        {view === 'help' ? <HelpPanel projects={projects}/> : view === 'pilot' && workspaceProject ? <PilotPanel key={workspaceProject.id} project={workspaceProject} onQuestions={setQuestions} onBack={()=>setView('projects')} onProject={project=>{setWorkspaceProject(project);setProjects(old=>old.map(p=>p.id===project.id?project:p));}} /> : view === 'projects' ? <>
          <section className="page-heading"><div><div className="eyebrow">VON DER IDEE ZUM EIGENEN TOOL</div><h1>Deine Projekte.</h1><p>Ein Platz für deine Ideen. Lokal gespeichert, bereit für den nächsten Schritt.</p></div><button className="button primary" onClick={openCreate}><Icon name="plus" />Neues Projekt</button></section>
          <div className="project-toolbar"><label className="check-label"><input type="checkbox" checked={showArchived} onChange={e=>setShowArchived(e.target.checked)}/>Archiv anzeigen</label><div className="section-title">Projektübersicht <span className="count">{projects.length}</span></div><div className="search-group"><label className="search"><Icon name="search" /><span className="sr-only">Projekte durchsuchen</span><input type="search" placeholder="Name oder Beschreibung suchen …" value={query} onChange={e => setQuery(e.target.value)} /></label><button className="icon-button" aria-label="Projekte aktualisieren" title="Aktualisieren" disabled={loading} onClick={() => void refresh()}><Icon name="refresh" /></button></div></div>
          {loadError && <div className="error-banner" role="alert"><Icon name="info" /><div><strong>Verbindung unterbrochen</strong><p>{loadError}</p></div><button className="button secondary" onClick={() => void refresh()}>Erneut versuchen</button></div>}
          {loading && projects.length === 0 ? <div className="loading-state" role="status"><span className="spinner" />Projekte werden geladen …</div> : !loadError && projects.length === 0 ? <section className="empty-state"><div className="empty-art" aria-hidden="true"><span className="orbit one" /><span className="orbit two" /><span className="empty-icon"><Icon name="folder" /></span><span className="spark">+</span></div><span className="eyebrow">RAUM FÜR DEINE IDEEN</span><h2>Was möchtest du bauen?</h2><p>Gib deinem ersten Projekt einen Namen.<br />Die Details kannst du direkt dazu festhalten.</p><button className="button primary" onClick={openCreate}><Icon name="plus" />Erstes Projekt anlegen</button><small>Deine Projektdaten bleiben auf diesem Rechner.</small></section> : filtered.length === 0 && !loadError ? <section className="no-results"><Icon name="search" /><h2>Keine passenden Projekte</h2><p>Versuche einen anderen Suchbegriff.</p><button className="button secondary" onClick={() => setQuery('')}>Suche zurücksetzen</button></section> : <div className="project-grid">{filtered.map((project, index) => <button className="project-card" key={project.id} onClick={() => void openDetail(project.id)} aria-label={`Projekt ${project.name} öffnen`}><div className="card-top"><span className={`project-icon color-${index % 4}`}><Icon name="folder" /></span><span className="project-label">PROJEKT</span><Icon name="arrow" /></div><h2>{project.name}</h2><p>{project.description || 'Noch keine Beschreibung hinterlegt.'}</p><div className="card-footer"><span>Erstellt am {date(project.created_at)}</span><span className="tiny-dot" /></div></button>)}</div>}
          <footer className="workspace-note"><Icon name="info" /><span>Projekte, Code, Prüfungen, Git und Workflows – lokal in einer Workbench.</span></footer>
        </> : <>
          <section className="page-heading"><div><div className="eyebrow">SCHRITT FÜR SCHRITT</div><h1>Der Entwicklungspfad.</h1><p>Ein klares Ziel. Zehn überprüfbare Etappen.</p></div><span className="stage-badge">Etappen 1–10 integriert</span></section>
          <div className="roadmap">{stages.map(([title, text], i) => <article className={i === 0 ? 'stage current' : 'stage'} key={title}><span className="stage-number">{i === 0 ? <Icon name="check" /> : String(i + 1).padStart(2, '0')}</span><div><h2>{title}</h2><p>{text}</p></div><span className="stage-status">{'Verfügbar'}</span></article>)}</div>
          <div className="roadmap-note"><Icon name="pilot" /><div><h2>Pilot und Workbench gehören zusammen.</h2><p>Der Pilot steuert die Entwicklungsaufträge. Die Workbench verwaltet deine Projekte. Arbeitsordner, Aufgabenpläne und Automatikläufe sind im Entwicklungscockpit integriert. Editor, Python-Jobs, Prüfungen, Git, KI-Vorschläge und visuelle Workflows stehen im Entwicklungsbereich bereit.</p></div></div>
        </>}
      </main>
    </div>
    {toast && <div className="toast" role="status"><Icon name="check" />{toast}</div>}
    <dialog ref={dialog} onCancel={event => { event.preventDefault(); close(); }} onClose={() => setModal(null)} aria-labelledby="dialog-title">
      <div className="dialog-top"><span className="dialog-eyebrow">{modal === 'create' ? 'NEUES PROJEKT' : modal === 'pilot' ? 'TOOLFORGE PILOT' : 'PROJEKTDETAILS'}</span><button className="icon-button" onClick={close} disabled={saving || pilotBusy} aria-label="Dialog schließen"><Icon name="close" /></button></div>
      {modal === 'create' && <form onSubmit={create} noValidate><h2 id="dialog-title">Eine neue Idee beginnt hier.</h2><p className="dialog-lead">Name und Beschreibung werden lokal gespeichert.</p><label className="field">Projektname <span aria-hidden="true">*</span><input ref={nameInput} name="name" value={name} onChange={e => setName(e.target.value)} placeholder="Zum Beispiel: CSV-Assistent" required aria-invalid={!!errors.name} aria-describedby={errors.name ? 'name-error' : 'name-hint'} disabled={saving} /></label>{errors.name ? <p className="field-error" id="name-error" role="alert">{errors.name}</p> : <p className="field-hint" id="name-hint">1 bis 100 Zeichen. Gleiche Namen sind erlaubt.</p>}<label className="field description-field">Beschreibung <span className="optional">optional</span><textarea name="description" rows={5} value={description} onChange={e => setDescription(e.target.value)} placeholder="Was soll dein Tool später können?" aria-invalid={!!errors.description} aria-describedby={errors.description ? 'description-error' : 'description-hint'} disabled={saving} /></label><div className="field-meta"><span id="description-hint">Ein kurzer Überblick über dein Vorhaben.</span><span>{Array.from(description).length.toLocaleString('de')} / 2.000</span></div>{errors.description && <p className="field-error" id="description-error" role="alert">{errors.description}</p>}{errors.general && <div className="form-error" role="alert">{errors.general} Deine Eingaben bleiben erhalten.</div>}<div className="dialog-actions"><button type="button" className="button secondary" onClick={close} disabled={saving}>Abbrechen</button><button type="submit" className="button primary" disabled={saving}>{saving ? <><span className="spinner" />Wird angelegt …</> : <>Projekt anlegen<Icon name="arrow" /></>}</button></div></form>}
      {modal === 'detail' && <><h2 id="dialog-title">{detail ? detail.name : 'Projektdetails'}</h2>{detailLoading && <p className="loading-state" role="status"><span className="spinner" />Details werden geladen …</p>}{detailError && <div className="form-error" role="alert">{detailError}<button className="button secondary" onClick={() => void openDetail(detailId)}>Erneut versuchen</button></div>}{detail && <><p className="detail-description">{detail.description || 'Für dieses Projekt wurde noch keine Beschreibung hinterlegt.'}</p><dl><dt>Erstellt am</dt><dd>{date(detail.created_at)}</dd><dt>Projekt-ID</dt><dd className="mono">{detail.id}</dd><dt>Speicherung</dt><dd>Lokal auf diesem Rechner</dd></dl><ProjectManager key={detail.id} project={detail} onChanged={()=>{close();void refresh();}}/><div className="detail-note"><Icon name="info" /><p>Öffne das Entwicklungscockpit, verbinde einen Arbeitsordner und lass den Pilot den gespeicherten Stand einlesen.</p></div></>}<div className="dialog-actions"><button className="button secondary" onClick={close}>Schließen</button>{detail && !detail.archived && <button className="button primary" onClick={()=>{setWorkspaceProject(detail);setView('pilot');close();}}>Entwicklungscockpit öffnen<Icon name="arrow" /></button>}</div></>}
      {modal === 'pilot' && <><h2 id="dialog-title">Automatisch weiterentwickeln.</h2><p className="dialog-lead">Öffne den mitgelieferten ToolForge Pilot als Desktop-Fenster.</p><div className="pilot-explainer"><span>01</span><p>Arbeitsordner im Pilot auswählen.</p><span>02</span><p>Modell und Aufgabenplan festlegen.</p><span>03</span><p>Prüfen lassen und automatisch fortsetzen.</p></div><p className="field-hint">Die Projekte dieser Workbench sind noch nicht mit den Arbeitsordnern im Pilot verknüpft. Der Pilot startet keinen Entwicklungsauftrag ohne deine Freigabe.</p>{pilotError && <div className="form-error" role="alert">{pilotError}</div>}<div className="dialog-actions"><button className="button secondary" onClick={close} disabled={pilotBusy}>Abbrechen</button><button className="button primary" onClick={() => void openPilot()} disabled={pilotBusy}>{pilotBusy ? 'Wird geöffnet …' : 'Pilot-Fenster öffnen'}<Icon name="arrow" /></button></div></>}
    </dialog>
  </div>;
}
