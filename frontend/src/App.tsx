import BrandMark from './BrandMark';
import QuestionSound from './QuestionSound';
import Tutorial, { TutorialWelcome, type TourMode } from './Tutorial';
import DigitEgalLogo from './DigitEgalLogo';
import { LanguageSwitch, tr, useI18n } from './i18n';
import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
const HelpPanel = lazy(() => import('./HelpPanel'));
const ProjectManager = lazy(() => import('./ProjectManager'));
const PilotPanel = lazy(() => import('./PilotPanel'));

type Project = { id: string; name: string; description: string; created_at: string; folder_path?: string | null; archived?:boolean; group_id?: string | null };
type ProjectGroup = { id: string; name: string; created_at: string; project_count: number };
type GlobalQuestion = { id: string; folder: string; project: string; task: string; title: string; question: string; status?: string };
type Layout = 'grid' | 'list';
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
          if (field === 'name') fields.name = tr('Bitte einen Namen mit 1 bis 100 Zeichen eingeben.', 'Enter a name between 1 and 100 characters.');
          if (field === 'description') fields.description = tr('Die Beschreibung darf höchstens 2.000 Zeichen enthalten.', 'The description may contain at most 2,000 characters.');
        }
      }
      throw new APIError(typeof data.detail === 'string' ? data.detail : tr('Die Eingaben konnten nicht gespeichert werden.', 'The input could not be saved.'), fields);
    }
    return data as T;
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new APIError(tr('Die Verbindung zur lokalen Workbench ist unterbrochen. Bitte prüfen, ob der Server läuft, und erneut versuchen.', 'The connection to the local workbench was interrupted. Check that the server is running and try again.'));
  } finally { clearTimeout(timer); }
}
function initialTheme(): 'dark' | 'light' { try { return localStorage.getItem('toolforge-theme') === 'light' ? 'light' : 'dark'; } catch { return 'dark'; } }
function date(value: string, locale = 'de-DE') { return new Intl.DateTimeFormat(locale, { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(value)); }
function PanelFallback({ label }: { label: string }) { return <div className="loading-state" role="status"><span className="spinner" />{label}</div>; }
const stageData: [string, string, string, string][] = [
  ['Projektverwaltung', 'Project management', 'Projekte anlegen, durchsuchen und lokal speichern.', 'Create, search and store projects locally.'],
  ['Entwicklungsbereich', 'Development area', 'Dateibaum, Codeeditor und sicheres Speichern.', 'File tree, code editor and safe saving.'],
  ['Python ausführen', 'Run Python', 'Projektumgebungen, Start, Abbruch und Live-Ausgaben.', 'Project environments, start, cancel and live output.'],
  ['Prüfen & testen', 'Check & test', 'Automatisierte Tests, Linting und Typprüfung.', 'Automated tests, linting and type checking.'],
  ['Git-Versionierung', 'Git versioning', 'Änderungen vergleichen, Commits und Historie.', 'Compare changes, commits and history.'],
  ['KI-Unterstützung', 'AI support', 'Modellanbindung und kontrollierte Codeänderungen.', 'Model connection and controlled code changes.'],
  ['Visuelle Workflows', 'Visual workflows', 'Tools über Ein- und Ausgaben miteinander verbinden.', 'Connect tools through inputs and outputs.'],
  ['Durchgängige Abnahme', 'End-to-end acceptance', 'CSV validieren, Duplikate entfernen und Excel exportieren.', 'Validate CSV, remove duplicates and export Excel.'],
  ['Docker-Sandbox', 'Docker sandbox', 'Projektbefehle optional im Container ausführen.', 'Optionally run project commands in a container.'],
  ['Sandbox-Netzwerke', 'Sandbox networks', 'Gewählte Projektcontainer in einem internen Netz verbinden.', 'Connect selected project containers in an internal network.'],
  ['Analyse & Betrieb', 'Analysis & operations', 'Inkrementeller Index, Messreihen, Anwendungsabnahme, Graph, Presets und Sicherungen.', 'Incremental index, benchmarks, application acceptance, graph, presets and backups.'],
  ['Marke & Performance', 'Brand & performance', 'Einheitliches Logo, konsolidierte Berichte und ein schnellerer Start durch geteilte Ladebereiche.', 'Unified logo, consolidated reports and faster startup through shared lazy areas.'],
  ['OpenCode Free & kleine Modelle', 'OpenCode Free & small models', 'Kostenlose Modelle, klare Modellquellen-Presets, gemeinsames Free-Kontingent und kompaktere Prompts.', 'Free models, explicit source presets, a shared free quota and more compact prompts.'],
  ['Übergabe, Prüfung & Zweisprachigkeit', 'Handoff, review & bilingual UI', 'Gestoppte Aufgaben an andere Modelle übergeben, Ergebnisse unabhängig prüfen und die Oberfläche zwischen Deutsch und Englisch umschalten.', 'Hand stuck tasks to other models, review results independently and switch the interface between German and English.']
];

export default function App() {
  const { t, locale } = useI18n();
  const stages = stageData.map(([deTitle, enTitle, deText, enText]) => [t(deTitle, enTitle), t(deText, enText)] as const);
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
  const [globalQuestions, setGlobalQuestions] = useState<GlobalQuestion[]>([]);
  const [shutdown, setShutdown] = useState(false);
  const [groups, setGroups] = useState<ProjectGroup[]>([]);
  const [layout, setLayout] = useState<Layout>(() => { try { return localStorage.getItem('toolforge-project-layout') === 'list' ? 'list' : 'grid'; } catch { return 'grid'; } });
  const [showGroups, setShowGroups] = useState(false); const [newGroup, setNewGroup] = useState(''); const [groupBusy, setGroupBusy] = useState(false);
  const [tour, setTour] = useState<TourMode | null>(null);
  const [developRequest, setDevelopRequest] = useState(0);
  const [welcome, setWelcome] = useState(() => { try { return localStorage.getItem('toolforge-tutorial-seen') !== '1'; } catch { return false; } });
  const dialog = useRef<HTMLDialogElement>(null); const nameInput = useRef<HTMLInputElement>(null);
  const loadSequence = useRef(0); const detailSequence = useRef(0);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem('toolforge-theme', theme); } catch { /* Private-mode storage may be unavailable. */ } }, [theme]);
  useEffect(() => { try { localStorage.setItem('toolforge-project-layout', layout); } catch { /* Private-mode storage may be unavailable. */ } }, [layout]);
  useEffect(() => { const handler = (event: Event) => { const mode = (event as CustomEvent<string>).detail; if (mode === 'main') { setView('projects'); setTour('main'); return; } if (mode === 'pilot' || mode === 'collaboration') { if (!workspaceProject) { setToast(t('Öffne zuerst ein Projekt mit Arbeitsordner, um dieses Tutorial zu starten.', 'Open a project with a connected working folder first to start this tutorial.')); return; } setView('pilot'); setTour(mode as TourMode); window.setTimeout(() => window.dispatchEvent(new CustomEvent('toolforge-pilot-tab', { detail: mode === 'collaboration' ? 'collaboration' : 'dashboard' })), 250); return; } if (mode === 'developer') { if (!workspaceProject) { setToast(t('Öffne zuerst ein Projekt mit Arbeitsordner, um das Entwickler-Tutorial zu starten.', 'Open a project with a connected working folder first to start the developer tutorial.')); return; } try { localStorage.setItem('toolforge-dev-tutorial-seen', '1'); } catch { /* unavailable */ } setView('pilot'); setDevelopRequest(value => value + 1); setTour('developer'); } }; window.addEventListener('toolforge-tour', handler); return () => window.removeEventListener('toolforge-tour', handler); }, [workspaceProject]);
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    let active = true; let source: EventSource | undefined; let timer: number | undefined;
    const connect = () => {
      if (!active) return;
      source = new EventSource('/api/events');
      source.addEventListener('questions', event => {
        try {
          const data = JSON.parse((event as MessageEvent).data) as { questions?: GlobalQuestion[] };
          const rows = Array.isArray(data.questions) ? data.questions : [];
          setGlobalQuestions(rows);
          // Outside the cockpit, surface global questions through the sound/badge channel.
          if (view !== 'pilot') setQuestions(rows.map(row => `${row.project}: ${row.title || row.task}`));
        } catch { /* Ignore malformed heartbeat payloads. */ }
      });
      source.onerror = () => { source?.close(); source = undefined; if (active) timer = window.setTimeout(connect, 5000); };
    };
    connect();
    return () => { active = false; if (timer) window.clearTimeout(timer); source?.close(); };
  }, [view]);
  useEffect(() => { if (modal && dialog.current && !dialog.current.open) dialog.current.showModal(); if (!modal && dialog.current?.open) dialog.current.close(); if (modal === 'create') nameInput.current?.focus(); }, [modal]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 5000); return () => clearTimeout(t); }, [toast]);
  async function refresh() {
    const sequence = ++loadSequence.current; setLoading(true); setLoadError('');
    try {
      const [data, groupData] = await Promise.all([api<Project[]>('/api/projects'), api<ProjectGroup[]>('/api/groups')]);
      if (sequence === loadSequence.current) { setProjects(data); setGroups(groupData); }
    }
    catch (error) { if (sequence === loadSequence.current) setLoadError((error as Error).message); }
    finally { if (sequence === loadSequence.current) setLoading(false); }
  }
  function closeTour() { if (tour === 'main') { try { localStorage.setItem('toolforge-tutorial-seen', '1'); } catch { /* unavailable */ } } setTour(null); }
  function startMainTour() { setWelcome(false); try { localStorage.setItem('toolforge-tutorial-seen', '1'); } catch { /* unavailable */ } setView('projects'); setTour('main'); }
  function skipWelcome() { setWelcome(false); try { localStorage.setItem('toolforge-tutorial-seen', '1'); } catch { /* unavailable */ } }
  async function createGroup(event: FormEvent) {
    event.preventDefault(); const name = newGroup.trim(); if (!name || groupBusy) return;
    setGroupBusy(true);
    try { const group = await api<ProjectGroup>('/api/groups', { method: 'POST', body: JSON.stringify({ name }) }); setGroups(old => [...old, group]); setNewGroup(''); setToast(t(`Gruppe „${group.name}“ wurde angelegt.`, `Group “${group.name}” was created.`)); }
    catch (error) { setToast((error as Error).message); }
    finally { setGroupBusy(false); }
  }
  async function renameGroup(group: ProjectGroup) {
    const name = window.prompt(t('Neuer Name der Projektgruppe:', 'New project group name:'), group.name)?.trim(); if (!name || name === group.name) return;
    setGroupBusy(true);
    try { const updated = await api<ProjectGroup>(`/api/groups/${group.id}`, { method: 'PATCH', body: JSON.stringify({ name }) }); setGroups(old => old.map(g => g.id === group.id ? updated : g)); setToast(t('Projektgruppe umbenannt.', 'Project group renamed.')); }
    catch (error) { setToast((error as Error).message); }
    finally { setGroupBusy(false); }
  }
  async function deleteGroup(group: ProjectGroup) {
    if (!window.confirm(t(`Projektgruppe „${group.name}“ löschen? Die Projekte bleiben erhalten und wechseln zu „Ohne Gruppe“.`, `Delete project group “${group.name}”? The projects remain and move to “Ungrouped”.`))) return;
    setGroupBusy(true);
    try {
      await api(`/api/groups/${group.id}`, { method: 'DELETE' });
      setGroups(old => old.filter(g => g.id !== group.id));
      setProjects(old => old.map(p => p.group_id === group.id ? { ...p, group_id: null } : p));
      setToast(t('Projektgruppe gelöscht. Projekte bleiben erhalten.', 'Project group deleted. Projects remain.'));
    } catch (error) { setToast((error as Error).message); }
    finally { setGroupBusy(false); }
  }
  async function moveProject(project: Project, groupId: string) {
    setGroupBusy(true);
    try {
      const updated = await api<Project>(`/api/projects/${project.id}`, { method: 'PATCH', body: JSON.stringify({ group_id: groupId || null }) });
      setProjects(old => old.map(p => p.id === updated.id ? updated : p));
      if (detail?.id === updated.id) setDetail(updated);
      setToast(groupId ? t('Projekt verschoben.', 'Project moved.') : t('Projekt aus der Gruppe entfernt.', 'Project removed from the group.'));
    } catch (error) { setToast((error as Error).message); }
    finally { setGroupBusy(false); }
  }
  function openCreate() { setName(''); setDescription(''); setErrors({}); setModal('create'); }
  function close() { if (!saving && !pilotBusy) { detailSequence.current++; setModal(null); } }
  async function create(event: FormEvent) {
    event.preventDefault(); if (saving) return;
    const checked: Errors = {}; const trimmed = name.trim();
    if (Array.from(trimmed).length < 1 || Array.from(trimmed).length > 100) checked.name = t('Bitte einen Namen mit 1 bis 100 Zeichen eingeben.', 'Enter a name between 1 and 100 characters.');
    if (Array.from(description).length > 2000) checked.description = t('Die Beschreibung darf höchstens 2.000 Zeichen enthalten.', 'The description may contain at most 2,000 characters.');
    setErrors(checked); if (Object.keys(checked).length) { nameInput.current?.focus(); return; }
    setSaving(true);
    try {
      const project = await api<Project>('/api/projects', { method: 'POST', body: JSON.stringify({ name: trimmed, description }) });
      // Prevent an older list request from discarding the newly created record.
      loadSequence.current++; setLoading(false); setLoadError('');
      setProjects(previous => [project, ...previous.filter(p => p.id !== project.id)]);
      setQuery(''); setView('projects'); setModal(null); setToast(t(`„${project.name}“ wurde angelegt.`, `“${project.name}” was created.`));
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
  const filtered = projects.filter(p => !!p.archived===showArchived).filter(p => `${p.name} ${p.description}`.toLocaleLowerCase(locale).includes(query.trim().toLocaleLowerCase(locale)));
  async function shutDown() {
    if (!window.confirm(t('ToolForge beenden? Laufende Aufträge werden gestoppt. Ungespeicherte Editorentwürfe vorher speichern.', 'Quit ToolForge? Running tasks will be stopped. Save unsaved editor drafts first.'))) return;
    try { await api('/api/shutdown', { method: 'POST', body: '{}' }); }
    catch (e) { setToast((e as Error).message); return; }
    setShutdown(true);
    // Browsers only allow closing windows opened by script; the overlay stays as fallback.
    try { window.close(); } catch { /* Fallback below. */ }
    window.setTimeout(() => { try { window.close(); } catch { /* Fallback below. */ } }, 400);
  }
  const knownGroupIds = new Set(groups.map(group => group.id));
  const ungrouped = filtered.filter(project => !project.group_id || !knownGroupIds.has(project.group_id));
  const visibleGroups = groups.map(group => ({ ...group, projects: filtered.filter(project => project.group_id === group.id) })).filter(group => !query.trim() || group.projects.length > 0);
  function projectCard(project: Project, index: number) {
    return <button className="project-card" key={project.id} onClick={() => void openDetail(project.id)} aria-label={t(`Projekt ${project.name} öffnen`, `Open project ${project.name}`)}><div className="card-top"><span className={`project-icon color-${index % 4}`}><Icon name="folder" /></span><span className="project-label">{t('PROJEKT', 'PROJECT')}</span><Icon name="arrow" /></div><h2>{project.name}</h2><p>{project.description || t('Noch keine Beschreibung hinterlegt.', 'No description yet.')}</p><div className="card-footer"><span>{t('Erstellt am', 'Created on')} {date(project.created_at, locale)}</span><span className="tiny-dot" /></div></button>;
  }
  function projectRow(project: Project, index: number) {
    return <div className="project-row" key={project.id}><button className="project-row-main" onClick={() => void openDetail(project.id)} aria-label={t(`Projekt ${project.name} öffnen`, `Open project ${project.name}`)}><span className={`project-icon color-${index % 4}`}><Icon name="folder" /></span><span className="project-row-text"><strong>{project.name}</strong><small>{project.description || t('Noch keine Beschreibung hinterlegt.', 'No description yet.')}</small></span><span className="project-row-date">{date(project.created_at, locale)}</span><Icon name="arrow" /></button><label className="project-row-group"><span>{t('Gruppe', 'Group')}</span><select value={project.group_id || ''} disabled={groupBusy} onClick={event => event.stopPropagation()} onChange={event => void moveProject(project, event.target.value)}><option value="">{t('Ohne Gruppe', 'Ungrouped')}</option>{groups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label></div>;
  }
  function projectCollection(items: Project[], start = 0) {
    return layout === 'grid' ? <div className="project-grid">{items.map((project, index) => projectCard(project, start + index))}</div> : <div className="project-list">{items.map((project, index) => projectRow(project, start + index))}</div>;
  }
  if (shutdown) return <div className="shutdown-screen" role="status">
    <div className="shutdown-card"><BrandMark /><h1>{t('ToolForge wurde beendet.', 'ToolForge has quit.')}</h1>
      <p>{t('Der lokale Server ist gestoppt. Du kannst dieses Browserfenster jetzt schließen.', 'The local server has stopped. You can close this browser window now.')}</p>
      <button className="button primary" onClick={() => { try { window.close(); } catch { /* Browser blockiert das Schließen. */ } }}>{t('Fenster schließen', 'Close window')}</button>
      <p className="field-hint">{t('Falls sich das Fenster nicht automatisch schließt, blockiert der Browser das Schließen per Skript. Schließe den Tab dann mit Strg+W.', 'If the window does not close automatically, the browser blocked script-based closing. Close the tab with Ctrl+W.')}</p>
    </div>
  </div>;
  return <div className="app-shell">
    <a className="skip-link" href="#main">{t('Zum Inhalt', 'Skip to content')}</a>
    <aside className="sidebar">
      <div className="brand-block"><div className="brand"><BrandMark /><div>ToolForge<span>LOCAL WORKBENCH</span></div></div></div>
      <div className="workspace-label">{t('DEIN ARBEITSBEREICH', 'YOUR WORKSPACE')}</div>
      <nav aria-label={t('Hauptnavigation', 'Main navigation')}>
        <button data-tour="nav-projects" className={view === 'projects' ? 'nav active' : 'nav'} onClick={() => setView('projects')} aria-current={view === 'projects' ? 'page' : undefined}><Icon name="grid" />{t('Projekte', 'Projects')}<span className="nav-count">{projects.length}</span></button>
        <button data-tour="nav-roadmap" className={view === 'roadmap' ? 'nav active' : 'nav'} onClick={() => setView('roadmap')} aria-current={view === 'roadmap' ? 'page' : undefined}><Icon name="route" />{t('Entwicklungspfad', 'Development path')}</button>
        <button data-tour="nav-help" className={view==='help'?'nav active':'nav'} onClick={()=>setView('help')}><Icon name="info"/>{t('Hilfe', 'Help')}</button>
      </nav>
      <section className="pilot-card"><div className="pilot-symbol"><Icon name="pilot" /></div><h2>{t('Dein Pilot ist dabei.', 'Your Pilot is ready.')}</h2><p>{t('Aufgaben planen und Aider schrittweise arbeiten lassen.', 'Plan tasks and let Aider work step by step.')}</p><div className="inline-actions"><button data-tour="pilot-open" className="button secondary" disabled={pilotBusy} onClick={() => void openPilot()}>{pilotBusy ? t('Pilot startet …', 'Pilot starting …') : t('Pilot öffnen', 'Open Pilot')}<Icon name="arrow" /></button><button className="button secondary" onClick={() => { const active=projects.find(p=>!p.archived);if(active){setWorkspaceProject(active);setView('pilot');}else{setToast(t('Lege zuerst ein Projekt an und verbinde einen Arbeitsordner.', 'Create a project first and connect a working folder.'));} }}>{t('Cockpit öffnen', 'Open cockpit')}</button></div>{pilotError && <p className="field-error" role="alert">{pilotError}</p>}</section>
      <div className="sidebar-bottom"><span className="local-dot" />{t('Lokal auf deinem Rechner', 'Local on your computer')}<span className="version">V1.4 · Pilot + Workbench</span><DigitEgalLogo compact /></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><button data-tour="shutdown" className="button secondary" onClick={()=>void shutDown()}>{t('ToolForge beenden', 'Quit ToolForge')}</button><div><span className="breadcrumb">Workbench</span><span className="slash">/</span><strong>{view === 'projects' ? t('Projekte', 'Projects') : view === 'pilot' ? t('Entwicklungscockpit', 'Development cockpit') : view==='help'?t('Hilfe', 'Help'):t('Entwicklungspfad', 'Development path')}</strong></div><div className="topbar-actions" data-tour="topbar-actions"><LanguageSwitch /><QuestionSound questions={questions} /><button className="icon-button" aria-label={theme === 'dark' ? t('Helles Design aktivieren', 'Enable light theme') : t('Dunkles Design aktivieren', 'Enable dark theme')} title={t('Design wechseln', 'Switch theme')} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button></div></header>
      <main id="main" tabIndex={-1}>
        {globalQuestions.length > 0 && view !== 'pilot' && <div className="global-question-banner" role="status">
          <Icon name="info" />
          <div><strong>{t(`${globalQuestions.length} offene Rückfrage${globalQuestions.length === 1 ? '' : 'n'}`, `${globalQuestions.length} open question${globalQuestions.length === 1 ? '' : 's'}`)}</strong><p>{globalQuestions.slice(0, 2).map(row => `${row.project}: ${row.title || row.task} — ${row.question}`).join(' · ')}</p></div>
          <button className="button secondary" onClick={() => { const target = projects.find(item => item.folder_path === globalQuestions[0].folder); if (target) { setWorkspaceProject(target); setView('pilot'); } else setToast(t('Projekt nicht in der Übersicht gefunden. Öffne es erneut.', 'Project not found in the overview. Open it again.')); }}>{t('Im Cockpit öffnen', 'Open in cockpit')}</button>
        </div>}
        {view === 'help' ? <Suspense fallback={<PanelFallback label={t('Hilfe wird geladen …', 'Loading help …')} />}><HelpPanel projects={projects}/></Suspense> : view === 'pilot' && workspaceProject ? <Suspense fallback={<PanelFallback label={t('Entwicklungscockpit wird geladen …', 'Loading development cockpit …')} />}><PilotPanel key={workspaceProject.id} project={workspaceProject} developRequest={developRequest} onDevelopOpened={()=>setDevelopRequest(0)} onQuestions={setQuestions} onBack={()=>setView('projects')} onProject={project=>{setWorkspaceProject(project);setProjects(old=>old.map(p=>p.id===project.id?project:p));}} /></Suspense> : view === 'projects' ? <>
          <section className="page-heading"><div><div className="eyebrow">{t('VON DER IDEE ZUM EIGENEN TOOL', 'FROM IDEA TO YOUR OWN TOOL')}</div><h1>{t('Deine Projekte.', 'Your projects.')}</h1><p>{t('Ein Platz für deine Ideen. Lokal gespeichert, bereit für den nächsten Schritt.', 'A place for your ideas. Stored locally, ready for the next step.')}</p></div><button data-tour="new-project" className="button primary" onClick={openCreate}><Icon name="plus" />{t('Neues Projekt', 'New project')}</button></section>
          <div className="project-toolbar" data-tour="project-toolbar">
            <div className="toolbar-left">
              <label className="check-label"><input type="checkbox" checked={showArchived} onChange={e=>setShowArchived(e.target.checked)}/>{t('Archiv anzeigen', 'Show archive')}</label>
              <div className="view-switch" role="group" aria-label={t('Projektansicht', 'Project view')}><button className={layout==='grid'?'active':''} aria-pressed={layout==='grid'} onClick={()=>setLayout('grid')}><Icon name="grid" />{t('Kacheln', 'Grid')}</button><button className={layout==='list'?'active':''} aria-pressed={layout==='list'} onClick={()=>setLayout('list')}><Icon name="route" />{t('Liste', 'List')}</button></div>
              <button className="button secondary compact-button" onClick={()=>setShowGroups(!showGroups)}>{t('Gruppen', 'Groups')} {groups.length?`· ${groups.length}`:''}</button>
            </div>
            <div className="section-title">{t('Projektübersicht', 'Project overview')} <span className="count">{projects.length}</span></div>
            <div className="search-group"><label className="search"><Icon name="search" /><span className="sr-only">{t('Projekte durchsuchen', 'Search projects')}</span><input type="search" placeholder={t('Name oder Beschreibung suchen …', 'Search name or description …')} value={query} onChange={e => setQuery(e.target.value)} /></label><button className="icon-button" aria-label={t('Projekte aktualisieren', 'Refresh projects')} title={t('Aktualisieren', 'Refresh')} disabled={loading} onClick={() => void refresh()}><Icon name="refresh" /></button></div>
          </div>
          {showGroups && <section className="panel group-panel" data-tour="groups">
            <div className="panel-title"><h2>{t('Projektgruppen', 'Project groups')}</h2><button className="text-button" onClick={()=>setShowGroups(false)}>{t('Schließen', 'Close')}</button></div>
            <p>{t('Gruppen sortieren die Projektübersicht. Projekte verschiebst du hier über die Listenansicht oder in den Projektdetails; beim Löschen einer Gruppe bleiben alle Projekte erhalten.', 'Groups organize the project overview. Move projects here through the list view or in the project details; deleting a group keeps all projects.')}</p>
            <form className="group-create" onSubmit={createGroup}><input aria-label={t('Neue Projektgruppe', 'New project group')} placeholder={t('Neue Gruppe, z. B. Buchhaltung', 'New group, e.g. Accounting')} value={newGroup} maxLength={60} onChange={e=>setNewGroup(e.target.value)} disabled={groupBusy}/><button className="button primary" type="submit" disabled={groupBusy||!newGroup.trim()}>{t('Gruppe anlegen', 'Create group')}</button></form>
            {groups.length ? <div className="group-list">{groups.map(group=><div className="group-row" key={group.id}><span><strong>{group.name}</strong><small>{t(`${projects.filter(project=>project.group_id===group.id).length} Projekte`, `${projects.filter(project=>project.group_id===group.id).length} projects`)}</small></span><button className="text-button" disabled={groupBusy} onClick={()=>void renameGroup(group)}>{t('Umbenennen', 'Rename')}</button><button className="text-button danger-text" disabled={groupBusy} onClick={()=>void deleteGroup(group)}>{t('Löschen', 'Delete')}</button></div>)}</div> : <p className="group-empty">{t('Noch keine Projektgruppe angelegt.', 'No project group created yet.')}</p>}
          </section>}
          {loadError && <div className="error-banner" role="alert"><Icon name="info" /><div><strong>{t('Verbindung unterbrochen', 'Connection interrupted')}</strong><p>{loadError}</p></div><button className="button secondary" onClick={() => void refresh()}>{t('Erneut versuchen', 'Try again')}</button></div>}
          {loading && projects.length === 0 ? <div className="loading-state" role="status"><span className="spinner" />{t('Projekte werden geladen …', 'Loading projects …')}</div> : !loadError && projects.length === 0 ? <section className="empty-state"><div className="empty-art" aria-hidden="true"><span className="orbit one" /><span className="orbit two" /><span className="empty-icon"><Icon name="folder" /></span><span className="spark">+</span></div><span className="eyebrow">{t('RAUM FÜR DEINE IDEEN', 'ROOM FOR YOUR IDEAS')}</span><h2>{t('Was möchtest du bauen?', 'What do you want to build?')}</h2><p>{t('Gib deinem ersten Projekt einen Namen.', 'Give your first project a name.')}<br />{t('Die Details kannst du direkt dazu festhalten.', 'You can add the details right away.')}</p><button className="button primary" onClick={openCreate}><Icon name="plus" />{t('Erstes Projekt anlegen', 'Create first project')}</button><small>{t('Deine Projektdaten bleiben auf diesem Rechner.', 'Your project data stays on this computer.')}</small></section> : filtered.length === 0 && !loadError ? <section className="no-results"><Icon name="search" /><h2>{t('Keine passenden Projekte', 'No matching projects')}</h2><p>{t('Versuche einen anderen Suchbegriff.', 'Try a different search term.')}</p><button className="button secondary" onClick={() => setQuery('')}>{t('Suche zurücksetzen', 'Reset search')}</button></section> : groups.length === 0 ? projectCollection(filtered) : <div className="project-groups">
            {visibleGroups.map(group=><section className="project-group" key={group.id}><div className="group-heading"><h2>{group.name}</h2><span className="count">{group.projects.length}</span></div>{group.projects.length?projectCollection(group.projects):<p className="group-empty">{t('Noch keine Projekte in dieser Gruppe.', 'No projects in this group yet.')}</p>}</section>)}
            {ungrouped.length>0&&<section className="project-group"><div className="group-heading"><h2>{t('Ohne Gruppe', 'Ungrouped')}</h2><span className="count">{ungrouped.length}</span></div>{projectCollection(ungrouped)}</section>}
          </div>}
          <footer className="workspace-note"><Icon name="info" /><span>{t('Projekte, Code, Prüfungen, Git und Workflows – lokal in einer Workbench.', 'Projects, code, checks, Git and workflows — locally in one workbench.')}</span></footer>
        </> : <>
          <section className="page-heading"><div><div className="eyebrow">{t('SCHRITT FÜR SCHRITT', 'STEP BY STEP')}</div><h1>{t('Der Entwicklungspfad.', 'The development path.')}</h1><p>{t('Ein klares Ziel. Vierzehn überprüfbare Etappen.', 'A clear goal. Fourteen verifiable stages.')}</p></div><span className="stage-badge">{t('Etappen 1–14 integriert', 'Stages 1–14 integrated')}</span></section>
          <div className="roadmap">{stages.map(([title, text], i) => <article className={i === 0 ? 'stage current' : 'stage'} key={title}><span className="stage-number">{i === 0 ? <Icon name="check" /> : String(i + 1).padStart(2, '0')}</span><div><h2>{title}</h2><p>{text}</p></div><span className="stage-status">{t('Verfügbar', 'Available')}</span></article>)}</div>
          <div className="roadmap-note"><Icon name="pilot" /><div><h2>{t('Pilot und Workbench gehören zusammen.', 'Pilot and workbench belong together.')}</h2><p>{t('Der Pilot steuert die Entwicklungsaufträge. Die Workbench verwaltet deine Projekte. Arbeitsordner, Aufgabenpläne und Automatikläufe sind im Entwicklungscockpit integriert. Editor, Python-Jobs, Prüfungen, Git, KI-Vorschläge und visuelle Workflows stehen im Entwicklungsbereich bereit.', 'The Pilot controls development tasks. The workbench manages your projects. Working folders, task plans and automated runs are integrated in the development cockpit. The development area provides the editor, Python jobs, checks, Git, AI suggestions and visual workflows.')}</p></div></div>
        </>}
      </main>
    </div>
    {toast && <div className="toast" role="status"><Icon name="check" />{toast}</div>}
    <dialog ref={dialog} onCancel={event => { event.preventDefault(); close(); }} onClose={() => setModal(null)} aria-labelledby="dialog-title">
      <div className="dialog-top"><span className="dialog-eyebrow">{modal === 'create' ? t('NEUES PROJEKT', 'NEW PROJECT') : modal === 'pilot' ? 'TOOLFORGE PILOT' : t('PROJEKTDETAILS', 'PROJECT DETAILS')}</span><button className="icon-button" onClick={close} disabled={saving || pilotBusy} aria-label={t('Dialog schließen', 'Close dialog')}><Icon name="close" /></button></div>
      {modal === 'create' && <form onSubmit={create} noValidate><h2 id="dialog-title">{t('Eine neue Idee beginnt hier.', 'A new idea starts here.')}</h2><p className="dialog-lead">{t('Name und Beschreibung werden lokal gespeichert.', 'Name and description are stored locally.')}</p><label className="field">{t('Projektname', 'Project name')} <span aria-hidden="true">*</span><input ref={nameInput} name="name" value={name} onChange={e => setName(e.target.value)} placeholder={t('Zum Beispiel: CSV-Assistent', 'For example: CSV assistant')} required aria-invalid={!!errors.name} aria-describedby={errors.name ? 'name-error' : 'name-hint'} disabled={saving} /></label>{errors.name ? <p className="field-error" id="name-error" role="alert">{errors.name}</p> : <p className="field-hint" id="name-hint">{t('1 bis 100 Zeichen. Gleiche Namen sind erlaubt.', '1 to 100 characters. Duplicate names are allowed.')}</p>}<label className="field description-field">{t('Beschreibung', 'Description')} <span className="optional">{t('optional', 'optional')}</span><textarea name="description" rows={5} value={description} onChange={e => setDescription(e.target.value)} placeholder={t('Was soll dein Tool später können?', 'What should your tool be able to do?')} aria-invalid={!!errors.description} aria-describedby={errors.description ? 'description-error' : 'description-hint'} disabled={saving} /></label><div className="field-meta"><span id="description-hint">{t('Ein kurzer Überblick über dein Vorhaben.', 'A short overview of your idea.')}</span><span>{Array.from(description).length.toLocaleString(locale)} / 2.000</span></div>{errors.description && <p className="field-error" id="description-error" role="alert">{errors.description}</p>}{errors.general && <div className="form-error" role="alert">{errors.general} {t('Deine Eingaben bleiben erhalten.', 'Your input is preserved.')}</div>}<div className="dialog-actions"><button type="button" className="button secondary" onClick={close} disabled={saving}>{t('Abbrechen', 'Cancel')}</button><button type="submit" className="button primary" disabled={saving}>{saving ? <><span className="spinner" />{t('Wird angelegt …', 'Creating …')}</> : <>{t('Projekt anlegen', 'Create project')}<Icon name="arrow" /></>}</button></div></form>}
      {modal === 'detail' && <><h2 id="dialog-title">{detail ? detail.name : t('Projektdetails', 'Project details')}</h2>{detailLoading && <p className="loading-state" role="status"><span className="spinner" />{t('Details werden geladen …', 'Loading details …')}</p>}{detailError && <div className="form-error" role="alert">{detailError}<button className="button secondary" onClick={() => void openDetail(detailId)}>{t('Erneut versuchen', 'Try again')}</button></div>}{detail && <><p className="detail-description">{detail.description || t('Für dieses Projekt wurde noch keine Beschreibung hinterlegt.', 'No description has been added for this project yet.')}</p><dl><dt>{t('Erstellt am', 'Created on')}</dt><dd>{date(detail.created_at, locale)}</dd><dt>{t('Projekt-ID', 'Project ID')}</dt><dd className="mono">{detail.id}</dd><dt>{t('Speicherung', 'Storage')}</dt><dd>{t('Lokal auf diesem Rechner', 'Local on this computer')}</dd></dl><label className="field project-group-select">{t('Projektgruppe', 'Project group')}<select value={detail.group_id || ''} disabled={groupBusy} onChange={event => void moveProject(detail, event.target.value)}><option value="">{t('Ohne Gruppe', 'Ungrouped')}</option>{groups.map(group=><option key={group.id} value={group.id}>{group.name}</option>)}</select><small>{t('Verschiebt nur die Zuordnung in der Übersicht. Projektdateien bleiben unverändert.', 'Only changes the assignment in the overview. Project files stay unchanged.')}</small></label><Suspense fallback={<p className="loading-state" role="status"><span className="spinner" />{t('Projektverwaltung wird geladen …', 'Loading project management …')}</p>}><ProjectManager key={detail.id} project={detail} onChanged={()=>{close();void refresh();}}/></Suspense><div className="detail-note"><Icon name="info" /><p>{t('Öffne das Entwicklungscockpit, verbinde einen Arbeitsordner und lass den Pilot den gespeicherten Stand einlesen.', 'Open the development cockpit, connect a working folder and let the Pilot read the saved state.')}</p></div></>}<div className="dialog-actions"><button className="button secondary" onClick={close}>{t('Schließen', 'Close')}</button>{detail && !detail.archived && <button className="button primary" onClick={()=>{setWorkspaceProject(detail);setView('pilot');close();}}>{t('Entwicklungscockpit öffnen', 'Open development cockpit')}<Icon name="arrow" /></button>}</div></>}
      {modal === 'pilot' && <><h2 id="dialog-title">{t('Automatisch weiterentwickeln.', 'Develop automatically.')}</h2><p className="dialog-lead">{t('Öffne den mitgelieferten ToolForge Pilot als Desktop-Fenster.', 'Open the included ToolForge Pilot as a desktop window.')}</p><div className="pilot-explainer"><span>01</span><p>{t('Arbeitsordner im Pilot auswählen.', 'Select a working folder in the Pilot.')}</p><span>02</span><p>{t('Modell und Aufgabenplan festlegen.', 'Choose the model and task plan.')}</p><span>03</span><p>{t('Prüfen lassen und automatisch fortsetzen.', 'Run checks and continue automatically.')}</p></div><p className="field-hint">{t('Die Projekte dieser Workbench sind noch nicht mit den Arbeitsordnern im Pilot verknüpft. Der Pilot startet keinen Entwicklungsauftrag ohne deine Freigabe.', 'Projects in this workbench are not yet linked to working folders in the Pilot. The Pilot never starts a development task without your approval.')}</p>{pilotError && <div className="form-error" role="alert">{pilotError}</div>}<div className="dialog-actions"><button className="button secondary" onClick={close} disabled={pilotBusy}>{t('Abbrechen', 'Cancel')}</button><button className="button primary" onClick={() => void openPilot()} disabled={pilotBusy}>{pilotBusy ? t('Wird geöffnet …', 'Opening …') : t('Pilot-Fenster öffnen', 'Open Pilot window')}<Icon name="arrow" /></button></div></>}
    </dialog>
    {tour && <Tutorial mode={tour} onClose={closeTour}/>}
    {welcome && !tour && <TutorialWelcome onStart={startMainTour} onSkip={skipWelcome}/>}
  </div>;
}
