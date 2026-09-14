'use client'

import { useEffect, useState } from 'react'
import { Monitor, Moon, Sun } from 'lucide-react'
import { useLanguage } from './LanguageProvider'
import { applyTheme, readTheme, THEME_KEY, THEMES } from './theme'

const ICON = { system: Monitor, light: Sun, dark: Moon }

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
  const Icon = ICON[choice]
  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`${t('theme_toggle_label')}: ${label}`}
      title={`${t('theme_toggle_label')}: ${label}`}
      className="theme-toggle"
    >
      <Icon size={15} strokeWidth={2} aria-hidden="true" />
    </button>
  )
}
