import { useEffect, useState } from 'react';
import { useI18n, tr } from './i18n';
type Suggestion = { id: string; title: string; category: string; description: string; tradeoff: string; acceptance: string };
type Info = { busy: boolean; phase: string; error: string; assistance: { suggestions: Suggestion[]; pending: { id: string; text: string; status: string; error?: string }[]; coverage?: { read: string[]; omitted: string[] } } };
export async function assistantApi<T>(url: string, data?: unknown): Promise<T> {
  const r = await fetch(url, { method: data === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', 'X-ToolForge-Request': '1' }, body: data === undefined ? undefined : JSON.stringify(data) });
  const v = await r.json();
  if (!r.ok) throw Error(v.detail || tr('Anfrage fehlgeschlagen', 'Request failed'));
  return v;
}
export function ModelChoice({ base, value, onChange, disabled }: { base: string; value: string; onChange: (v: string) => void; disabled: boolean }) {
  const { t } = useI18n();
  const [models, setModels] = useState<{ key: string }[]>([]), [error, setError] = useState('');
  return <div className="field"><label>{t('Modell für diese Assistenz', 'Model for this assistance')}<select aria-label={t('Assistenzmodell', 'Assistance model')} disabled={disabled} value={value} onChange={e => onChange(e.target.value)}><option value="">{t('Modell auswählen', 'Choose a model')}</option>{models.map(m => <option key={m.key}>{m.key}</option>)}</select></label><button className="button secondary" disabled={disabled} onClick={() => void assistantApi<{ models: { key: string }[]; judge: string }>(base + '/assistant/options', {}).then(r => { setModels(r.models); onChange(r.judge); setError(''); }).catch(e => setError(e.message))}>{t('Modelle laden & allgemeines Modell vorschlagen', 'Load models & suggest a general model')}</button><small>{t('Vorauswahl nach Modellfamilie; für einen gemessenen Vergleich den Vorabcheck nutzen. Vorheriges Arbeitsmodell wird anschließend wieder geladen.', 'Preselection by model family; use the preflight for a measured comparison. The previous working model is then loaded again.')}</small>{error && <p role="alert">{error}</p>}</div>;
}
export default function ImprovementPanel({ projectId }: { projectId: string }) {
  const { t } = useI18n();
  const base = `/api/projects/${projectId}/pilot`; const [info, setInfo] = useState<Info | null>(null), [text, setText] = useState(''), [model, setModel] = useState(''), [error, setError] = useState(''), [pending, setPending] = useState(false), [selected, setSelected] = useState<string[]>([]), [categories, setCategories] = useState(['architecture', 'code', 'features', 'ui', 'speed', 'tests']);
  async function refresh() { setInfo(await assistantApi<Info>(base)); }
  useEffect(() => { void refresh().catch(e => setError(e.message)); const id = setInterval(() => void refresh().catch(() => { }), 2200); return () => clearInterval(id); }, [projectId]);
  async function action(fn: () => Promise<unknown>) { setPending(true); setError(''); try { await fn(); await refresh(); } catch (e) { setError((e as Error).message); } finally { setPending(false); } }
  const categoryLabels: Record<string, string> = {
    architecture: t('Architektur', 'Architecture'), code: t('Codequalität', 'Code quality'),
    features: t('Funktionen', 'Features'), ui: t('Darstellung & Bedienung', 'Appearance & usability'),
    speed: t('Geschwindigkeit', 'Speed'), tests: t('Tests & Zuverlässigkeit', 'Tests & reliability'),
    security: t('Sicherheit & Datenhaltung', 'Security & data handling')
  };
  const queueLabels: Record<string, string> = {
    queued: t('Vorgemerkt', 'Queued'), planning: t('Wird geplant', 'Planning'),
    applied: t('Eingeplant', 'Scheduled'), error: t('Fehler', 'Error')
  };
  return <section className="panel assistance-panel"><h2>{t('Verbesserungen und Erweiterungen', 'Improvements and extensions')}</h2><p>{t('Bestätigte Erweiterungen ergänzen den bestehenden Plan. Während der Entwicklung werden sie vor dem nächsten Durchlauf eingeplant; bereits geprüfte Aufgaben bleiben erhalten.', 'Confirmed extensions add to the existing plan. During development they are scheduled before the next run; already verified tasks are preserved.')}</p>{error && <p role="alert" className="field-error">{error}</p>}
    <label className="field">{t('Was soll ergänzt oder verbessert werden?', 'What should be added or improved?')}<textarea rows={4} value={text} onChange={e => setText(e.target.value)} /></label><button className="button primary" disabled={pending || !text.trim()} onClick={() => void action(async () => { await assistantApi(base + '/improvements/add', { text }); setText(''); })}>{t('Erweiterung zur Planung hinzufügen', 'Add extension to planning')}</button>
    <h3>{t('Verbesserungen vorschlagen lassen', 'Suggest improvements')}</h3><div className="permission-list">{Object.entries(categoryLabels).map(([id, label]) => <label className="check-label" key={id}><input type="checkbox" checked={categories.includes(id)} onChange={e => setCategories(e.target.checked ? [...categories, id] : categories.filter(x => x !== id))} />{label}</label>)}</div>
    <ModelChoice base={base} value={model} onChange={setModel} disabled={pending || !!info?.busy} /><button className="button secondary" disabled={pending || !!info?.busy || !model || !categories.length} onClick={() => void action(() => assistantApi(base + '/improvements/suggest', { model, categories }))}>{t('Projekt analysieren & Vorschläge erstellen', 'Analyze project & create suggestions')}</button>
    <p role="status">{info?.phase}</p>{info?.error && <p role="alert">{info.error}</p>}{info?.assistance.coverage && <details><summary>{t(`Umfang der Analyse: ${info.assistance.coverage.read.length} Dateien ausschnittweise gelesen`, `Analysis scope: ${info.assistance.coverage.read.length} files read in excerpts`)}</summary><p>{t('Gelesen:', 'Read:')} {info.assistance.coverage.read.join(', ')}</p><p>{t('Nicht vollständig gelesen:', 'Not read in full:')} {info.assistance.coverage.omitted.join(', ') || t('Keine weiteren Dateien in der Übersicht', 'No further files in the overview')}</p></details>}
    {info?.assistance.suggestions.map(s => <article className="panel" key={s.id}><label className="check-label"><input type="checkbox" checked={selected.includes(s.id)} onChange={e => setSelected(e.target.checked ? [...selected, s.id] : selected.filter(x => x !== s.id))} /><strong>{s.title}</strong></label><p>{s.description}</p><p><strong>{t('Aufwand/Risiko:', 'Effort/risk:')}</strong> {s.tradeoff}</p><p><strong>{t('Abnahme:', 'Acceptance:')}</strong> {s.acceptance}</p></article>)}{!!info?.assistance.suggestions.length && <button className="button primary" disabled={pending || !selected.length} onClick={() => void action(async () => { await assistantApi(base + '/improvements/add', { selected }); setSelected([]); })}>{t('Ausgewählte Vorschläge bestätigen & einplanen', 'Confirm & schedule selected suggestions')}</button>}
    {!!info?.assistance.pending.length && <><h3>{t('Erweiterungsaufträge', 'Extension requests')}</h3>{info.assistance.pending.map(r => <details key={r.id}><summary>{queueLabels[r.status] || r.status} · {r.text.slice(0, 120)}</summary><p>{r.text}</p>{r.error && <p role="alert">{r.error}</p>}</details>)}</>}
  </section>;
}
