import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export type Lang = 'de' | 'en';

type I18nValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  toggleLang: () => void;
  t: (de: string, en: string) => string;
  locale: string;
};

const I18nContext = createContext<I18nValue>({
  lang: 'de',
  setLang: () => undefined,
  toggleLang: () => undefined,
  t: (de) => de,
  locale: 'de-DE'
});

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem('toolforge-language');
    if (saved === 'de' || saved === 'en') return saved;
    return navigator.language.toLowerCase().startsWith('de') ? 'de' : 'en';
  } catch {
    return 'de';
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(initialLang);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = lang === 'de' ? 'ToolForge — Deine lokale Workbench' : 'ToolForge — Your local workbench';
    const description = document.querySelector('meta[name="description"]');
    if (description) {
      description.setAttribute('content', lang === 'de'
        ? 'ToolForge: deine lokale Workbench für eigene Softwaretools.'
        : 'ToolForge: your local workbench for custom software tools.');
    }
    try { localStorage.setItem('toolforge-language', lang); } catch { /* storage may be unavailable */ }
  }, [lang]);
  const value: I18nValue = {
    lang,
    setLang,
    toggleLang: () => setLang(current => current === 'de' ? 'en' : 'de'),
    t: (de, en) => lang === 'de' ? de : en,
    locale: lang === 'de' ? 'de-DE' : 'en-US'
  };
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

/** Translation for helpers outside React, based on the current document language. */
export function tr(de: string, en: string) {
  return document.documentElement.lang === 'en' ? en : de;
}

type Translate = (de: string, en: string) => string;

/** Shared labels for the three model sources. */
export function sourceName(key: string, t: Translate) {
  if (key === 'local') return t('Lokal (LM Studio)', 'Local (LM Studio)');
  if (key === 'free') return 'OpenCode Free';
  if (key === 'api') return t('API (bezahlt)', 'API (paid)');
  return key;
}

/** Shared labels for source presets. */
export function modeName(key: string, t: Translate) {
  const values: Record<string, [string, string]> = {
    local: ['Nur Lokal', 'Local only'], free: ['Nur Free', 'Free only'], api: ['Nur API', 'API only'],
    free_local: ['Free & Lokal', 'Free & local'], local_api: ['Lokal & API', 'Local & API'],
    free_api: ['Free & API', 'Free & API']
  };
  const pair = values[key];
  return pair ? t(pair[0], pair[1]) : key;
}

/** Shared labels for source preferences. */
export function preferenceName(key: string, t: Translate) {
  const values: Record<string, [string, string]> = {
    max_quality: ['MAX Quality', 'MAX quality'],
    balanced: ['Preis/Leistung', 'Price/performance'],
    cost_saving: ['Kostensparend', 'Cost saving']
  };
  const pair = values[key];
  return pair ? t(pair[0], pair[1]) : key;
}

/** Compact `EN | DE` switch used beside the theme and volume controls. */
export function LanguageSwitch() {
  const { lang, setLang, t } = useI18n();
  return <div className="language-switch" role="group" aria-label={t('Sprache', 'Language')}>
    <button type="button" className={lang === 'en' ? 'active' : ''} aria-pressed={lang === 'en'}
      title={t('Englische Oberfläche', 'English interface')} onClick={() => setLang('en')}>EN</button>
    <span aria-hidden="true">|</span>
    <button type="button" className={lang === 'de' ? 'active' : ''} aria-pressed={lang === 'de'}
      title={t('Deutsche Oberfläche', 'German interface')} onClick={() => setLang('de')}>DE</button>
  </div>;
}
