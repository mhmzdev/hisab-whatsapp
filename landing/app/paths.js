// Plain <a href="/…"> is not rewritten by Next's basePath (only next/link is): every root-relative link on the page
// goes through withBase, so a build under /hisab links to /hisab/#pricing, not the site root.
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || ''

export const withBase = (path) => `${BASE_PATH}${path}`
