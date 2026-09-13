// Theme choice per browser: 'system' | 'light' | 'dark' in localStorage, applied as <html data-theme="light|dark">.
// THEME_SCRIPT runs inline in <head> before first paint (layout.jsx), so a reload never flashes the other theme;
// ThemeToggle.jsx uses applyTheme for every later change. Keep the two resolutions identical.
export const THEME_KEY = 'hisab-theme'
export const THEMES = ['system', 'light', 'dark']

export const THEME_SCRIPT = `(function(){try{var c=localStorage.getItem('${THEME_KEY}')}catch(e){}
var d=c==='dark'||(c!=='light'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);
document.documentElement.setAttribute('data-theme',d?'dark':'light')})()`

export function readTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY)
    return THEMES.includes(saved) ? saved : 'system'
  } catch {
    return 'system'
  }
}

export function applyTheme(choice) {
  const dark = choice === 'dark' || (choice !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
}
