import { IBM_Plex_Mono, Inter, Noto_Nastaliq_Urdu } from 'next/font/google'
import './globals.css'
import BrandMark from './BrandMark'
import HeaderTagline from './HeaderTagline'
import { LanguageProvider } from './LanguageProvider'
import LanguageSwitcher from './LanguageSwitcher'
import ThemeToggle from './ThemeToggle'
import { THEME_SCRIPT } from './theme'

// self-hosted at build time by next/font: the exported page makes no request to Google
const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600', '700'], variable: '--font-sans' })
const mono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['400', '500'], variable: '--font-mono' })
const urdu = Noto_Nastaliq_Urdu({ subsets: ['arabic'], weight: ['400', '600'], variable: '--font-urdu' })

export const metadata = {
  title: 'Hosted Hisab',
}

export default function RootLayout({ children }) {
  return (
    // data-theme is set by THEME_SCRIPT before React hydrates, so the server markup cannot match it
    <html lang="en" className={`${inter.variable} ${mono.variable} ${urdu.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <LanguageProvider>
          <header className="page site-header">
            <a className="brand-mark" href="/">
              <BrandMark size={30} radius={8} />
              <span className="brand-word">Hisab</span>
              <span className="brand-urdu urdu" dir="rtl">حساب</span>
            </a>
            <HeaderTagline />
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
