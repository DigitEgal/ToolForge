import { useEffect, useState } from 'react';
import type { Snapshot } from './pilotTypes';
import { useI18n } from './i18n';

type RequestFn = <T>(path: string, data?: unknown, method?: string) => Promise<T>;
type Coverage = { files_total: number; files_included: number; chars_total: number; chars_included: number; percent: number; budget_chars: number; manifest_chars: number };
type Analysis = { coverage: Coverage; manifest: { files_total: number; truncated: boolean }; chunks: { path: string; part: number; parts: number; start_line: number; end_line: number }[]; batches: { file: string; parts: number; included: boolean }[] };
type IndexState = { indexed: boolean; summary?: { files?: number; indexed?: number; symbols?: number; dependencies?: number; errors?: number; truncated?: boolean; languages?: Record<string, number> } | null; last_change?: { changed_count?: number; removed_count?: number; unchanged?: number; changed?: string[]; removed?: string[] } | null };
type GraphNode = { id: string; title: string; status: string; priority: number; depends_on: string[]; open_dependencies: string[]; files: string[]; conflicts: string[]; blocking_conflicts: string[]; approved_files: string[]; approval_missing: string[]; blocked: boolean; question?: string | null };
type Graph = { nodes: GraphNode[]; edges: { from: string; to: string }[]; conflicts: { file: string; tasks: string[]; blocking: boolean; approved: boolean; note: string }[]; critical_path: string[]; ready: string[]; summary: { tasks?: number; verified?: number; blocked?: number; conflicts?: number; blocking_conflicts?: number; approved_conflicts?: number } };
type Scenario = { id: string; kind: string; passed?: boolean; error?: string; output?: string; informational?: boolean; url?: string; argv?: string[]; code?: number };
type ScenarioReport = { at: number; passed: boolean; review_required: boolean; reviewed_at?: number | null; review_note?: string; scenarios: Scenario[]; test_changes: { added: string[]; removed: string[]; changed: string[]; diffs: { path: string; diff: string }[] } };
type BenchmarkGroup = { model: string; context_tokens: number; quantization: string; samples: number; quality_mean: number; quality_stdev: number; tokens_per_second: number | null; vram_peak_bytes: number | null };
type BenchmarkSample = { id: string; context_tokens: number; valid: boolean; score: number; tokens_per_second?: number | null; vram_bytes?: number | null; error?: string };
type BenchmarkReport = { status: string; model: string; contexts: number[]; repeats: number; samples: BenchmarkSample[]; groups: BenchmarkGroup[]; recommendation?: { model: string; context_tokens: number; quantization: string; quality_mean: number; quality_stdev: number; tokens_per_second: number | null; vram_peak_bytes: number | null; reason: string } | null; cached?: boolean; error?: string };
type Backup = { file: string; reason: string; at: number; version: number; goal: string; tasks: number };
type Operations = { installer: { installer_definition: boolean; build_script: boolean; inno_setup_available: boolean; signtool_available: boolean; certificate_configured: boolean; signed: boolean; note: string }; tray: { available: boolean; optional_file: string; note: string }; plan_backups?: Backup[] };
type Environment = { generated_at: number; controller: { python: string; requirements: { name: string; version: string; installed: string | null }[] }; aider: { python: string; installed_version: string | null; pinned: { name: string; version: string }[] }; docker: { available: boolean; tag: string; image_id: string | null; repo_digests: string[]; note?: string }; presets_folder: string; reproducible: boolean };
type ResearchSource = { title: string; url: string; host: string; snippet: string; evidence?: { text: string; score: number }[] };
type ResearchEntry = { id: string; at: number; query: string; task: string; domains: string[]; results: ResearchSource[]; error: string; cached?: boolean };
type SandboxState = { docker_cli?: boolean; docker_available: boolean; daemon_available?: boolean; daemon_version?: string; daemon_error?: string; tag: string; image: { tag: string; id: string; repo_digests: string[]; created: string; size: number | null } | null; network: string | null; networks: { name: string; driver: string; scope: string }[]; error?: string };

function bytes(value: number | null | undefined) {
  if (!value) return '—';
  if (value > 1024 ** 3) return (value / 1024 ** 3).toFixed(1) + ' GB';
  if (value > 1024 ** 2) return (value / 1024 ** 2).toFixed(0) + ' MB';
  return (value / 1024).toFixed(0) + ' KB';
}
function stamp(value: number | null | undefined, locale: string) {
  return value ? new Date(value * 1000).toLocaleString(locale) : '—';
}

export default function AdvancedPanel({ base, snapshot, busy, request, action, refresh }: { base: string; snapshot: Snapshot; busy: boolean; request: RequestFn; action: (fn: () => Promise<void>) => Promise<void>; refresh: () => Promise<void> }) {
  const { t, locale } = useI18n();
  const graph = (snapshot.graph || { nodes: [], edges: [], conflicts: [], critical_path: [], ready: [], summary: {} }) as unknown as Graph;
  const report = snapshot.scenarios as unknown as ScenarioReport | null;
  const benchmark = snapshot.benchmark as unknown as BenchmarkReport | null;
  const operations = (snapshot.operations || {}) as unknown as Operations;
  const environment = snapshot.environment;
  const index = (snapshot.index || { indexed: false }) as IndexState;
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [models, setModels] = useState<{ id: string; type: string }[]>([]);
  const [benchContexts, setBenchContexts] = useState(String(snapshot.settings.context_tokens));
  const [benchRepeats, setBenchRepeats] = useState(2);
  const [benchKind, setBenchKind] = useState('coding');
  const [benchModel, setBenchModel] = useState(snapshot.settings.model);
  const [benchJudge, setBenchJudge] = useState('');
  const [benchGoal, setBenchGoal] = useState(snapshot.state?.plan.goal || '');
  const [benchForce, setBenchForce] = useState(false);
  const [researchQuery, setResearchQuery] = useState('');
  const [researchTask, setResearchTask] = useState('manual');
  const [researchForce, setResearchForce] = useState(false);
  const [research, setResearch] = useState<ResearchEntry | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [lock, setLock] = useState<Environment | null>(null);
  const [presetName, setPresetName] = useState('mein-preset');
  const [presetFile, setPresetFile] = useState('');
  const [importPath, setImportPath] = useState('');
  const [importOverwrite, setImportOverwrite] = useState(false);
  const [sandbox, setSandbox] = useState<SandboxState | null>(null);
  const [packageManager, setPackageManager] = useState('pip');
  const [packageName, setPackageName] = useState('');
  const [packageVersion, setPackageVersion] = useState('');

  async function loadSandbox() {
    try { setSandbox(await request<SandboxState>(base + '/sandbox')); } catch { setSandbox(null); }
  }
  const pause = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
  async function sandboxAction(path: string, data: unknown = {}) {
    await request(path, data);
    for (let attempt = 0; attempt < 300; attempt += 1) {
      await pause(1000);
      const current = await request<Snapshot>(base);
      if (!current.busy) {
        await loadSandbox();
        await refresh();
        if (current.error) throw new Error(current.error);
        return;
      }
    }
    throw new Error(t('Der Sandbox-Auftrag meldet nach fünf Minuten noch keinen Abschluss. Protokoll prüfen.', 'The sandbox job has not completed after five minutes. Check the log.'));
  }
  useEffect(() => { void loadSandbox(); }, []);
  const priorities: Record<string, number> = Object.fromEntries(graph.nodes.map(node => [node.id, node.priority]));
  async function graphUpdate(data: Record<string, unknown>) {
    await request(base + '/graph', data);
    await refresh();
  }
  async function runAnalysis() {
    const result = await request<Analysis>(base + '/analysis', { max_chars: 60000 });
    setAnalysis(result);
  }
  const sandboxBadge = sandbox?.docker_available
    ? t('Docker bereit', 'Docker ready')
    : sandbox?.docker_cli ? t('Daemon nicht erreichbar', 'Daemon unreachable') : t('Docker fehlt', 'Docker missing');

  return <div className="advanced-panel">
    <section className="panel">
      <div className="panel-title"><h2>{t('Vollständige Projektanalyse', 'Full project analysis')}</h2><span className="stage-badge">{index.indexed ? t('Index aktuell', 'Index up to date') : t('Noch kein Index', 'No index yet')}</span></div>
      <p>{t('Dateien werden inkrementell über Signatur neu gelesen. Der Index enthält Symbole, Importe und Abhängigkeiten aller Dateien; große Projekte werden in belegten Teilabschnitten gelesen.', 'Files are re-read incrementally by signature. The index contains symbols, imports and dependencies of all files; large projects are read in documented chunks.')}</p>
      {index.summary && <div className="metrics compact"><article><span>{t('Dateien', 'Files')}</span><strong>{index.summary.files || 0}</strong></article><article><span>{t('Symbole', 'Symbols')}</span><strong>{index.summary.symbols || 0}</strong></article><article><span>{t('Abhängigkeiten', 'Dependencies')}</span><strong>{index.summary.dependencies || 0}</strong></article><article><span>{t('Lesefehler', 'Read errors')}</span><strong>{index.summary.errors || 0}</strong></article></div>}
      {index.last_change && <p className="field-hint">{t('Letzte Aktualisierung', 'Last update')}: {index.last_change.changed_count || 0} {t('geändert', 'changed')}, {index.last_change.removed_count || 0} {t('entfernt', 'removed')}, {index.last_change.unchanged || 0} {t('unverändert', 'unchanged')}.</p>}
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => { await request(base + '/index', { force: true }); await refresh(); })}>{t('Index vollständig neu lesen', 'Re-read the full index')}</button><button className="button primary" disabled={busy} onClick={() => void action(runAnalysis)}>{t('Vollständigen Analyseverlauf erzeugen', 'Generate full analysis run')}</button></div>
      {analysis && <div className="analysis-report"><p><strong>{t('Abdeckung:', 'Coverage:')}</strong> {analysis.coverage.files_included} / {analysis.coverage.files_total} {t('Dateien', 'files')} · {analysis.coverage.percent}% {t('des lesbaren Quelltexts', 'of readable source')} · {t('Budget', 'Budget')} {analysis.coverage.budget_chars.toLocaleString(locale)} {t('Zeichen', 'characters')}.</p><progress max="100" value={analysis.coverage.percent} /><details><summary>{t(`Teilschritte und Abdeckung (${analysis.chunks.length} Textblöcke)`, `Chunks and coverage (${analysis.chunks.length} text blocks)`)}</summary>{analysis.batches.map(row => <p key={row.file}>{row.included ? '✓' : '○'} {row.file} · {row.parts} {t('Teil(e)', 'part(s)')}</p>)}</details></div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>{t('Aufgaben-Graph', 'Task graph')}</h2><span className="stage-badge">{graph.summary.tasks || 0} {t('Aufgaben', 'tasks')}</span></div>
      <p>{t('Blockierungen, Abhängigkeiten und gemeinsame Dateien. Prioritäten steuern die Reihenfolge; parallele gemeinsame Dateien benötigen eine ausdrückliche Freigabe.', 'Blockers, dependencies and shared files. Priorities control the order; parallel shared files require explicit approval.')}</p>
      <p className="field-hint">{t('Kritischer Pfad', 'Critical path')}: {graph.critical_path.join(' → ') || '—'} · {t('Bereit', 'Ready')}: {graph.ready.join(', ') || t('keine', 'none')} · {t('Blockiert', 'Blocked')}: {graph.summary.blocked || 0}</p>
      {!graph.nodes.length ? <p>{t('Noch kein Aufgabenplan geladen.', 'No task plan loaded yet.')}</p> : <div className="graph-list">{graph.nodes.map(node => <div className={'graph-node' + (node.blocked ? ' blocked' : '')} key={node.id}><div><strong>{node.id}</strong> · {node.title}<small>{node.depends_on.length ? ' ← ' + node.depends_on.join(', ') : t(' keine Voraussetzungen', ' no dependencies')} · {node.status}</small>{!!node.question && <small className="field-error"> {t('Rückfrage:', 'Question:')} {node.question}</small>}{node.approval_missing.length > 0 && <small className="field-error"> {t('Freigabe fehlt:', 'Approval missing:')} {node.approval_missing.join(', ')}</small>}</div><label className="priority-field">{t('Priorität', 'Priority')}<select value={node.priority} disabled={busy} onChange={event => void action(async () => graphUpdate({ priorities: { ...priorities, [node.id]: Number(event.target.value) } }))}>{[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map(value => <option value={value} key={value}>{value}</option>)}</select></label></div>)}</div>}
      {!!graph.conflicts.length && <div className="graph-conflicts"><h3>{t('Gemeinsame Dateien', 'Shared files')}</h3>{graph.conflicts.map(row => <div className="graph-conflict" key={row.file}><div><strong>{row.file}</strong><small>{row.tasks.join(', ')} · {row.blocking ? t('parallele Nutzung', 'parallel use') : t('durch Reihenfolge abgesichert', 'protected by ordering')}</small></div>{row.blocking && <button className="button secondary" disabled={busy} onClick={() => void action(async () => graphUpdate({ approve_file: row.file, approved: !row.approved, note: t('Im Aufgaben-Graph freigegeben', 'Approved in the task graph') }))}>{row.approved ? t('Freigabe zurückziehen', 'Withdraw approval') : t('Ausdrücklich freigeben', 'Approve explicitly')}</button>}</div>)}</div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>{t('Empirische Messreihe', 'Empirical benchmark')}</h2><span className="stage-badge">{benchmark?.cached ? t('Cache', 'Cache') : benchmark?.status || t('neu', 'new')}</span></div>
      <p>{t('Mehrere Kontextgrößen, Wiederholungen, Tokens/s, VRAM-Spitzen und Qualitätsstreuung. Die Empfehlung gilt nur für diese Hardware, Quantisierung und Aufgabe.', 'Multiple context sizes, repetitions, tokens/s, VRAM peaks and quality spread. The recommendation applies only to this hardware, quantization and task.')}</p>
      <div className="settings-grid">
        <label className="field">{t('Kontextgrößen (Komma)', 'Context sizes (comma)')}<input value={benchContexts} disabled={busy} onChange={event => setBenchContexts(event.target.value)} /></label>
        <label className="field">{t('Wiederholungen', 'Repetitions')}<input type="number" min="1" max="5" value={benchRepeats} disabled={busy} onChange={event => setBenchRepeats(Number(event.target.value))} /></label>
        <label className="field">{t('Aufgabentyp', 'Task type')}<select value={benchKind} disabled={busy} onChange={event => setBenchKind(event.target.value)}><option value="coding">{t('Codierung', 'Coding')}</option><option value="presentation">{t('Präsentation', 'Presentation')}</option><option value="context">{t('Langkontext', 'Long context')}</option><option value="general">{t('Allgemein', 'General')}</option></select></label>
        <label className="field">{t('Modell', 'Model')}<input list="benchmark-models" value={benchModel} disabled={busy} onChange={event => setBenchModel(event.target.value)} /><datalist id="benchmark-models">{models.map(model => <option value={model.id} key={model.id} />)}</datalist></label>
        <label className="field">{t('Auswertungsmodell (optional)', 'Evaluation model (optional)')}<input value={benchJudge} disabled={busy} onChange={event => setBenchJudge(event.target.value)} placeholder="z. B. qwen3-8b" /></label>
        <label className="field">{t('Arbeitsprobe', 'Work sample')}<input value={benchGoal} disabled={busy} onChange={event => setBenchGoal(event.target.value)} placeholder={t('Aufgabenbeschreibung', 'Task description')} /></label>
      </div>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => setModels(await request<{ id: string; type: string }[]>(base + '/models', {})))}>{t('Installierte Modelle laden', 'Load installed models')}</button><label className="check-label"><input type="checkbox" checked={benchForce} disabled={busy} onChange={event => setBenchForce(event.target.checked)} />{t('Cache ignorieren', 'Ignore cache')}</label><button className="button primary" disabled={busy || !benchModel.trim()} onClick={() => void action(async () => { await request(base + '/benchmark', { contexts: benchContexts.split(',').map(value => Number(value.trim())).filter(value => Number.isFinite(value)), repeats: benchRepeats, kind: benchKind, model: benchModel, judge: benchJudge, goal: benchGoal, force: benchForce }); await refresh(); })}>{t('Messreihe starten', 'Start benchmark')}</button></div>
      {benchmark?.recommendation && <div className="benchmark-result"><h3>{t('Gemessene Empfehlung', 'Measured recommendation')}</h3><p><strong>{benchmark.recommendation.model}</strong> · {benchmark.recommendation.context_tokens} {t('Tokens', 'tokens')} · {t('Qualität', 'Quality')} {benchmark.recommendation.quality_mean} ± {benchmark.recommendation.quality_stdev} · {benchmark.recommendation.tokens_per_second ?? '—'} {t('Tokens/s', 'tokens/s')} · VRAM {bytes(benchmark.recommendation.vram_peak_bytes)}</p><p className="field-hint">{benchmark.recommendation.reason} {t('Keine Garantie eines global besten Modells.', 'No guarantee of a globally best model.')}</p></div>}
      {benchmark?.error && <p className="field-error">{benchmark.error}</p>}
      {!!benchmark?.groups?.length && <details open><summary>{t('Messgruppen und Streuung', 'Measurement groups and spread')}</summary><div className="table-wrap"><table><thead><tr><th>{t('Modell', 'Model')}</th><th>{t('Kontext', 'Context')}</th><th>{t('Proben', 'Samples')}</th><th>{t('Qualität', 'Quality')}</th><th>{t('Streuung', 'Spread')}</th><th>{t('Tokens/s', 'Tokens/s')}</th><th>{t('VRAM-Spitze', 'VRAM peak')}</th></tr></thead><tbody>{benchmark.groups.map((row, index) => <tr key={index}><td>{row.model}</td><td>{row.context_tokens}</td><td>{row.samples}</td><td>{row.quality_mean}</td><td>± {row.quality_stdev}</td><td>{row.tokens_per_second ?? '—'}</td><td>{bytes(row.vram_peak_bytes)}</td></tr>)}</tbody></table></div></details>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>{t('Anwendungsabnahme', 'Application acceptance')}</h2><span className="stage-badge">{report ? (report.passed ? t('bestanden', 'passed') : t('nicht bestanden', 'failed')) : t('noch keine', 'none yet')}</span></div>
      <p>{t('Deklarierte CLI-, HTTP- und Headless-Browser-Szenarien prüfen das gebaute Werkzeug als Anwendung. Teständerungen werden getrennt vom Planreview ausgewiesen.', 'Declared CLI, HTTP and headless browser scenarios verify the built tool as an application. Test changes are reported separately from the plan review.')}</p>
      {!snapshot.state?.plan.acceptance_scenarios?.length && <p className="field-hint">{t('Im Plan ist kein Feld ', 'The plan does not declare an ')}<code>acceptance_scenarios</code>{t(' deklariert. Ohne Deklaration wird nur ein informatives CLI-', ' field. Without a declaration, only an informational CLI ')}<code>--help</code>{t('-Szenario versucht; es blockiert die Fertigstellung nicht.', ' scenario is attempted; it does not block completion.')}</p>}
      <div className="inline-actions"><button className="button primary" disabled={busy || !snapshot.state} onClick={() => void action(async () => { await request(base + '/scenarios/run', {}); await refresh(); })}>{t('Anwendungsabnahme jetzt ausführen', 'Run application acceptance now')}</button></div>
      {report && <div className="scenario-report"><p><strong>{report.scenarios.filter(row => row.passed && !row.informational).length} {t('bestanden', 'passed')}</strong> · {report.scenarios.filter(row => !row.passed).length} {t('nicht bestanden', 'failed')} · {t('Teständerungen:', 'Test changes:')} {report.test_changes.added.length + report.test_changes.changed.length + report.test_changes.removed.length}</p>{report.scenarios.map(row => <details key={row.id} className={row.passed ? 'scenario passed' : 'scenario failed'}><summary>{row.passed ? '✓' : '✗'} {row.id} · {row.kind}{row.informational ? t(' · informativ', ' · informational') : ''}</summary>{row.error && <p className="field-error">{row.error}</p>}{row.url && <p>{row.url}</p>}{row.argv && <p className="mono">{row.argv.join(' ')}</p>}{row.output && <pre>{row.output.slice(-5000)}</pre>}</details>)}{report.review_required && <div className="review-box"><p><strong>{t('Teständerungen gesondert prüfen', 'Review test changes separately')}</strong></p>{!!report.test_changes.added.length && <p>{t('Neu:', 'Added:')} {report.test_changes.added.join(', ')}</p>}{!!report.test_changes.changed.length && <p>{t('Geändert:', 'Changed:')} {report.test_changes.changed.join(', ')}</p>}{!!report.test_changes.removed.length && <p>{t('Entfernt:', 'Removed:')} {report.test_changes.removed.join(', ')}</p>}{report.test_changes.diffs.map(row => <details key={row.path}><summary>Diff {row.path}</summary><pre>{row.diff}</pre></details>)}{report.reviewed_at ? <p className="notice" role="status">✓ {t('Geprüft am', 'Reviewed on')} {stamp(report.reviewed_at, locale)}. {report.review_note}</p> : <><label className="field">{t('Prüfnotiz', 'Review note')}<textarea value={reviewNote} onChange={event => setReviewNote(event.target.value)} /></label><button className="button danger" disabled={busy} onClick={() => void action(async () => { await request(base + '/scenarios/review', { note: reviewNote }); await refresh(); })}>{t('Teständerungen prüfen und bestätigen', 'Review and confirm test changes')}</button></>}</div>}</div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>{t('Recherche mit Textbelegen', 'Research with text evidence')}</h2><span className="stage-badge">{research?.cached ? t('Cache', 'Cache') : 'live'}</span></div>
      <p>{t('Domainfilter, geöffnete Quellen mit Textbelegen, siebentägiger Cache und Zuordnung zu Aufgabe oder Fehler. Suchergebnis-Snippets allein gelten nicht als Nachweis.', 'Domain filter, opened sources with text evidence, a seven-day cache and assignment to a task or error. Search result snippets alone do not count as evidence.')}</p>
      <div className="settings-grid"><label className="field">{t('Suchbegriff', 'Search term')}<input value={researchQuery} disabled={busy} onChange={event => setResearchQuery(event.target.value)} placeholder={t('z. B. pytest fixture scope', 'e.g. pytest fixture scope')} /></label><label className="field">{t('Zuordnung Aufgabe/Fehler', 'Assigned task/error')}<input value={researchTask} disabled={busy} onChange={event => setResearchTask(event.target.value)} /></label></div>
      <p className="field-hint">{t('Domainfilter aus den Einstellungen:', 'Domain filter from settings:')} {snapshot.settings.research_domains || t('alle öffentlichen Quellen', 'all public sources')}.</p>
      <div className="inline-actions"><label className="check-label"><input type="checkbox" checked={researchForce} disabled={busy} onChange={event => setResearchForce(event.target.checked)} />{t('Cache ignorieren', 'Ignore cache')}</label><button className="button primary" disabled={busy || !researchQuery.trim()} onClick={() => void action(async () => { setResearch(await request<ResearchEntry>(base + '/research', { query: researchQuery, task_id: researchTask, force: researchForce })); await refresh(); })}>{t('Recherche starten', 'Start research')}</button></div>
      {research?.error && <p className="field-error">{research.error}</p>}
      {!!research?.results.length && <div className="research-results">{research.results.map(row => <details key={row.url} open><summary>{row.title} · {row.host}</summary><p><a href={row.url} target="_blank" rel="noreferrer">{row.url}</a></p><p>{row.snippet}</p>{(row.evidence || []).map((item, index) => <blockquote key={index}>{item.text}</blockquote>)}</details>)}</div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>{t('Umgebung, Presets und Betrieb', 'Environment, presets and operations')}</h2><span className="stage-badge">{environment?.presets?.length || 0} Presets</span></div>
      <p>{t('Versionsgebundene Controller-/Aider-Pakete, Docker-Digests und portable Presets machen Läufe nachvollziehbar. Diagnosejournale werden rotiert; vor Planänderungen entstehen Sicherungen.', 'Version-pinned controller/Aider packages, Docker digests and portable presets make runs traceable. Diagnostic journals are rotated; backups are created before plan changes.')}</p>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => { setLock(await request<Environment>(base + '/environment')); })}>{t('Umgebungssperre anzeigen', 'Show environment lock')}</button><button className="button secondary" disabled={busy} onClick={() => void action(async () => { await request(base + '/operations/rotate', {}); await refresh(); })}>{t('Diagnosejournale rotieren', 'Rotate diagnostic journals')}</button><a className="button secondary" href={base + '/export'}>{t('Projekt als ZIP exportieren', 'Export project as ZIP')}</a></div>
      {lock && <div className="environment-report"><p>{t('Controller-Python', 'Controller Python')} {lock.controller.python} · Aider {lock.aider.installed_version || t('nicht erkannt', 'not detected')} · {t('reproduzierbar:', 'reproducible:')} {lock.reproducible ? t('ja', 'yes') : t('teilweise', 'partly')} · Docker: {lock.docker.available ? (lock.docker.image_id ? lock.docker.image_id.slice(0, 19) : lock.docker.note || t('verfügbar', 'available')) : t('nicht verfügbar', 'not available')}</p>{!!lock.docker.repo_digests.length && <p className="mono">{lock.docker.repo_digests.join(' · ')}</p>}<details><summary>{t('Paket-Lockfiles', 'Package lockfiles')}</summary><p><strong>{t('Controller:', 'Controller:')}</strong> {lock.controller.requirements.map(row => `${row.name}==${row.version}`).join(', ') || '—'}</p><p><strong>Aider:</strong> {lock.aider.pinned.map(row => `${row.name}==${row.version}`).join(', ') || '—'}</p></details></div>}
      <div className="settings-grid"><label className="field">{t('Preset-Name', 'Preset name')}<input value={presetName} disabled={busy} onChange={event => setPresetName(event.target.value)} /></label><label className="field">{t('Vorhandenes Preset', 'Existing preset')}<input list="preset-files" value={presetFile} disabled={busy} onChange={event => setPresetFile(event.target.value)} /><datalist id="preset-files">{environment?.presets?.map(preset => <option value={preset.file} key={preset.file}>{preset.name}</option>)}</datalist></label><label className="field">{t('Projekt-ZIP importieren', 'Import project ZIP')}<input value={importPath} disabled={busy} onChange={event => setImportPath(event.target.value)} placeholder="C:\...\toolforge-projekt.zip" /></label></div>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => { await request(base + '/presets/export', { name: presetName }); await refresh(); })}>{t('Preset exportieren', 'Export preset')}</button><button className="button secondary" disabled={busy || !presetFile} onClick={() => void action(async () => { await request(base + '/presets/import', { file: presetFile, apply: true }); await refresh(); })}>{t('Preset importieren & anwenden', 'Import & apply preset')}</button><label className="check-label"><input type="checkbox" checked={importOverwrite} disabled={busy} onChange={event => setImportOverwrite(event.target.checked)} />{t('Import überschreibt vorhandene Dateien', 'Import overwrites existing files')}</label><button className="button danger" disabled={busy || !importPath.trim()} onClick={() => void action(async () => { if (!window.confirm(t('Projektarchiv in diesen Arbeitsordner importieren?', 'Import project archive into this working folder?'))) return; await request(base + '/import', { path: importPath, overwrite: importOverwrite }); await refresh(); })}>{t('ZIP importieren', 'Import ZIP')}</button></div>
      <div className="operations-row"><p><strong>Tray:</strong> {operations.tray?.available ? t('verfügbar', 'available') : t('optional nicht installiert', 'optionally not installed')} · {operations.tray?.note}</p><p><strong>{t('Installer:', 'Installer:')}</strong> {operations.installer?.signed ? t('signiert', 'signed') : t('Signatur vorbereitet', 'signature prepared')} · {operations.installer?.note}</p></div>
      {!!operations.plan_backups?.length && <details><summary>{t(`Plan-Sicherungen (${operations.plan_backups.length})`, `Plan backups (${operations.plan_backups.length})`)}</summary>{operations.plan_backups.map(backup => <div className="backup-row" key={backup.file}><span><strong>V{backup.version}</strong> · {backup.reason} · {stamp(backup.at, locale)} · {backup.tasks} {t('Aufgaben', 'tasks')}</span><button className="text-button" disabled={busy} onClick={() => void action(async () => { if (!window.confirm(t(`Planstand V${backup.version} wiederherstellen?`, `Restore plan version V${backup.version}?`))) return; await request(base + '/backups/restore', { file: backup.file }); await refresh(); })}>{t('Wiederherstellen', 'Restore')}</button></div>)}</details>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>{t('Sandbox-Komfort', 'Sandbox convenience')}</h2><span className="stage-badge">{sandboxBadge}</span></div>
      <p>{t('Projekt-Image, Netzwerke, Ressourcen und gezielte Container-Pakete. Ports werden ausschließlich auf Loopback freigegeben.', 'Project image, networks, resources and targeted container packages. Ports are exposed on loopback only.')}</p>
      <p className="field-hint">{t('Der Build startet nur, wenn Docker-CLI ', 'The build starts only when Docker CLI ')}<em>{t('und', 'and')}</em>{t(' Linux-Daemon erreichbar sind. Fehler erscheinen nach Abschluss; der Status wird während des Builds automatisch aktualisiert.', ' Linux daemon are reachable. Errors appear after completion; the status refreshes automatically during the build.')}</p>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(loadSandbox)}>{t('Status aktualisieren', 'Refresh status')}</button><button className="button primary" disabled={busy || !sandbox?.docker_available} onClick={() => void action(async () => { await sandboxAction(base + '/sandbox/build'); })}>{t('Projekt-Image bauen', 'Build project image')}</button><button className="button danger" disabled={busy || !sandbox?.docker_available} onClick={() => void action(async () => { if (!window.confirm(t('Projekt-Image entfernen? Der nächste Lauf baut es erneut.', 'Remove the project image? The next run will rebuild it.'))) return; await sandboxAction(base + '/sandbox/image/remove'); })}>{t('Image entfernen', 'Remove image')}</button></div>
      {sandbox && <div className="sandbox-status"><p><strong>{sandbox.tag}</strong> · {sandbox.image ? `${sandbox.image.id.slice(0, 19)} · ${bytes(sandbox.image.size)}` : t('noch nicht gebaut', 'not built yet')} · {t('Netzwerk:', 'Network:')} {sandbox.network || t('keines', 'none')}</p>{sandbox.daemon_version && <p className="field-hint">{t('Docker-Daemon:', 'Docker daemon:')} {sandbox.daemon_version}</p>}{sandbox.daemon_error && <p className="field-error">{sandbox.daemon_error}</p>}{sandbox.error && <p className="field-error">{sandbox.error}</p>}{!!sandbox.networks.length && <p className="field-hint">{t('Vorhandene ToolForge-Netzwerke:', 'Existing ToolForge networks:')} {sandbox.networks.map(row => row.name).join(', ')}</p>}</div>}
      <div className="inline-actions"><button className="button secondary" disabled={busy || !snapshot.settings.sandbox_network || !sandbox?.docker_available} onClick={() => void action(async () => { await sandboxAction(base + '/sandbox/network', { action: 'ensure', name: snapshot.settings.sandbox_network }); })}>{t('Netzwerk anlegen', 'Create network')}</button><button className="button secondary" disabled={busy || !snapshot.settings.sandbox_network || !sandbox?.docker_available} onClick={() => void action(async () => { await sandboxAction(base + '/sandbox/network', { action: 'remove', name: snapshot.settings.sandbox_network }); })}>{t('Netzwerk entfernen', 'Remove network')}</button></div>
      <div className="settings-grid"><label className="field">{t('Paketmanager', 'Package manager')}<select value={packageManager} disabled={busy} onChange={event => setPackageManager(event.target.value)}><option value="pip">pip</option><option value="npm">npm</option></select></label><label className="field">{t('Paketname', 'Package name')}<input value={packageName} disabled={busy} onChange={event => setPackageName(event.target.value)} placeholder={t('z. B. pillow', 'e.g. pillow')} /></label><label className="field">{t('Version (optional)', 'Version (optional)')}<input value={packageVersion} disabled={busy} onChange={event => setPackageVersion(event.target.value)} /></label></div>
      <div className="inline-actions"><button className="button primary" disabled={busy || !packageName.trim() || !sandbox?.docker_available} onClick={() => void action(async () => { await sandboxAction(base + '/sandbox/package', { manager: packageManager, name: packageName, version: packageVersion }); })}>{t('Im abgeleiteten Container-Image installieren', 'Install in the derived container image')}</button></div>
      <p className="field-hint">{t('Ressourcenregler stehen unter Einstellungen:', 'Resource controls are under Settings:')} {t('Speicher', 'Memory')} {snapshot.settings.sandbox_memory}, CPUs {snapshot.settings.sandbox_cpus}, {t('Prozesse', 'processes')} {snapshot.settings.sandbox_pids}, {t('Ports', 'ports')} {snapshot.settings.sandbox_ports || t('keine', 'none')}.</p>
    </section>
  </div>;
}
