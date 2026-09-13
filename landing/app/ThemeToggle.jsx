'use client'

import { useEffect, useState } from 'react'
import { useLanguage } from './LanguageProvider'
import { applyTheme, readTheme, THEME_KEY, THEMES } from './theme'

const ICON = { system: '◐', light: '☀', dark: '☾' }

export default function ThemeToggle() {
  const { t } = useLanguage()
  const [choice, setChoice] = useState('system')

  useEffect(() => {
    setChoice(readTheme())
  }, [])

  // on System, follow the device when it switches (sunset, a quick-settings toggle) without a reload
  useEffect(() => {
    if (choice !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => applyTheme('system')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [choice])

  function cycle() {
    const next = THEMES[(THEMES.indexOf(choice) + 1) % THEMES.length]
    setChoice(next)
    applyTheme(next)
    try {
      localStorage.setItem(THEME_KEY, next)
    } catch {}
  }

  const label = t(`theme_${choice}`)
  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`${t('theme_toggle_label')}: ${label}`}
      title={`${t('theme_toggle_label')}: ${label}`}
      style={{
        padding: '6px 12px',
        borderRadius: 999,
        border: `1px solid var(--line)`,
        background: 'var(--surface)',
        color: 'var(--text)',
        cursor: 'pointer',
        fontSize: 14,
      }}
    >
      <span aria-hidden="true">{ICON[choice]}</span> {label}
    </button>
  )
}
