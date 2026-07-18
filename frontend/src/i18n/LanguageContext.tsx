import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { Lang } from './translations';
import { translate as t } from './translations';

interface LangContextType {
  lang: Lang;
  toggleLang: () => void;
  tr: (key: string) => string;
}

const LangContext = createContext<LangContextType>({
  lang: 'en',
  toggleLang: () => {},
  tr: (key: string) => key,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  // Auto-detect from browser
  const [lang, setLang] = useState<Lang>(() => {
    if (typeof navigator !== 'undefined' && navigator.language.startsWith('zh')) {
      return 'zh';
    }
    return 'en';
  });

  const toggleLang = useCallback(() => {
    setLang((prev) => (prev === 'en' ? 'zh' : 'en'));
  }, []);

  const tr = useCallback((key: string) => t(lang, key), [lang]);

  return (
    <LangContext.Provider value={{ lang, toggleLang, tr }}>
      {children}
    </LangContext.Provider>
  );
}

export function useTr() {
  return useContext(LangContext);
}
