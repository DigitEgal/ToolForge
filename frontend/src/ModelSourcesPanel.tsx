import { useEffect, useState } from 'react';
import type { Model, OpenCodeStatus, Settings, Snapshot } from './pilotTypes';
import { useI18n, tr, sourceName, modeName, preferenceName } from './i18n';

type SourceKey = 'local' | 'free' | 'api';
type RequestFn = <T>(path: string, data?: unknown, method?: string) => Promise<T>;

const MODE_SOURCES: Record<string, SourceKey[]> = {
  local: ['local'], free: ['free'], api: ['api'],
  free_local: ['free', 'local'], local_api: ['local', 'api'], free_api: ['free', 'api']
};
const PREFERENCE_ORDER: Record<string, SourceKey[]> = {
  max_quality: ['api', 'local', 'free'],
  balanced: ['free', 'local', 'api'],
  cost_saving: ['local', 'free', 'api']
};
function allowedSources(mode: string, preference: string): SourceKey[] {
  const allowed = MODE_SOURCES[mode] || ['local'];
  const preferred = (PREFERENCE_ORDER[preference] || PREFERENCE_ORDER.balanced).filter(source => allowed.includes(source));
  return [...preferred, ...allowed.filter(source => !preferred.includes(source))];
}

function blockedText(until: number) {
  const remaining = Math.max(1, Math.ceil((until - Date.now() / 1000) / 60));
  return tr(`noch ca. ${remaining} Minuten`, `about ${remaining} more minutes`);
}

function modelOptions(models: Model[], value: string) {
  const rows = models.filter(row => row.type !== 'embedding');
  return <>
    <option value="">{tr('Modell auswählen', 'Choose a model')}</option>
    {value && !rows.some(row => row.id === value) && <option value={value}>{value} · {tr('gespeichert', 'saved')}</option>}
    {rows.map(row => <option value={row.id} key={row.id}>
      {row.id}{row.loaded_context ? ` · ${row.loaded_context} ${tr('Tokens', 'tokens')}` : row.saved_profile?.context_tokens ? ` · ${row.saved_profile.context_tokens} ${tr('Tokens', 'tokens')}` : ''}
    </option>)}
  </>;
}

export default function ModelSourcesPanel({ base, settings, snapshot, busy: parentBusy, request, update, saveSettings }: {
  base: string; settings: Settings; snapshot: Snapshot; busy: boolean; request: RequestFn;
  update: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
  saveSettings: () => Promise<void>;
}) {
  const { t } = useI18n();
  const [models, setModels] = useState<Partial<Record<SourceKey, Model[]>>>({});
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [opencode, setOpencode] = useState<OpenCodeStatus | null>(null);
  const [orderText, setOrderText] = useState(settings.opencode_order.join(', '));
  const busy = parentBusy || pending;

  useEffect(() => {
    setOrderText(settings.opencode_order.join(', '));
  }, [settings.opencode_order]);

  const modes = { ...(snapshot.sources?.modes || {}), local: modeName('local', t), free: modeName('free', t), api: modeName('api', t), free_local: modeName('free_local', t), local_api: modeName('local_api', t), free_api: modeName('free_api', t) };
  const preferences = { ...(snapshot.sources?.preferences || {}), max_quality: preferenceName('max_quality', t), balanced: preferenceName('balanced', t), cost_saving: preferenceName('cost_saving', t) };
  const labels: Record<string, string> = { ...(snapshot.sources?.labels || {}), local: sourceName('local', t), free: 'OpenCode Free', api: sourceName('api', t) };
  const mode = settings.source_mode in MODE_SOURCES ? settings.source_mode : 'local';
  const preference = settings.preference in PREFERENCE_ORDER ? settings.preference : 'balanced';
  const activeSources = MODE_SOURCES[mode];
  const order = allowedSources(mode, preference);
  const activeSource: SourceKey = settings.provider === 'opencode' ? 'free' : settings.provider === 'api' ? 'api' : 'local';
  const blockedSources = snapshot.opencode?.blocked_sources || {};
  const blockedRows = Object.entries(blockedSources)
    .filter(([, until]) => until > Date.now() / 1000)
    .sort((a, b) => a[1] - b[1]);

  async function run(task: () => Promise<void>) {
    setPending(true); setError('');
    try { await task(); } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function loadModels(source: SourceKey) {
    await run(async () => {
      setStatus(`${labels[source]} · ${t('Modelle werden geladen …', 'Loading models …')}`);
      await saveSettings();
      const rows = await request<Model[]>(base + '/models', { source });
      setModels(old => ({ ...old, [source]: rows }));
      setStatus(`${labels[source]} · ${t(`${rows.filter(row => row.type !== 'embedding').length} Modelle geladen.`, `${rows.filter(row => row.type !== 'embedding').length} models loaded.`)}`);
    });
  }

  function chooseModel(source: SourceKey, value: string) {
    if (source === 'local') update('local_model', value);
    else if (source === 'free') update('free_model', value);
    else update('api_model', value);
    const current = activeSource === source;
    if (current) update('model', value);
    const row = (models[source] || []).find(item => item.id === value);
    if (current && row) {
      const context = row.loaded_context || row.saved_profile?.context_tokens;
      if (context) {
        update('context_tokens', context);
        update('output_tokens', Math.min(row.saved_profile?.output_tokens || settings.output_tokens, Math.floor(context / 2)));
      }
      if (row.saved_profile?.temperature !== undefined) update('temperature', row.saved_profile.temperature);
    }
  }

  function parseOrder(value: string) {
    setOrderText(value);
    update('opencode_order', value.split(',').map(item => item.trim()).filter(Boolean));
  }

  async function checkOpenCode(start: boolean) {
    await run(async () => {
      setStatus(start ? t('OpenCode wird gestartet …', 'Starting OpenCode …') : t('OpenCode-Status wird geprüft …', 'Checking OpenCode status …'));
      const data = await request<OpenCodeStatus>(base + '/opencode/status', { start });
      setOpencode(data);
      setStatus(data.available
        ? `${t('OpenCode verbunden', 'OpenCode connected')}${data.url ? ': ' + data.url : ''}${data.version ? ' · ' + data.version : ''}.`
        : t('OpenCode nicht verbunden: ', 'OpenCode not connected: ') + (data.error || t('unbekannter Fehler', 'unknown error')));
    });
  }

  async function openConsole() {
    await run(async () => {
      const data = await request<{ started: boolean; command: string; directory: string }>(base + '/opencode/console', {});
      setStatus(t(`OpenCode-Konsole geöffnet: ${data.directory}`, `OpenCode console opened: ${data.directory}`));
    });
  }

  const statusText = (source: SourceKey) => activeSource === source
    ? t('aktiv', 'active')
    : activeSources.includes(source) ? t('erlaubt', 'allowed') : t('nicht im Profil', 'not in profile');

  return <section className="panel model-sources-panel" data-tour="model-sources">
    <div className="panel-title">
      <div>
        <h2>{t('Modellquellen', 'Model sources')}</h2>
        <p>{t('Lege fest, welche Quellen erlaubt sind und in welcher Reihenfolge ToolForge ausweicht. Modelle werden pro Quelle gespeichert.', 'Choose which sources are allowed and in which order ToolForge falls back. Models are stored per source.')}</p>
      </div>
      <span className="stage-badge">V1.4</span>
    </div>

    <h3>{t('Quellen-Vorauswahl', 'Source preset')}</h3>
    <div className="source-preset-grid" role="group" aria-label={t('Modellquellen-Vorauswahl', 'Model source preset')}>
      {Object.entries(modes).map(([key, label]) => <button type="button" key={key}
        className={`source-preset ${mode === key ? 'selected' : ''}`}
        aria-pressed={mode === key} disabled={busy}
        onClick={() => update('source_mode', key)}>
        <strong>{label}</strong>
        <small>{(MODE_SOURCES[key] || []).map(source => labels[source]).join(' → ')}</small>
      </button>)}
    </div>

    <div className="settings-grid source-preference-row">
      <label className="field">{t('Fallback-Reihenfolge', 'Fallback order')}
        <select value={preference} disabled={busy} onChange={event => update('preference', event.target.value)}>
          {Object.entries(preferences).map(([key, label]) => <option value={key} key={key}>{label}</option>)}
        </select>
        <small>{t('Gilt nur für die erlaubten Quellen. Bei erschöpftem Free-Kontingent wird niemals ein anderes Free-Modell als Ersatz ausgegeben.', 'Applies only to allowed sources. When the free quota is exhausted, another free model is never substituted.')}</small>
      </label>
      <div className="field">{t('Wirksame Reihenfolge', 'Effective order')}
        <div className="source-order">{order.map((source, index) =>
          <span className={`source-chip ${activeSource === source ? 'active' : ''}`} key={source}>
            {index + 1} · {labels[source]}
          </span>)}</div>
        <small>{t('Die aktive Quelle bleibt bei einem laufenden Auftrag zuerst; danach gilt diese Reihenfolge.', 'The active source stays first while a task is running; this order applies after that.')}</small>
      </div>
    </div>

    {blockedRows.length > 0 && <div className="source-blocked" role="status">
      <strong>{t('Vorübergehend gesperrt', 'Temporarily blocked')}</strong>
      {blockedRows.map(([source, until]) => <span key={source}>{labels[source] || source} · {blockedText(until)}</span>)}
      <small>{t('Die Sperre gilt für die ganze Quelle. Erneut prüfen ist jederzeit möglich; ein Modellname innerhalb von OpenCode Free umgeht das gemeinsame Tageslimit nicht.', 'The block applies to the whole source. Checking again is always possible; another model name inside OpenCode Free does not bypass the shared daily limit.')}</small>
    </div>}
    {!blockedRows.length && snapshot.sources?.effective && <p className="field-hint">{t('Aktuell wirksam', 'Currently effective')}: {snapshot.sources.effective.map(source => labels[source] || source).join(' → ') || t('keine Quelle', 'no source')}.</p>}

    <div className="source-card-grid">
      <article className={`source-card ${activeSources.includes('local') ? 'enabled' : ''}`}>
        <div className="source-card-head"><h3>{t('Lokal · LM Studio', 'Local · LM Studio')}</h3><span className={`status-pill ${activeSource === 'local' ? 'running' : ''}`}>{statusText('local')}</span></div>
        <p>{t('Lokale Modelle laufen ohne Kontingent. Die Prüfung lädt während des Vorabchecks nacheinander die Kandidaten.', 'Local models run without a quota. During the preflight, candidates are loaded one after another.')}</p>
        <label className="field">{t('LM-Studio-API', 'LM Studio API')}<input value={settings.base} disabled={busy} onChange={event => update('base', event.target.value)} /></label>
        <label className="field">{t('API-Schlüssel (nur Sitzung)', 'API key (session only)')}<input type="password" autoComplete="off" value={settings.api_key || ''} placeholder="lm-studio" disabled={busy} onChange={event => update('api_key', event.target.value)} /></label>
        <label className="field">{t('Lokales Modell', 'Local model')}
          <div className="model-row">
            <select value={settings.local_model} disabled={busy} onChange={event => chooseModel('local', event.target.value)}>
              {modelOptions(models.local || [], settings.local_model)}
            </select>
            <button className="button secondary" type="button" disabled={busy} onClick={() => void loadModels('local')}>{t('Laden', 'Load')}</button>
          </div>
        </label>
        <small>{models.local?.length ? t(`${models.local.filter(row => row.type !== 'embedding').length} Modelle erkannt.`, `${models.local.filter(row => row.type !== 'embedding').length} models detected.`) : t('Modelle laden liest die installierte LM-Studio-Auswahl ein.', 'Load models reads the installed LM Studio selection.')}</small>
      </article>

      <article className={`source-card ${activeSources.includes('free') ? 'enabled' : ''}`}>
        <div className="source-card-head"><h3>OpenCode Free</h3><span className={`status-pill ${activeSource === 'free' ? 'running' : ''}`}>{statusText('free')}</span></div>
        <p>{t('Kostenlos ohne Konto. Alle Free-Modelle teilen sich ein Tageskontingent.', 'Free without an account. All free models share one daily quota.')}</p>
        <div className="quota-note"><strong>{t('Gemeinsames Tageslimit:', 'Shared daily limit:')}</strong> {t('Ein anderes Free-Modell ist kein zusätzliches Kontingent. Bei Erschöpfung hilft nur warten oder eine im Profil erlaubte lokale bzw. bezahlte API-Quelle.', 'A different free model is not additional quota. When exhausted, only waiting or a local or paid API source allowed by the profile helps.')}</div>
        <label className="field">{t('Free-Modell', 'Free model')}
          <div className="model-row">
            <select value={settings.free_model} disabled={busy} onChange={event => chooseModel('free', event.target.value)}>
              {modelOptions(models.free || [], settings.free_model)}
            </select>
            <button className="button secondary" type="button" disabled={busy} onClick={() => void loadModels('free')}>{t('Laden', 'Load')}</button>
          </div>
        </label>
        <div className="inline-actions source-actions">
          <button className="button secondary" type="button" disabled={busy} onClick={() => void checkOpenCode(false)}>{t('Status prüfen', 'Check status')}</button>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void checkOpenCode(true)}>{t('OpenCode starten', 'Start OpenCode')}</button>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void openConsole()}>{t('Konsole öffnen', 'Open console')}</button>
        </div>
        <small>{opencode ? (opencode.available
          ? `${t('Verbunden', 'Connected')}: ${opencode.url || ''} ${opencode.version || ''}`.trim()
          : `${t('Nicht verbunden', 'Not connected')}: ${opencode.error || t('unbekannter Fehler', 'unknown error')}`)
          : t('Status und Konsole werden nur auf Klick geprüft; der normale ToolForge-Start bleibt dadurch schnell.', 'Status and console are checked only on click, keeping normal ToolForge startup fast.')}</small>
        <details className="source-details">
          <summary>{t('Weitere freie Modelle und temporäre Fehler', 'More free models and temporary errors')}</summary>
          <label className="check-label"><input type="checkbox" checked={settings.opencode_fallback} disabled={busy} onChange={event => update('opencode_fallback', event.target.checked)} />{t('Bei temporären Modellfehlern (nicht Tageslimit) ein anderes freies Modell versuchen', 'Try another free model on temporary model errors (not the daily limit)')}</label>
          <label className="field">{t('Bevorzugte Free-Modelle (kommagetrennt)', 'Preferred free models (comma-separated)')}<input value={orderText} disabled={busy} onChange={event => parseOrder(event.target.value)} placeholder="deepseek-v4.1-flash-free, glm-5.3-flash-free" /><small>{t('Leer = alle verfügbaren Free-Modelle. Die Reihenfolge ist kein Kontingent-Reset.', 'Empty = all available free models. The order is not a quota reset.')}</small></label>
        </details>
      </article>

      <article className={`source-card ${activeSources.includes('api') ? 'enabled' : ''}`}>
        <div className="source-card-head"><h3>{t('API · bezahlt', 'API · paid')}</h3><span className={`status-pill ${activeSource === 'api' ? 'running' : ''}`}>{statusText('api')}</span></div>
        <p>{t('OpenAI-kompatible API als Qualitäts- oder Ausweichquelle. Es werden nur die konfigurierten Modelle und der Sitzungsschlüssel verwendet.', 'OpenAI-compatible API as a quality or fallback source. Only the configured models and the session key are used.')}</p>
        <label className="field">{t('API-Basis', 'API base')}<input value={settings.api_base} disabled={busy} onChange={event => update('api_base', event.target.value)} placeholder="https://api.openai.com/v1" /></label>
        <label className="field">{t('API-Schlüssel (nur Sitzung)', 'API key (session only)')}<input type="password" autoComplete="off" value={settings.remote_api_key || ''} placeholder={snapshot.sources?.remote_key_set ? t('Schlüssel gesetzt', 'Key set') : t('API-Schlüssel', 'API key')} disabled={busy} onChange={event => update('remote_api_key', event.target.value)} /><small>{t('Wird nicht gespeichert und nicht an das Projektjournal geschrieben.', 'Not saved and not written to the project journal.')}</small></label>
        <label className="field">{t('API-Modell', 'API model')}
          <div className="model-row">
            <select value={settings.api_model} disabled={busy} onChange={event => chooseModel('api', event.target.value)}>
              {modelOptions(models.api || [], settings.api_model)}
            </select>
            <button className="button secondary" type="button" disabled={busy} onClick={() => void loadModels('api')}>{t('Laden', 'Load')}</button>
          </div>
        </label>
        <small>{models.api?.length ? t(`${models.api.length} API-Modelle erkannt.`, `${models.api.length} API models detected.`) : t('Laden fragt den /models-Katalog ab; ein bereits gespeichertes Modell bleibt als Auswahl erhalten.', 'Load queries the /models catalogue; an already saved model remains selectable.')}</small>
      </article>
    </div>

    {error && <p className="field-error" role="alert">{error}</p>}
    {status && <p className="field-hint" role="status">{status}</p>}
    <div className="inline-actions">
      <button className="button primary" type="button" disabled={busy} onClick={() => void run(async () => { await saveSettings(); setStatus(t('Modellquellen gespeichert.', 'Model sources saved.')); })}>{t('Quellen & Modelle speichern', 'Save sources & models')}</button>
      <span className="field-hint">{t('Änderungen an Vorauswahl und Modellen werden erst mit dem Speichern wirksam.', 'Changes to the preset and models take effect only after saving.')}</span>
    </div>
  </section>;
}
