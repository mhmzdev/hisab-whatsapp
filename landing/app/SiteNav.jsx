'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import BrandMark from './BrandMark'
import { HOSTED } from './hosted'
import { useLanguage } from './LanguageProvider'
import LanguageSwitcher from './LanguageSwitcher'
import { readSignedIn } from './signedIn'
import ThemeToggle from './ThemeToggle'

// section anchors on the landing page (page.jsx ids); the portal header shows only the brand and the controls
const LINKS = [
  { id: 'ways', key: 'nav_features' },
  { id: 'books', key: 'nav_ledger' },
  { id: 'how', key: 'nav_setup' },
  { id: 'shop', key: 'nav_shop' },
  { id: 'pricing', key: 'nav_pricing' },
]

export default function SiteNav() {
  const { t } = useLanguage()
  const onLanding = !usePathname()?.startsWith('/portal')
  const [signedIn, setSignedIn] = useState(false)
  useEffect(() => setSignedIn(readSignedIn()), [])

  return (
    <header className="site-nav">
      <div className="site-nav-inner">
        <a className="brand-mark" href="/">
          <BrandMark size={28} radius={8} />
          <span className="brand-word">Hisab</span>
          <span className="brand-urdu urdu" dir="rtl">حساب</span>
        </a>
        {onLanding && (
          <nav className="site-nav-links">
            {LINKS.map(({ id, key }) => (
              <a key={id} href={`/#${id}`}>{t(key)}</a>
            ))}
          </nav>
        )}
        <div className="header-controls">
          <LanguageSwitcher />
          <ThemeToggle />
          {onLanding && HOSTED && (
            <a className="site-nav-cta" href={signedIn ? '/portal/' : '/#pricing'}>
              {signedIn ? t('cta_go_to_portal') : t('nav_get_started')}
            </a>
          )}
          {onLanding && !HOSTED && (
            <a className="site-nav-cta" href="https://github.com/mhmzdev/hisab-whatsapp#run-it-for-real" target="_blank" rel="noopener noreferrer">
              {t('hero_cta_secondary')}
            </a>
          )}
        </div>
      </div>
    </header>
  )
}
