import './globals.css'
import { LanguageProvider } from './LanguageProvider'
import LanguageSwitcher from './LanguageSwitcher'

export const metadata = {
  title: 'Hosted Hisab',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <LanguageProvider>
          <header className="page site-header">
            <div className="brand-mark">
              <span className="brand-word">Hisab</span>
              <span className="brand-urdu urdu" dir="rtl">حساب</span>
            </div>
            <LanguageSwitcher />
          </header>
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}
