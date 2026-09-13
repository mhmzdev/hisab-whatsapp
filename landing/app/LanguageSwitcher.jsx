'use client'

import { useLanguage } from './LanguageProvider'

const OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'ur', label: 'اردو' },
]

export default function LanguageSwitcher() {
  const { lang, setLang } = useLanguage()

  return (
    <div style={{ display: 'flex', gap: 8 }}>
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => setLang(opt.value)}
          aria-pressed={lang === opt.value}
          style={{
            padding: '6px 12px',
            borderRadius: 999,
            border: `1px solid var(--line)`,
            background: lang === opt.value ? 'var(--brand)' : 'var(--surface)',
            color: lang === opt.value ? '#fff' : 'var(--text)',
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
