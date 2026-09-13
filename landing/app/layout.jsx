import './globals.css'
import { LanguageProvider } from './LanguageProvider'
import LanguageSwitcher from './LanguageSwitcher'
import ThemeToggle from './ThemeToggle'
import { THEME_SCRIPT } from './theme'

export const metadata = {
  title: 'Hosted Hisab',
}

export default function RootLayout({ children }) {
  return (
    // data-theme is set by THEME_SCRIPT before React hydrates, so the server markup cannot match it
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <LanguageProvider>
          <header className="page site-header">
            <a className="brand-mark" href="/">
              <span className="brand-word">Hisab</span>
              <span className="brand-urdu urdu" dir="rtl">حساب</span>
            </a>
            <div className="header-controls">
              <LanguageSwitcher />
              <ThemeToggle />
            </div>
          </header>
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}
