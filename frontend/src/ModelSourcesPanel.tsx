import { useEffect, useState } from 'react';
import type { Model, OpenCodeStatus, Settings, Snapshot } from './pilotTypes';

type SourceKey = 'local' | 'free' | 'api';
type RequestFn = <T>(path: string, data?: unknown, method?: string) => Promise<T>;

const SOURCE_LABELS: Record<string, string> = {
  local: 'Lokal (LM Studio)', free: 'OpenCode Free', api: 'API (bezahlt)'
};
const MODE_LABELS: Record<string, string> = {
  local: 'Nur Lokal', free: 'Nur Free', api: 'Nur API',
  free_local: 'Free & Lokal', local_api: 'Lokal & API', free_api: 'Free & API'
};
const PREFERENCE_LABELS: Record<string, string> = {
  max_quality: 'MAX Quality', balanced: 'Preis/Leistung', cost_saving: 'Kostensparend'
};
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
  return `noch ca. ${remaining} Minuten`;
}

function modelOptions(models: Model[], value: string) {
  const rows = models.filter(row => row.type !== 'embedding');
  return <>
    <option value="">Modell auswählen</option>
    {value && !rows.some(row => row.id === value) && <option value={value}>{value} · gespeichert</option>}
    {rows.map(row => <option value={row.id} key={row.id}>
      {row.id}{row.loaded_context ? ` · ${row.loaded_context} Tokens` : row.saved_profile?.context_tokens ? ` · ${row.saved_profile.context_tokens} Tokens` : ''}
    </option>)}
  </>;
}

export default function ModelSourcesPanel({ base, settings, snapshot, busy: parentBusy, request, update, saveSettings }: {
  base: string; settings: Settings; snapshot: Snapshot; busy: boolean; request: RequestFn;
  update: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
  saveSettings: () => Promise<void>;
}) {
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

  const modes = snapshot.sources?.modes || MODE_LABELS;
  const preferences = snapshot.sources?.preferences || PREFERENCE_LABELS;
  const labels = snapshot.sources?.labels || SOURCE_LABELS;
  const mode = settings.source_mode in MODE_SOURCES ? settings.source_mode : 'local';
  const preference = settings.preference in PREFERENCE_LABELS ? settings.preference : 'balanced';
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
      setStatus(`${labels[source]} · Modelle werden geladen …`);
      await saveSettings();
      const rows = await request<Model[]>(base + '/models', {source});
      setModels(old => ({...old, [source]: rows}));
      setStatus(`${labels[source]} · ${rows.filter(row => row.type !== 'embedding').length} Modelle geladen.`);
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
      setStatus(start ? 'OpenCode wird gestartet …' : 'OpenCode-Status wird geprüft …');
      const data = await request<OpenCodeStatus>(base + '/opencode/status', {start});
      setOpencode(data);
      setStatus(data.available
        ? `OpenCode verbunden${data.url ? ': ' + data.url : ''}${data.version ? ' · ' + data.version : ''}.`
        : 'OpenCode nicht verbunden: ' + (data.error || 'unbekannter Fehler'));
    });
  }

  async function openConsole() {
    await run(async () => {
      const data = await request<{started: boolean; command: string; directory: string}>(base + '/opencode/console', {});
      setStatus(`OpenCode-Konsole geöffnet: ${data.directory}`);
    });
  }

  return <section className="panel model-sources-panel">
    <div className="panel-title">
      <div>
        <h2>Modellquellen</h2>
        <p>Lege fest, welche Quellen erlaubt sind und in welcher Reihenfolge ToolForge ausweicht. Modelle werden pro Quelle gespeichert.</p>
      </div>
      <span className="stage-badge">V1.3</span>
    </div>

    <h3>Quellen-Vorauswahl</h3>
    <div className="source-preset-grid" role="group" aria-label="Modellquellen-Vorauswahl">
      {Object.entries(modes).map(([key, label]) => <button type="button" key={key}
        className={`source-preset ${mode === key ? 'selected' : ''}`}
        aria-pressed={mode === key} disabled={busy}
        onClick={() => update('source_mode', key)}>
        <strong>{label}</strong>
        <small>{(MODE_SOURCES[key] || []).map(source => labels[source]).join(' → ')}</small>
      </button>)}
    </div>

    <div className="settings-grid source-preference-row">
      <label className="field">Fallback-Reihenfolge
        <select value={preference} disabled={busy} onChange={event => update('preference', event.target.value)}>
          {Object.entries(preferences).map(([key, label]) => <option value={key} key={key}>{label}</option>)}
        </select>
        <small>Gilt nur für die erlaubten Quellen. Bei erschöpftem Free-Kontingent wird niemals ein anderes Free-Modell als Ersatz ausgegeben.</small>
      </label>
      <div className="field">Wirksame Reihenfolge
        <div className="source-order">{order.map((source, index) =>
          <span className={`source-chip ${activeSource === source ? 'active' : ''}`} key={source}>
            {index + 1} · {labels[source]}
          </span>)}</div>
        <small>Die aktive Quelle bleibt bei einem laufenden Auftrag zuerst; danach gilt diese Reihenfolge.</small>
      </div>
    </div>

    {blockedRows.length > 0 && <div className="source-blocked" role="status">
      <strong>Vorübergehend gesperrt</strong>
      {blockedRows.map(([source, until]) => <span key={source}>{labels[source] || source} · {blockedText(until)}</span>)}
      <small>Die Sperre gilt für die ganze Quelle. Erneut prüfen ist jederzeit möglich; ein Modellname innerhalb von OpenCode Free umgeht das gemeinsame Tageslimit nicht.</small>
    </div>}
    {!blockedRows.length && snapshot.sources?.effective && <p className="field-hint">Aktuell wirksam: {snapshot.sources.effective.map(source => labels[source] || source).join(' → ') || 'keine Quelle'}.</p>}

    <div className="source-card-grid">
      <article className={`source-card ${activeSources.includes('local') ? 'enabled' : ''}`}>
        <div className="source-card-head"><h3>Lokal · LM Studio</h3><span className={`status-pill ${activeSource === 'local' ? 'running' : ''}`}>{activeSource === 'local' ? 'aktiv' : activeSources.includes('local') ? 'erlaubt' : 'nicht im Profil'}</span></div>
        <p>Lokale Modelle laufen ohne Kontingent. Die Prüfung lädt während des Vorabchecks nacheinander die Kandidaten.</p>
        <label className="field">LM-Studio-API<input value={settings.base} disabled={busy} onChange={event => update('base', event.target.value)}/></label>
        <label className="field">API-Schlüssel (nur Sitzung)<input type="password" autoComplete="off" value={settings.api_key || ''} placeholder="lm-studio" disabled={busy} onChange={event => update('api_key', event.target.value)}/></label>
        <label className="field">Lokales Modell
          <div className="model-row">
            <select value={settings.local_model} disabled={busy} onChange={event => chooseModel('local', event.target.value)}>
              {modelOptions(models.local || [], settings.local_model)}
            </select>
            <button className="button secondary" type="button" disabled={busy} onClick={() => void loadModels('local')}>Laden</button>
          </div>
        </label>
        <small>{models.local?.length ? `${models.local.filter(row => row.type !== 'embedding').length} Modelle erkannt.` : 'Modelle laden liest die installierte LM-Studio-Auswahl ein.'}</small>
      </article>

      <article className={`source-card ${activeSources.includes('free') ? 'enabled' : ''}`}>
        <div className="source-card-head"><h3>OpenCode Free</h3><span className={`status-pill ${activeSource === 'free' ? 'running' : ''}`}>{activeSource === 'free' ? 'aktiv' : activeSources.includes('free') ? 'erlaubt' : 'nicht im Profil'}</span></div>
        <p>Kostenlos ohne Konto. Alle Free-Modelle teilen sich ein Tageskontingent.</p>
        <div className="quota-note"><strong>Gemeinsames Tageslimit:</strong> Ein anderes Free-Modell ist kein zusätzliches Kontingent. Bei Erschöpfung hilft nur warten oder eine im Profil erlaubte lokale bzw. bezahlte API-Quelle.</div>
        <label className="field">Free-Modell
          <div className="model-row">
            <select value={settings.free_model} disabled={busy} onChange={event => chooseModel('free', event.target.value)}>
              {modelOptions(models.free || [], settings.free_model)}
            </select>
            <button className="button secondary" type="button" disabled={busy} onClick={() => void loadModels('free')}>Laden</button>
          </div>
        </label>
        <div className="inline-actions source-actions">
          <button className="button secondary" type="button" disabled={busy} onClick={() => void checkOpenCode(false)}>Status prüfen</button>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void checkOpenCode(true)}>OpenCode starten</button>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void openConsole()}>Konsole öffnen</button>
        </div>
        <small>{opencode ? (opencode.available
          ? `Verbunden: ${opencode.url || ''} ${opencode.version || ''}`.trim()
          : `Nicht verbunden: ${opencode.error || 'unbekannter Fehler'}`)
          : 'Status und Konsole werden nur auf Klick geprüft; der normale ToolForge-Start bleibt dadurch schnell.'}</small>
        <details className="source-details">
          <summary>Weitere freie Modelle und temporäre Fehler</summary>
          <label className="check-label"><input type="checkbox" checked={settings.opencode_fallback} disabled={busy} onChange={event => update('opencode_fallback', event.target.checked)}/>Bei temporären Modellfehlern (nicht Tageslimit) ein anderes freies Modell versuchen</label>
          <label className="field">Bevorzugte Free-Modelle (kommagetrennt)<input value={orderText} disabled={busy} onChange={event => parseOrder(event.target.value)} placeholder="deepseek-v4.1-flash-free, glm-5.3-flash-free"/><small>Leer = alle verfügbaren Free-Modelle. Die Reihenfolge ist kein Kontingent-Reset.</small></label>
        </details>
      </article>

      <article className={`source-card ${activeSources.includes('api') ? 'enabled' : ''}`}>
        <div className="source-card-head"><h3>API · bezahlt</h3><span className={`status-pill ${activeSource === 'api' ? 'running' : ''}`}>{activeSource === 'api' ? 'aktiv' : activeSources.includes('api') ? 'erlaubt' : 'nicht im Profil'}</span></div>
        <p>OpenAI-kompatible API als Qualitäts- oder Ausweichquelle. Es werden nur die konfigurierten Modelle und der Sitzungsschlüssel verwendet.</p>
        <label className="field">API-Basis<input value={settings.api_base} disabled={busy} onChange={event => update('api_base', event.target.value)} placeholder="https://api.openai.com/v1"/></label>
        <label className="field">API-Schlüssel (nur Sitzung)<input type="password" autoComplete="off" value={settings.remote_api_key || ''} placeholder={snapshot.sources?.remote_key_set ? 'Schlüssel gesetzt' : 'API-Schlüssel'} disabled={busy} onChange={event => update('remote_api_key', event.target.value)}/><small>Wird nicht gespeichert und nicht an das Projektjournal geschrieben.</small></label>
        <label className="field">API-Modell
          <div className="model-row">
            <select value={settings.api_model} disabled={busy} onChange={event => chooseModel('api', event.target.value)}>
              {modelOptions(models.api || [], settings.api_model)}
            </select>
            <button className="button secondary" type="button" disabled={busy} onClick={() => void loadModels('api')}>Laden</button>
          </div>
        </label>
        <small>{models.api?.length ? `${models.api.length} API-Modelle erkannt.` : 'Laden fragt den /models-Katalog ab; ein bereits gespeichertes Modell bleibt als Auswahl erhalten.'}</small>
      </article>
    </div>

    {error && <p className="field-error" role="alert">{error}</p>}
    {status && <p className="field-hint" role="status">{status}</p>}
    <div className="inline-actions">
      <button className="button primary" type="button" disabled={busy} onClick={() => void run(async () => { await saveSettings(); setStatus('Modellquellen gespeichert.'); })}>Quellen & Modelle speichern</button>
      <span className="field-hint">Änderungen an Vorauswahl und Modellen werden erst mit dem Speichern wirksam.</span>
    </div>
  </section>;
}
