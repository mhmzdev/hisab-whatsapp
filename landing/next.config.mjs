// A static export. NEXT_PUBLIC_BASE_PATH serves it under a sub-path (GitHub Pages: /hisab); Next prefixes its own
// scripts, CSS, fonts and imported images, and app/paths.js prefixes our plain <a href>s. NEXT_DIST_DIR keeps a
// Pages build out of landing/out, which the emulators may be serving.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''

export default {
  output: 'export',
  trailingSlash: true,
  ...(basePath ? { basePath } : {}),
  ...(process.env.NEXT_DIST_DIR ? { distDir: process.env.NEXT_DIST_DIR } : {}),
}
