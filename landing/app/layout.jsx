import { IBM_Plex_Mono, Inter, Noto_Nastaliq_Urdu } from 'next/font/google'
import localFont from 'next/font/local'
import './globals.css'
import { LanguageProvider } from './LanguageProvider'
import SiteNav from './SiteNav'
import { THEME_SCRIPT } from './theme'
import favicon from '@/assets/hisab_light_64.png'
import touchIcon from '@/assets/hisab_light_180.png'

// self-hosted at build time by next/font: the exported page makes no request to Google
const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600', '700'], variable: '--font-sans' })
const mono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['400', '500'], variable: '--font-mono' })
const urdu = Noto_Nastaliq_Urdu({ subsets: ['arabic'], weight: ['400', '600'], variable: '--font-urdu' })
// Jameel Noori Nastaleeq is ~4.7 MB even as a subset woff2, so it is never preloaded and only the Urdu page
// uses it (globals.css --urdu-face): an English visitor's few Urdu words stay in Noto and never fetch it
// Noori draws smaller than Noto at the same font-size; size-adjust brings it up to the page's reading size
const noori = localFont({
  src: '../assets/noori-nastaleeq.woff2',
  variable: '--font-noori',
  display: 'swap',
  preload: false,
  declarations: [{ prop: 'size-adjust', value: '130%' }],
})

export const metadata = {
  title: 'Hosted Hisab',
  // the light mark, downscaled from assets/hisab_light.png (512 px, 148 KB): 64 px for the tab, 180 px for iOS home
  // screens. An imported image carries the base path (/hisab on GitHub Pages).
  icons: { icon: { url: favicon.src, type: 'image/png', sizes: '64x64' }, apple: { url: touchIcon.src, sizes: '180x180' } },
}

export default function RootLayout({ children }) {
  return (
    // data-theme is set by THEME_SCRIPT before React hydrates, so the server markup cannot match it
    <html lang="en" className={`${inter.variable} ${mono.variable} ${urdu.variable} ${noori.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <LanguageProvider>
          <SiteNav />
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}
