import { useEffect, useState } from 'react';
import type { Preflight, Settings, SourcesInfo } from './pilotTypes';
import { RoleEditor } from './CollaborationPanel';
import type { RoleModel } from './CollaborationPanel';
import { useI18n, sourceName, modeName, preferenceName } from './i18n';

type OptionModel = { key: string; max_context_length?: number; selected_variant?: string; source?: string; source_label?: string };
type Collaboration = {
  models: RoleModel[];
  handoff_models: string[];
  review_models: string[];
  settings?: Record<string, unknown>;
  blocked_message?: string;
  errors?: Record<string, string>;
};
type Options = {
  models: OptionModel[];
  candidates: string[];
  judge: string;
  sources?: { source: string; blocked: boolean }[];
  blocked_message?: string;
  prefix?: boolean;
  collaboration?: Collaboration;
};
type SnapshotLite = { busy: boolean; phase: string; error?: string; preflight?: Preflight | null; state?: { status?: string; plan_file?: string; plan?: { version: number } } | null };
const PAUSE = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const SOURCE_LABELS: Record<string, string> = { local: 'Lokal (LM Studio)', free: 'OpenCode Free', api: 'API (bezahlt)' };
const MODE_LABELS: Record<string, string> = { local: 'Nur Lokal', free: 'Nur Free', api: 'Nur API', free_local: 'Free & Lokal', local_api: 'Lokal & API', free_api: 'Free & API' };
const PREFERENCE_LABELS: Record<string, string> = { max_quality: 'MAX Quality', balanced: 'Preis/Leistung', cost_saving: 'Kostensparend' };

function splitKey(key: string, prefix: boolean | undefined): [string | null, string] {
  const index = key.indexOf('::');
  if (prefix && index > 0) {
    const source = key.slice(0, index);
    const model = key.slice(index + 2);
    if (SOURCE_LABELS[source] && model) return [source, model];
  }
  return [null, key];
}

function bareModel(key: string) {
  return splitKey(key, true)[1];
}

function sameList(left: string[] | undefined, right: string[] | undefined) {
  const a = (left || []).map(bareModel);
  const b = (right || []).map(bareModel);
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

export default function PreflightPanel({ base, goal, busy, report, settings, sourcesInfo, request, action, saveSettings, savePatch, refresh, onStarted }: {
  base: string;
  goal: string;
  busy: boolean;
  report?: Preflight | null;
  settings?: Settings | null;
  sourcesInfo?: SourcesInfo | null;
  request: <T>(url: string, data?: unknown) => Promise<T>;
  action: (fn: () => Promise<void>) => Promise<void>;
  saveSettings: () => Promise<void>;
  savePatch: (patch: Partial<Settings>) => Promise<void>;
  refresh: () => Promise<void>;
  onStarted?: () => void;
}) {
  const { t } = useI18n();
  const [kind, setKind] = useState('coding');
  const [options, setOptions] = useState<Options | null>(null);
  const [candidates, setCandidates] = useState<string[]>([]);
  const [judge, setJudge] = useState('');
  const [context, setContext] = useState(20000);
  const [two, setTwo] = useState(true);
  const [count, setCount] = useState(3);
  const [auto, setAuto] = useState('');
  const [roles, setRoles] = useState<Collaboration | null>(null);
  const [handoff, setHandoff] = useState<string[]>([]);
  const [review, setReview] = useState<string[]>([]);
  const [handoffEnabled, setHandoffEnabled] = useState(settings?.handoff_enabled !== false);
  const [reviewEnabled, setReviewEnabled] = useState(settings?.review_enabled !== false);
  const [strict, setStrict] = useState(settings?.review_strict !== false);
  const [afterFailures, setAfterFailures] = useState(Number(settings?.handoff_after_failures ?? 2));
  const [minApprovals, setMinApprovals] = useState(Number(settings?.review_min_approvals ?? 1));
  const [roleError, setRoleError] = useState('');
  const labels: Record<string, string> = { ...(sourcesInfo?.labels || SOURCE_LABELS), local: sourceName('local', t), free: 'OpenCode Free', api: sourceName('api', t) };
  const modes: Record<string, string> = { ...(sourcesInfo?.modes || MODE_LABELS), ...Object.fromEntries(Object.keys(MODE_LABELS).map(key => [key, modeName(key, t)])) };
  const preferences: Record<string, string> = { ...(sourcesInfo?.preferences || PREFERENCE_LABELS), ...Object.fromEntries(Object.keys(PREFERENCE_LABELS).map(key => [key, preferenceName(key, t)])) };
  const prefix = report?.source_prefix ?? options?.prefix;

  useEffect(() => {
    if (!settings) return;
    setHandoffEnabled(settings.handoff_enabled !== false);
    setReviewEnabled(settings.review_enabled !== false);
    setStrict(settings.review_strict !== false);
    setAfterFailures(Number(settings.handoff_after_failures ?? 2));
    setMinApprovals(Number(settings.review_min_approvals ?? 1));
  }, [settings?.handoff_enabled, settings?.review_enabled, settings?.review_strict, settings?.handoff_after_failures, settings?.review_min_approvals]);

  function applyCollaboration(data: Collaboration | undefined) {
    if (!data) return;
    setRoles(data);
    setHandoff(data.handoff_models || []);
    setReview(data.review_models || []);
    const values = data.settings || {};
    if (typeof values.handoff_enabled === 'boolean') setHandoffEnabled(values.handoff_enabled);
    if (typeof values.review_enabled === 'boolean') setReviewEnabled(values.review_enabled);
    if (typeof values.review_strict === 'boolean') setStrict(values.review_strict);
    if (typeof values.handoff_after_failures === 'number') setAfterFailures(values.handoff_after_failures);
    if (typeof values.review_min_approvals === 'number') setMinApprovals(values.review_min_approvals);
  }

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await request<Collaboration>(base + '/collaboration/models');
        if (!active) return;
        applyCollaboration(data);
        setRoleError('');
      } catch (error) {
        if (active) setRoleError((error as Error).message);
      }
    };
    void load();
    return () => { active = false; };
  }, [base, settings?.source_mode, settings?.preference]);

  function applyOptions(data: Options) {
    setOptions(data);
    setCandidates(data.candidates.slice(0, count));
    setJudge(data.judge);
    applyCollaboration(data.collaboration);
  }

  function sourceText(key: string, knownPrefix = prefix) {
    const [source, model] = splitKey(key, knownPrefix);
    return source ? `${labels[source] || source} · ${model}` : model;
  }
  function sourceOf(key: string) {
    const [source, model] = splitKey(key, prefix);
    return { source, model };
  }
  function changeCount(value: number) {
    setCount(value);
    setCandidates(old => {
      const next = old.slice(0, value);
      while (next.length < value) {
        const pick = options?.candidates.find(key => !next.includes(key));
        next.push(pick || '');
      }
      return next;
    });
  }
  function rolePayload() {
    return {
      handoff_models: handoff,
      review_models: review,
      handoff_enabled: handoffEnabled,
      review_enabled: reviewEnabled,
      review_strict: strict,
      handoff_after_failures: afterFailures,
      review_min_approvals: minApprovals
    };
  }
  async function waitFor(done: (snapshot: SnapshotLite) => boolean, label: string, timeout = 3600000) {
    const started = Date.now();
    for (;;) {
      const snapshot = await request<SnapshotLite>(base);
      setAuto(label + ' … ' + snapshot.phase);
      if (done(snapshot)) return snapshot;
      if (Date.now() - started > timeout) throw Error(t(`Zeitlimit für „${label}“ überschritten.`, `Time limit for “${label}” exceeded.`));
      await PAUSE(1200);
    }
  }
  async function autopilot() {
    if (!goal.trim() || !judge || !candidates.some(Boolean)) return;
    await saveSettings();
    const before = await request<SnapshotLite>(base);
    setAuto(t('Vorabcheck wird gestartet …', 'Starting preflight …'));
    await request(base + '/preflight', { goal, kind, candidates: [...new Set(candidates.filter(Boolean))], judge, context_tokens: context, two_temperatures: two, ...rolePayload() });
    const checked = await waitFor(s => !s.busy, t('Vorabcheck', 'Preflight'));
    if (checked.error || checked.preflight?.status !== 'ready') throw Error(checked.error || checked.preflight?.error || t('Vorabcheck ohne auswertbare Empfehlung beendet.', 'Preflight finished without a usable recommendation.'));
    setAuto(t('Empfehlung wird übernommen …', 'Applying recommendation …'));
    await request(base + '/preflight/accept', { goal });
    const accepted = await waitFor(s => !s.busy && (!!s.preflight?.accepted || !!s.error || !!s.preflight?.error), t('Modell laden', 'Load model'));
    if (!accepted.preflight?.accepted) throw Error(accepted.error || accepted.preflight?.error || t('Empfehlung konnte nicht übernommen werden.', 'The recommendation could not be applied.'));
    setAuto(t('Plan wird aus der Beschreibung erstellt …', 'Creating the plan from the description …'));
    await request(base + '/generate', { goal });
    const generated = await waitFor(s => !s.busy && ((s.state?.plan_file || '') !== (before.state?.plan_file || '') || !!s.error), t('Planerstellung', 'Plan generation'));
    if (!generated.state?.plan_file) throw Error(generated.error || t('Es wurde kein Aufgabenplan erstellt.', 'No task plan was created.'));
    setAuto(t('Ausführung wird gestartet …', 'Starting execution …'));
    await request(base + '/start', { answer: '' });
    const started = await waitFor(s => s.busy || !!s.error || (s.state?.status || 'READY') !== 'READY', t('Start', 'Start'));
    if (started.error) throw Error(started.error);
    setAuto(t('Automatischer Ablauf abgeschlossen.', 'Automatic sequence completed.'));
    await refresh();
    onStarted?.();
  }
  const staleGoal = !!report?.goal && report.goal.trim() !== goal.trim();
  const stalePreset = !!report && ((!!report.source_mode && report.source_mode !== settings?.source_mode) || (!!report.preference && report.preference !== settings?.preference));
  const reportRoles = report?.roles;
  const roleSettings = (report?.role_settings || {}) as Record<string, unknown>;
  const staleRoles = !!report && (
    !sameList(handoff, reportRoles?.handoff_models || report?.handoff_models) ||
    !sameList(review, reportRoles?.review_models || report?.review_models) ||
    (roleSettings.handoff_enabled !== undefined && roleSettings.handoff_enabled !== handoffEnabled) ||
    (roleSettings.review_enabled !== undefined && roleSettings.review_enabled !== reviewEnabled) ||
    (roleSettings.review_strict !== undefined && roleSettings.review_strict !== strict) ||
    (roleSettings.handoff_after_failures !== undefined && roleSettings.handoff_after_failures !== afterFailures) ||
    (roleSettings.review_min_approvals !== undefined && roleSettings.review_min_approvals !== minApprovals)
  );
  const stale = staleGoal || stalePreset || staleRoles;
  const reportMode = report?.source_mode ? modes[report.source_mode] || report.source_mode : '';
  const reportPreference = report?.preference ? preferences[report.preference] || report.preference : '';
  const recSource = report?.recommendation ? (report.recommendation.source || sourceOf(report.recommendation.model).source) : null;
  const freeRecommendation = recSource === 'free' || (!recSource && report?.provider === 'opencode');
  const quotaReported = !!report && (/rate.?limit|quota|kontingent|tageslimit|429/i.test(report.error || '') || (report.skipped_sources || []).length > 0);
  async function rerun() {
    if (!report) return;
    if (!goal.trim()) throw Error(t('Für den erneuten Vorabcheck zuerst eine Aufgabe beschreiben.', 'Describe a task first before re-running the preflight.'));
    await saveSettings();
    let list = [...new Set((report.candidates?.length ? report.candidates : report.samples.map(sample => sample.model)).filter(Boolean))];
    let judgeValue = report.judge || options?.judge || '';
    const testKind = report.kind || kind;
    const testContext = report.context_tokens || context;
    if (stalePreset || !list.length || !judgeValue) {
      // A changed preset invalidates prefixed model keys. Refresh the options
      // instead of sending old source keys into the new profile.
      const data = await request<Options>(base + '/preflight/options', { kind: testKind });
      applyOptions(data);
      list = data.candidates;
      judgeValue = data.judge;
      if (!list.length || !judgeValue) throw Error(t('Für den erneuten Vorabcheck zuerst Kandidaten und Auswertungsmodell wählen.', 'Choose candidates and an evaluation model before re-running the preflight.'));
    }
    setAuto(t('Vorabcheck wird erneut gestartet …', 'Restarting preflight …'));
    await request(base + '/preflight', { goal, kind: testKind, candidates: list, judge: judgeValue, context_tokens: testContext, two_temperatures: false, ...rolePayload() });
    await refresh();
    setAuto(t('Vorabcheck erneut gestartet. Der bisherige Bericht bleibt bis zum neuen Ergebnis sichtbar.', 'Preflight restarted. The previous report stays visible until the new result arrives.'));
  }
  const collaborationModels = roles?.models || options?.collaboration?.models || options?.models.map(model => ({ key: model.key, model: model.key, source: model.source, source_label: model.source_label })) || [];
  return <section className="panel preflight-panel" data-tour="preflight-panel">
    <h2>{t('1 · Modell-Vorabcheck', '1 · Model preflight')}</h2>
    <p>{t('Aufgabe oben beschreiben, Kandidaten vorschlagen lassen und Arbeitsproben vergleichen. ', 'Describe the task above, suggest candidates and compare work samples. ')}{report?.sources?.includes('free')
      ? t('OpenCode Free lädt keine Modelle in den Arbeitsspeicher; die Arbeitsproben laufen nacheinander über den lokalen kostenlosen Dienst. Alle Free-Modelle teilen sich dabei ein Tageskontingent.', 'OpenCode Free does not load models into memory; work samples run one after another through the local free service. All free models share one daily quota.')
      : t('Währenddessen werden lokale Modelle am eingestellten LM-Studio-Server entladen. Andere Anwendungen dort bitte pausieren.', 'During the comparison, local models are unloaded from the configured LM Studio server. Please pause other applications there.')}</p>
    <label className="check-label"><input type="checkbox" checked={!!settings?.skip_preflight} disabled={busy} onChange={event => void action(async () => { await savePatch({ skip_preflight: event.target.checked }); })} />{t('Vorabcheck überspringen (Start ohne bestätigten Modellvergleich erlauben)', 'Skip preflight (allow start without a confirmed model comparison)')}</label>
    <div className="settings-grid">
      <label className="field">{t('Testprofil', 'Test profile')}<select disabled={busy} value={kind} onChange={event => { setKind(event.target.value); setOptions(null); setCandidates([]); setJudge(''); }}>
        <option value="coding">{t('Coding & Tests', 'Coding & tests')}</option>
        <option value="presentation">{t('Präsentationen: Struktur & Verständlichkeit', 'Presentations: structure & clarity')}</option>
        <option value="context">{t('Großer Kontext / Quellenabgleich', 'Large context / source comparison')}</option>
        <option value="general">{t('Allgemeine Aufgaben', 'General tasks')}</option>
      </select></label>
      <label className="field">{t('Kontext für diesen Vergleich', 'Context for this comparison')}<input type="number" min={4096} max={200000} value={context} disabled={busy} onChange={event => setContext(Number(event.target.value))} /><small>{t('20.000 als Ausgangswert; wird beim Laden geprüft. Kleine Abweichungen werden als geprüfter Ist-Wert übernommen.', '20,000 as a starting value; verified when loading. Small differences are adopted as the verified actual value.')}</small></label>
    </div>
    <button className="button secondary" disabled={busy || !goal.trim()} onClick={() => void action(async () => { await saveSettings(); const data = await request<Options>(base + '/preflight/options', { kind }); applyOptions(data); })}>{t('Installierte Modelle prüfen & Kandidaten vorschlagen', 'Check installed models & suggest candidates')}</button>
    {options && <>
      <p>{t('Drei bis sechs Kandidaten wählbar. Vorauswahl nach Modellfamilie, kein bereits gemessenes Qualitätsurteil. ', 'Choose three to six candidates. Preselection is by model family, not a measured quality judgement. ')}{options.prefix ? t('Kandidaten sind mit ihrer Quelle gekennzeichnet.', 'Candidates are labelled with their source.') : t('Quantisierung laut Quelle beachten.', 'Consider the quantization reported by the source.')}</p>
      {options.blocked_message && <p className="field-error" role="status">{options.blocked_message}</p>}
      <div className="settings-grid">
        <label className="field">{t('Anzahl Kandidaten', 'Number of candidates')}<select disabled={busy} value={count} onChange={event => changeCount(Number(event.target.value))}>{[3, 4, 5, 6].map(n => <option key={n} value={n}>{t(`${n} Kandidaten`, `${n} candidates`)}</option>)}</select></label>
        {Array.from({ length: count }, (_, i) => <label className="field" key={i}>{t(`Kandidat ${i + 1}`, `Candidate ${i + 1}`)}
          <select disabled={busy} value={candidates[i] || ''} onChange={event => setCandidates(old => { const next = [...old]; while (next.length < count) next.push(''); next[i] = event.target.value; return next; })}>
            <option value="">{t('Keiner', 'None')}</option>
            {options.models.map(model => <option key={model.key} value={model.key}>{model.source_label ? model.source_label + ' · ' : ''}{model.key}{model.selected_variant ? ' · ' + model.selected_variant : ''}</option>)}
          </select>
        </label>)}
        <label className="field">{t('Allgemeines Auswertungsmodell', 'General evaluation model')}<select disabled={busy} value={judge} onChange={event => setJudge(event.target.value)}>
          <option value="">{t('Auswählen', 'Choose')}</option>
          {options.models.map(model => <option key={model.key} value={model.key}>{model.source_label ? model.source_label + ' · ' : ''}{model.key}</option>)}
        </select></label>
      </div>
      <label className="check-label"><input type="checkbox" checked={two} disabled={busy} onChange={event => setTwo(event.target.checked)} />{t('Zwei Temperaturen testen (höherer Zeitbedarf; bei Free-Kontingent sparsam einsetzen)', 'Test two temperatures (takes longer; use sparingly with a free quota)')}</label>
      <div className="inline-actions">
        <button className="button primary" disabled={busy || !judge || !candidates.some(Boolean) || !goal.trim()} onClick={() => void action(async () => { await saveSettings(); await request(base + '/preflight', { goal, kind, candidates: [...new Set(candidates.filter(Boolean))], judge, context_tokens: context, two_temperatures: two, ...rolePayload() }); await refresh(); })}>{t('Vorabcheck starten', 'Start preflight')}</button>
        <button className="button primary" disabled={busy || !judge || !candidates.some(Boolean) || !goal.trim()} onClick={() => void action(autopilot)}>{t('Automatisch: Vorabcheck → Empfehlung → Plan → Start', 'Automatic: preflight → recommendation → plan → start')}</button>
      </div>
      {auto && <p role="status" className="field-hint">{auto}</p>}
    </>}
    <div className="collaboration-options preflight-roles">
      <h3>{t('Übergabe & Prüfung für diesen Vorabcheck', 'Handoff & review for this preflight')}</h3>
      <p className="field-hint">{t('Die Auswahl wird mit der Empfehlung übernommen. Im laufenden Betrieb lässt sie sich jederzeit unter „Übergabe & Prüfung“ ändern.', 'The selection is applied together with the recommendation. During a run it can be changed at any time under “Handoff & review”.')}</p>
      {roleError && <p className="field-error" role="alert">{roleError}</p>}
      {roles?.blocked_message && <p className="field-hint">{roles.blocked_message}</p>}
      {!!roles?.errors && Object.keys(roles.errors).length > 0 && <p className="field-hint">{Object.entries(roles.errors).map(([source, text]) => `${source}: ${text}`).join(' · ')}</p>}
      <div className="collaboration-options">
        <label className="check-label"><input type="checkbox" checked={handoffEnabled} disabled={busy} onChange={event => setHandoffEnabled(event.target.checked)} />{t('Übergabe an andere Modelle erlauben', 'Allow handoff to other models')}</label>
        <label className="check-label"><input type="checkbox" checked={reviewEnabled} disabled={busy} onChange={event => setReviewEnabled(event.target.checked)} />{t('Unabhängige Ergebnisprüfung erlauben', 'Allow independent result review')}</label>
        <label className="check-label"><input type="checkbox" checked={strict} disabled={busy} onChange={event => setStrict(event.target.checked)} />{t('Bei eindeutiger Ablehnung reparieren statt nur protokollieren', 'Repair after a clear rejection instead of only logging it')}</label>
        <label className="field compact-field">{t('Übergabe nach Fehlversuchen', 'Hand off after failed attempts')}<input type="number" min={1} max={8} value={afterFailures} disabled={busy} onChange={event => setAfterFailures(Number(event.target.value))} /></label>
        <label className="field compact-field">{t('Mindestzustimmungen für Prüfung', 'Minimum review approvals')}<input type="number" min={1} max={8} value={minApprovals} disabled={busy} onChange={event => setMinApprovals(Number(event.target.value))} /></label>
      </div>
      <div className="role-grid">
        <RoleEditor label={t('Übergabe-Reihenfolge', 'Handoff order')} hint={t('Wird der Reihe nach versucht; das aktive Hauptmodell bleibt ausgeschlossen.', 'Tried in order; the active primary model is excluded.')} models={collaborationModels} selected={handoff} onChange={setHandoff} disabled={busy || !handoffEnabled} emptyLabel={t('Keine Übergabemodelle gewählt. Das Hauptmodell bleibt allein zuständig.', 'No handoff models selected. The primary model remains solely responsible.')} />
        <RoleEditor label={t('Prüfer-Reihenfolge', 'Reviewer order')} hint={t('Ersteller einer Aufgabe werden automatisch von deren Prüfung ausgeschlossen.', 'Creators of a task are automatically excluded from reviewing it.')} models={collaborationModels} selected={review} onChange={setReview} disabled={busy || !reviewEnabled} emptyLabel={t('Keine Prüfer gewählt. Es findet keine unabhängige Prüfung statt.', 'No reviewers selected. No independent review will run.')} />
      </div>
    </div>
    {report && <>
      <div className="preflight-status">
        <p role="status">{t('Status', 'Status')}: {report.status === 'ready' ? t('Ausgewertet', 'Evaluated') : report.status === 'running' ? t('Läuft', 'Running') : t('Angehalten', 'Stopped')}{report.accepted ? t(' · übernommen', ' · applied') : ''}{report.status === 'error' ? t(' · Fehler', ' · error') : ''}{reportMode ? t(` · Profil ${reportMode}`, ` · profile ${reportMode}`) : ''}{reportPreference ? ` · ${reportPreference}` : ''}</p>
        <div className="inline-actions">
          <button className="button secondary" disabled={busy || report.status === 'running' || !goal.trim()} onClick={() => void action(rerun)}>{t('Vorabcheck erneut ausführen', 'Run preflight again')}</button>
          <button className="button secondary" disabled={busy || !goal.trim()} onClick={() => void action(async () => {
            await saveSettings();
            const data = await request<Options>(base + '/preflight/options', { kind: report.kind || kind });
            const available = new Set(data.models.map(model => model.key));
            const kept = stalePreset ? [] : (report.candidates || []).filter(key => available.has(key));
            applyOptions(data);
            setCandidates((kept.length ? kept : data.candidates).slice(0, count));
            setJudge(available.has(report.judge || '') ? report.judge || '' : data.judge);
            setAuto(kept.length ? t('Kandidaten aus dem letzten Bericht geladen; Auswahl kann geändert werden.', 'Candidates from the last report loaded; the selection can be changed.') : t('Frische Kandidaten für die aktuelle Vorauswahl geladen.', 'Fresh candidates loaded for the current preset.'));
          })}>{t('Kandidaten erneut laden', 'Reload candidates')}</button>
        </div>
      </div>
      {staleGoal && <p className="field-error" role="alert">{t('Die Aufgabe wurde seit diesem Vorabcheck geändert. Bericht ist veraltet; bitte erneut ausführen.', 'The task changed since this preflight. The report is outdated; please run it again.')}</p>}
      {!staleGoal && stalePreset && <p className="field-error" role="alert">{t(`Quellen-Vorauswahl oder Reihenfolge wurde geändert. Der Bericht gilt für ${reportMode || 'die bisherige Vorauswahl'}${reportPreference ? ` · ${reportPreference}` : ''}. Bitte erneut ausführen.`, `The source preset or order changed. The report applies to ${reportMode || 'the previous preset'}${reportPreference ? ` · ${reportPreference}` : ''}. Please run it again.`)}</p>}
      {staleRoles && !staleGoal && !stalePreset && <p className="field-error" role="alert">{t('Übergabe- oder Prüferauswahl wurde geändert. Bitte den Vorabcheck erneut ausführen, damit die Rollen mit der Empfehlung übernommen werden.', 'The handoff or reviewer selection changed. Run the preflight again so the roles are applied with the recommendation.')}</p>}
      {quotaReported && <p className="field-hint" role="note"><strong>{t('Free-Kontingent:', 'Free quota:')}</strong> {t('Alle OpenCode-Free-Modelle teilen sich das Tageslimit. Ein anderer Free-Modellname schafft kein neues Kontingent. Für einen erneuten Lauf eine im Profil erlaubte lokale oder bezahlte API-Quelle wählen oder auf den Reset warten.', 'All OpenCode free models share the daily limit. A different free model name does not create new quota. For another run, choose a local or paid API source allowed by the profile or wait for the reset.')}</p>}
      {report.error && <p role="alert" className="field-error">{report.error}</p>}
      {!!report.skipped_sources?.length && <details open><summary>{t(`Übersprungene Kandidaten (${report.skipped_sources.length})`, `Skipped candidates (${report.skipped_sources.length})`)}</summary><ul>{report.skipped_sources.map(key => <li key={key}>{sourceText(key)}</li>)}</ul><small>{t('Die Quelle war beim Lauf vorübergehend gesperrt. Der Bericht bleibt für ungesperrte Kandidaten auswertbar.', 'The source was temporarily blocked during the run. The report remains usable for unblocked candidates.')}</small></details>}
      {report.samples.map(sample => {
        const score = report.verdict?.scores[sample.id];
        return <details key={sample.id}><summary>{sample.id} · {sourceText(sample.model)} · T {sample.temperature} · {sample.seconds ?? '—'} s · {sample.valid ? t('Format gültig', 'Format valid') : t('Ungültig', 'Invalid')}{score !== undefined ? t(` · Bewertung ${score}/100`, ` · score ${score}/100`) : ''}</summary><pre style={{ whiteSpace: 'pre-wrap' }}>{sample.response || sample.error}</pre></details>;
      })}
      {!!report.alternatives?.length && <details><summary>{t(`Gemessene Ausweichquellen (${report.alternatives.length})`, `Measured alternative sources (${report.alternatives.length})`)}</summary><div className="table-wrap"><table><thead><tr><th>{t('Quelle', 'Source')}</th><th>{t('Modell', 'Model')}</th><th>{t('Temperatur', 'Temperature')}</th><th>{t('Kontext', 'Context')}</th><th>{t('Bewertung', 'Score')}</th></tr></thead><tbody>{report.alternatives.map(row => <tr key={row.model}><td>{labels[row.source || ''] || sourceOf(row.model).source || '—'}</td><td>{sourceOf(row.model).model}</td><td>{row.temperature}</td><td>{row.context_tokens}</td><td>{row.score ?? '—'}</td></tr>)}</tbody></table></div><small>{t('Nur gemessene Kandidaten aus genau diesem Lauf. Bei einem späteren Quellenwechsel kann eine bereits geprüfte Alternative übernommen werden.', 'Only candidates measured in this exact run. If the source changes later, an already verified alternative can be applied.')}</small></details>}
      {report.recommendation && <>
        <h3>{t('Empfehlung', 'Recommendation')}: {sourceText(report.recommendation.model)}</h3>
        <p>{t('Temperatur', 'Temperature')} {report.recommendation.temperature} · {t('Kontext', 'Context')} {report.recommendation.context_tokens} {t('Tokens', 'tokens')}{report.recommendation.score !== undefined ? t(` · Bewertung ${report.recommendation.score}/100`, ` · score ${report.recommendation.score}/100`) : ''}</p>
        <p>{report.recommendation.reason}</p>
        <button className="button primary" disabled={busy || report.status !== 'ready' || stale} onClick={() => void action(async () => { await request(base + '/preflight/accept', { goal }); await refresh(); })}>{freeRecommendation ? t('Empfehlung übernehmen', 'Apply recommendation') : t('Empfehlung übernehmen & Modell laden', 'Apply recommendation & load model')}</button>
      </>}
      {report.accepted_settings && <p className="field-hint">{t('Übernommen', 'Applied')}: {labels[report.accepted_settings.source || ''] || report.accepted_settings.source || report.accepted_settings.provider || '—'} · {report.accepted_settings.model || '—'} · {report.accepted_settings.context_tokens ?? '—'} {t('Tokens', 'tokens')}</p>}
      <p className="field-hint">{report.note} {t('Ergebnisse werden im Projekt unter .toolforge/preflight-history gespeichert; der letzte Bericht bleibt auch nach einem Fehler sichtbar.', 'Results are stored in the project under .toolforge/preflight-history; the last report stays visible even after an error.')}</p>
    </>}
  </section>;
}
