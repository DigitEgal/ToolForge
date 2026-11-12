import { useEffect, useState } from 'react';
import type { Snapshot } from './pilotTypes';

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
type SandboxState = { docker_available: boolean; tag: string; image: { tag: string; id: string; repo_digests: string[]; created: string; size: number | null } | null; network: string | null; networks: { name: string; driver: string; scope: string }[]; error?: string };

function bytes(value: number | null | undefined) {
  if (!value) return '—';
  if (value > 1024 ** 3) return (value / 1024 ** 3).toFixed(1) + ' GB';
  if (value > 1024 ** 2) return (value / 1024 ** 2).toFixed(0) + ' MB';
  return (value / 1024).toFixed(0) + ' KB';
}
function stamp(value: number | null | undefined) {
  return value ? new Date(value * 1000).toLocaleString('de-DE') : '—';
}

export default function AdvancedPanel({ base, snapshot, busy, request, action, refresh }: { base: string; snapshot: Snapshot; busy: boolean; request: RequestFn; action: (fn: () => Promise<void>) => Promise<void>; refresh: () => Promise<void> }) {
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

  return <div className="advanced-panel">
    <section className="panel">
      <div className="panel-title"><h2>Vollständige Projektanalyse</h2><span className="stage-badge">{index.indexed ? 'Index aktuell' : 'Noch kein Index'}</span></div>
      <p>Dateien werden inkrementell über Signatur neu gelesen. Der Index enthält Symbole, Importe und Abhängigkeiten aller Dateien; große Projekte werden in belegten Teilabschnitten gelesen.</p>
      {index.summary && <div className="metrics compact"><article><span>Dateien</span><strong>{index.summary.files || 0}</strong></article><article><span>Symbole</span><strong>{index.summary.symbols || 0}</strong></article><article><span>Abhängigkeiten</span><strong>{index.summary.dependencies || 0}</strong></article><article><span>Lesefehler</span><strong>{index.summary.errors || 0}</strong></article></div>}
      {index.last_change && <p className="field-hint">Letzte Aktualisierung: {index.last_change.changed_count || 0} geändert, {index.last_change.removed_count || 0} entfernt, {index.last_change.unchanged || 0} unverändert.</p>}
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => { await request(base + '/index', { force: true }); await refresh(); })}>Index vollständig neu lesen</button><button className="button primary" disabled={busy} onClick={() => void action(runAnalysis)}>Vollständigen Analyseverlauf erzeugen</button></div>
      {analysis && <div className="analysis-report"><p><strong>Abdeckung:</strong> {analysis.coverage.files_included} / {analysis.coverage.files_total} Dateien · {analysis.coverage.percent}% des lesbaren Quelltexts · Budget {analysis.coverage.budget_chars.toLocaleString('de')} Zeichen.</p><progress max="100" value={analysis.coverage.percent}/><details><summary>Teilschritte und Abdeckung ({analysis.chunks.length} Textblöcke)</summary>{analysis.batches.map(row => <p key={row.file}>{row.included ? '✓' : '○'} {row.file} · {row.parts} Teil(e)</p>)}</details></div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>Aufgaben-Graph</h2><span className="stage-badge">{graph.summary.tasks || 0} Aufgaben</span></div>
      <p>Blockierungen, Abhängigkeiten und gemeinsame Dateien. Prioritäten steuern die Reihenfolge; parallele gemeinsame Dateien benötigen eine ausdrückliche Freigabe.</p>
      <p className="field-hint">Kritischer Pfad: {graph.critical_path.join(' → ') || '—'} · Bereit: {graph.ready.join(', ') || 'keine'} · Blockiert: {graph.summary.blocked || 0}</p>
      {!graph.nodes.length ? <p>Noch kein Aufgabenplan geladen.</p> : <div className="graph-list">{graph.nodes.map(node => <div className={'graph-node' + (node.blocked ? ' blocked' : '')} key={node.id}><div><strong>{node.id}</strong> · {node.title}<small>{node.depends_on.length ? ' ← ' + node.depends_on.join(', ') : ' keine Voraussetzungen'} · {node.status}</small>{!!node.question && <small className="field-error"> Rückfrage: {node.question}</small>}{node.approval_missing.length > 0 && <small className="field-error"> Freigabe fehlt: {node.approval_missing.join(', ')}</small>}</div><label className="priority-field">Priorität<select value={node.priority} disabled={busy} onChange={event => void action(async () => graphUpdate({ priorities: { ...priorities, [node.id]: Number(event.target.value) } }))}>{[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map(value => <option value={value} key={value}>{value}</option>)}</select></label></div>)}</div>}
      {!!graph.conflicts.length && <div className="graph-conflicts"><h3>Gemeinsame Dateien</h3>{graph.conflicts.map(row => <div className="graph-conflict" key={row.file}><div><strong>{row.file}</strong><small>{row.tasks.join(', ')} · {row.blocking ? 'parallele Nutzung' : 'durch Reihenfolge abgesichert'}</small></div>{row.blocking && <button className="button secondary" disabled={busy} onClick={() => void action(async () => graphUpdate({ approve_file: row.file, approved: !row.approved, note: 'Im Aufgaben-Graph freigegeben' }))}>{row.approved ? 'Freigabe zurückziehen' : 'Ausdrücklich freigeben'}</button>}</div>)}</div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>Empirische Messreihe</h2><span className="stage-badge">{benchmark?.cached ? 'Cache' : benchmark?.status || 'neu'}</span></div>
      <p>Mehrere Kontextgrößen, Wiederholungen, Tokens/s, VRAM-Spitzen und Qualitätsstreuung. Die Empfehlung gilt nur für diese Hardware, Quantisierung und Aufgabe.</p>
      <div className="settings-grid"><label className="field">Kontextgrößen (Komma)<input value={benchContexts} disabled={busy} onChange={event => setBenchContexts(event.target.value)}/></label><label className="field">Wiederholungen<input type="number" min="1" max="5" value={benchRepeats} disabled={busy} onChange={event => setBenchRepeats(Number(event.target.value))}/></label><label className="field">Aufgabentyp<select value={benchKind} disabled={busy} onChange={event => setBenchKind(event.target.value)}><option value="coding">Codierung</option><option value="presentation">Präsentation</option><option value="context">Langkontext</option><option value="general">Allgemein</option></select></label><label className="field">Modell<input list="benchmark-models" value={benchModel} disabled={busy} onChange={event => setBenchModel(event.target.value)}/><datalist id="benchmark-models">{models.map(model => <option value={model.id} key={model.id}/>)}</datalist></label><label className="field">Auswertungsmodell (optional)<input value={benchJudge} disabled={busy} onChange={event => setBenchJudge(event.target.value)} placeholder="z. B. qwen3-8b"/></label><label className="field">Arbeitsprobe<input value={benchGoal} disabled={busy} onChange={event => setBenchGoal(event.target.value)} placeholder="Aufgabenbeschreibung"/></label></div>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => setModels(await request<{ id: string; type: string }[]>(base + '/models', {})))}>Installierte Modelle laden</button><label className="check-label"><input type="checkbox" checked={benchForce} disabled={busy} onChange={event => setBenchForce(event.target.checked)}/>Cache ignorieren</label><button className="button primary" disabled={busy || !benchModel.trim()} onClick={() => void action(async () => { await request(base + '/benchmark', { contexts: benchContexts.split(',').map(value => Number(value.trim())).filter(value => Number.isFinite(value)), repeats: benchRepeats, kind: benchKind, model: benchModel, judge: benchJudge, goal: benchGoal, force: benchForce }); await refresh(); })}>Messreihe starten</button></div>
      {benchmark?.recommendation && <div className="benchmark-result"><h3>Gemessene Empfehlung</h3><p><strong>{benchmark.recommendation.model}</strong> · {benchmark.recommendation.context_tokens} Tokens · Qualität {benchmark.recommendation.quality_mean} ± {benchmark.recommendation.quality_stdev} · {benchmark.recommendation.tokens_per_second ?? '—'} Tokens/s · VRAM {bytes(benchmark.recommendation.vram_peak_bytes)}</p><p className="field-hint">{benchmark.recommendation.reason} Keine Garantie eines global besten Modells.</p></div>}
      {benchmark?.error && <p className="field-error">{benchmark.error}</p>}
      {!!benchmark?.groups?.length && <details open><summary>Messgruppen und Streuung</summary><div className="table-wrap"><table><thead><tr><th>Modell</th><th>Kontext</th><th>Proben</th><th>Qualität</th><th>Streuung</th><th>Tokens/s</th><th>VRAM-Spitze</th></tr></thead><tbody>{benchmark.groups.map((row, index) => <tr key={index}><td>{row.model}</td><td>{row.context_tokens}</td><td>{row.samples}</td><td>{row.quality_mean}</td><td>± {row.quality_stdev}</td><td>{row.tokens_per_second ?? '—'}</td><td>{bytes(row.vram_peak_bytes)}</td></tr>)}</tbody></table></div></details>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>Anwendungsabnahme</h2><span className="stage-badge">{report ? (report.passed ? 'bestanden' : 'nicht bestanden') : 'noch keine'}</span></div>
      <p>Deklarierte CLI-, HTTP- und Headless-Browser-Szenarien prüfen das gebaute Werkzeug als Anwendung. Teständerungen werden getrennt vom Planreview ausgewiesen.</p>
      {!snapshot.state?.plan.acceptance_scenarios?.length && <p className="field-hint">Im Plan ist kein Feld <code>acceptance_scenarios</code> deklariert. Ohne Deklaration wird nur ein informatives CLI-<code>--help</code>-Szenario versucht; es blockiert die Fertigstellung nicht.</p>}
      <div className="inline-actions"><button className="button primary" disabled={busy || !snapshot.state} onClick={() => void action(async () => { await request(base + '/scenarios/run', {}); await refresh(); })}>Anwendungsabnahme jetzt ausführen</button></div>
      {report && <div className="scenario-report"><p><strong>{report.scenarios.filter(row => row.passed && !row.informational).length} bestanden</strong> · {report.scenarios.filter(row => !row.passed).length} nicht bestanden · Teständerungen: {report.test_changes.added.length + report.test_changes.changed.length + report.test_changes.removed.length}</p>{report.scenarios.map(row => <details key={row.id} className={row.passed ? 'scenario passed' : 'scenario failed'}><summary>{row.passed ? '✓' : '✗'} {row.id} · {row.kind}{row.informational ? ' · informativ' : ''}</summary>{row.error && <p className="field-error">{row.error}</p>}{row.url && <p>{row.url}</p>}{row.argv && <p className="mono">{row.argv.join(' ')}</p>}{row.output && <pre>{row.output.slice(-5000)}</pre>}</details>)}{report.review_required && <div className="review-box"><p><strong>Teständerungen gesondert prüfen</strong></p>{!!report.test_changes.added.length && <p>Neu: {report.test_changes.added.join(', ')}</p>}{!!report.test_changes.changed.length && <p>Geändert: {report.test_changes.changed.join(', ')}</p>}{!!report.test_changes.removed.length && <p>Entfernt: {report.test_changes.removed.join(', ')}</p>}{report.test_changes.diffs.map(row => <details key={row.path}><summary>Diff {row.path}</summary><pre>{row.diff}</pre></details>)}{report.reviewed_at ? <p className="notice" role="status">✓ Geprüft am {stamp(report.reviewed_at)}. {report.review_note}</p> : <><label className="field">Prüfnotiz<textarea value={reviewNote} onChange={event => setReviewNote(event.target.value)}/></label><button className="button danger" disabled={busy} onClick={() => void action(async () => { await request(base + '/scenarios/review', { note: reviewNote }); await refresh(); })}>Teständerungen prüfen und bestätigen</button></>}</div>}</div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>Recherche mit Textbelegen</h2><span className="stage-badge">{research?.cached ? 'Cache' : 'live'}</span></div>
      <p>Domainfilter, geöffnete Quellen mit Textbelegen, siebentägiger Cache und Zuordnung zu Aufgabe oder Fehler. Suchergebnis-Snippets allein gelten nicht als Nachweis.</p>
      <div className="settings-grid"><label className="field">Suchbegriff<input value={researchQuery} disabled={busy} onChange={event => setResearchQuery(event.target.value)} placeholder="z. B. pytest fixture scope"/></label><label className="field">Zuordnung Aufgabe/Fehler<input value={researchTask} disabled={busy} onChange={event => setResearchTask(event.target.value)}/></label></div>
      <p className="field-hint">Domainfilter aus den Einstellungen: {snapshot.settings.research_domains || 'alle öffentlichen Quellen'}.</p>
      <div className="inline-actions"><label className="check-label"><input type="checkbox" checked={researchForce} disabled={busy} onChange={event => setResearchForce(event.target.checked)}/>Cache ignorieren</label><button className="button primary" disabled={busy || !researchQuery.trim()} onClick={() => void action(async () => { setResearch(await request<ResearchEntry>(base + '/research', { query: researchQuery, task_id: researchTask, force: researchForce })); await refresh(); })}>Recherche starten</button></div>
      {research?.error && <p className="field-error">{research.error}</p>}
      {!!research?.results.length && <div className="research-results">{research.results.map(row => <details key={row.url} open><summary>{row.title} · {row.host}</summary><p><a href={row.url} target="_blank" rel="noreferrer">{row.url}</a></p><p>{row.snippet}</p>{(row.evidence || []).map((item, index) => <blockquote key={index}>{item.text}</blockquote>)}</details>)}</div>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>Umgebung, Presets und Betrieb</h2><span className="stage-badge">{environment?.presets?.length || 0} Presets</span></div>
      <p>Versionsgebundene Controller-/Aider-Pakete, Docker-Digests und portable Presets machen Läufe nachvollziehbar. Diagnosejournale werden rotiert; vor Planänderungen entstehen Sicherungen.</p>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => { setLock(await request<Environment>(base + '/environment')); })}>Umgebungssperre anzeigen</button><button className="button secondary" disabled={busy} onClick={() => void action(async () => { await request(base + '/operations/rotate', {}); await refresh(); })}>Diagnosejournale rotieren</button><a className="button secondary" href={base + '/export'}>Projekt als ZIP exportieren</a></div>
      {lock && <div className="environment-report"><p>Controller-Python {lock.controller.python} · Aider {lock.aider.installed_version || 'nicht erkannt'} · reproduzierbar: {lock.reproducible ? 'ja' : 'teilweise'} · Docker: {lock.docker.available ? (lock.docker.image_id ? lock.docker.image_id.slice(0, 19) : lock.docker.note || 'verfügbar') : 'nicht verfügbar'}</p>{!!lock.docker.repo_digests.length && <p className="mono">{lock.docker.repo_digests.join(' · ')}</p>}<details><summary>Paket-Lockfiles</summary><p><strong>Controller:</strong> {lock.controller.requirements.map(row => `${row.name}==${row.version}`).join(', ') || '—'}</p><p><strong>Aider:</strong> {lock.aider.pinned.map(row => `${row.name}==${row.version}`).join(', ') || '—'}</p></details></div>}
      <div className="settings-grid"><label className="field">Preset-Name<input value={presetName} disabled={busy} onChange={event => setPresetName(event.target.value)}/></label><label className="field">Vorhandenes Preset<input list="preset-files" value={presetFile} disabled={busy} onChange={event => setPresetFile(event.target.value)}/><datalist id="preset-files">{environment?.presets?.map(preset => <option value={preset.file} key={preset.file}>{preset.name}</option>)}</datalist></label><label className="field">Projekt-ZIP importieren<input value={importPath} disabled={busy} onChange={event => setImportPath(event.target.value)} placeholder="C:\...\toolforge-projekt.zip"/></label></div>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(async () => { await request(base + '/presets/export', { name: presetName }); await refresh(); })}>Preset exportieren</button><button className="button secondary" disabled={busy || !presetFile} onClick={() => void action(async () => { await request(base + '/presets/import', { file: presetFile, apply: true }); await refresh(); })}>Preset importieren & anwenden</button><label className="check-label"><input type="checkbox" checked={importOverwrite} disabled={busy} onChange={event => setImportOverwrite(event.target.checked)}/>Import überschreibt vorhandene Dateien</label><button className="button danger" disabled={busy || !importPath.trim()} onClick={() => void action(async () => { if (!window.confirm('Projektarchiv in diesen Arbeitsordner importieren?')) return; await request(base + '/import', { path: importPath, overwrite: importOverwrite }); await refresh(); })}>ZIP importieren</button></div>
      <div className="operations-row"><p><strong>Tray:</strong> {operations.tray?.available ? 'verfügbar' : 'optional nicht installiert'} · {operations.tray?.note}</p><p><strong>Installer:</strong> {operations.installer?.signed ? 'signiert' : 'Signatur vorbereitet'} · {operations.installer?.note}</p></div>
      {!!operations.plan_backups?.length && <details><summary>Plan-Sicherungen ({operations.plan_backups.length})</summary>{operations.plan_backups.map(backup => <div className="backup-row" key={backup.file}><span><strong>V{backup.version}</strong> · {backup.reason} · {stamp(backup.at)} · {backup.tasks} Aufgaben</span><button className="text-button" disabled={busy} onClick={() => void action(async () => { if (!window.confirm(`Planstand V${backup.version} wiederherstellen?`)) return; await request(base + '/backups/restore', { file: backup.file }); await refresh(); })}>Wiederherstellen</button></div>)}</details>}
    </section>

    <section className="panel">
      <div className="panel-title"><h2>Sandbox-Komfort</h2><span className="stage-badge">{sandbox?.docker_available ? 'Docker bereit' : 'Docker fehlt'}</span></div>
      <p>Projekt-Image, Netzwerke, Ressourcen und gezielte Container-Pakete. Ports werden ausschließlich auf Loopback freigegeben.</p>
      <div className="inline-actions"><button className="button secondary" disabled={busy} onClick={() => void action(loadSandbox)}>Status aktualisieren</button><button className="button primary" disabled={busy} onClick={() => void action(async () => { await request(base + '/sandbox/build', {}); await loadSandbox(); })}>Projekt-Image bauen</button><button className="button danger" disabled={busy} onClick={() => void action(async () => { if (!window.confirm('Projekt-Image entfernen? Der nächste Lauf baut es erneut.')) return; await request(base + '/sandbox/image/remove', {}); await loadSandbox(); })}>Image entfernen</button></div>
      {sandbox && <div className="sandbox-status"><p><strong>{sandbox.tag}</strong> · {sandbox.image ? `${sandbox.image.id.slice(0, 19)} · ${bytes(sandbox.image.size)}` : 'noch nicht gebaut'} · Netzwerk: {sandbox.network || 'keines'}</p>{sandbox.error && <p className="field-error">{sandbox.error}</p>}{!!sandbox.networks.length && <p className="field-hint">Vorhandene ToolForge-Netzwerke: {sandbox.networks.map(row => row.name).join(', ')}</p>}</div>}
      <div className="inline-actions"><button className="button secondary" disabled={busy || !snapshot.settings.sandbox_network} onClick={() => void action(async () => { await request(base + '/sandbox/network', { action: 'ensure', name: snapshot.settings.sandbox_network }); await loadSandbox(); })}>Netzwerk anlegen</button><button className="button secondary" disabled={busy || !snapshot.settings.sandbox_network} onClick={() => void action(async () => { await request(base + '/sandbox/network', { action: 'remove', name: snapshot.settings.sandbox_network }); await loadSandbox(); })}>Netzwerk entfernen</button></div>
      <div className="settings-grid"><label className="field">Paketmanager<select value={packageManager} disabled={busy} onChange={event => setPackageManager(event.target.value)}><option value="pip">pip</option><option value="npm">npm</option></select></label><label className="field">Paketname<input value={packageName} disabled={busy} onChange={event => setPackageName(event.target.value)} placeholder="z. B. pillow"/></label><label className="field">Version (optional)<input value={packageVersion} disabled={busy} onChange={event => setPackageVersion(event.target.value)}/></label></div>
      <div className="inline-actions"><button className="button primary" disabled={busy || !packageName.trim()} onClick={() => void action(async () => { await request(base + '/sandbox/package', { manager: packageManager, name: packageName, version: packageVersion }); await loadSandbox(); })}>Im abgeleiteten Container-Image installieren</button></div>
      <p className="field-hint">Ressourcenregler stehen unter Einstellungen: Speicher {snapshot.settings.sandbox_memory}, CPUs {snapshot.settings.sandbox_cpus}, Prozesse {snapshot.settings.sandbox_pids}, Ports {snapshot.settings.sandbox_ports || 'keine'}.</p>
    </section>
  </div>;
}
