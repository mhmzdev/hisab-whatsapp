'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import strings from '@/content/strings.json'

const STORAGE_KEY = 'hisab-lang'

const LanguageContext = createContext({ lang: 'en', setLang: () => {}, t: (key) => key })

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState('en')

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      // the page speaks en and ur only; any other saved value (an old Roman Urdu choice) stays on the English default
      if (saved === 'en' || saved === 'ur') {
        setLangState(saved)
      }
    } catch {}
  }, [])

  function setLang(next) {
    setLangState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {}
  }

  function t(key) {
    const entry = strings[key]
    if (!entry) return key
    return entry[lang] || entry.en || key
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      <div lang={lang === 'ur' ? 'ur' : 'en'} dir={lang === 'ur' ? 'rtl' : 'ltr'} className={lang === 'ur' ? 'urdu' : ''}>
        {children}
      </div>
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
