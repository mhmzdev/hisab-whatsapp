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
          <header className="page" style={{ display: 'flex', justifyContent: 'flex-end', paddingBlock: 16 }}>
            <LanguageSwitcher />
          </header>
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}
