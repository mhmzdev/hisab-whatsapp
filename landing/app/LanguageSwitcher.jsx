'use client'

import { useLanguage } from './LanguageProvider'

const OPTIONS = [
  { value: 'en', label: 'EN', className: 'lang-seg' },
  { value: 'ur', label: 'اردو', className: 'lang-seg lang-seg-urdu urdu' },
]

export default function LanguageSwitcher() {
  const { lang, setLang } = useLanguage()

  return (
    <div className="lang-switch" dir="ltr">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => setLang(opt.value)}
          aria-pressed={lang === opt.value}
          className={opt.className}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
