// Firebase for the portal route only: phone auth + the tenant document. Configured from
// NEXT_PUBLIC_FIREBASE_* at build time (a static export has no server); NEXT_PUBLIC_USE_EMULATORS=1
// points auth and Firestore at the local Emulator Suite (firebase.json ports). Nothing here is a
// secret — a Firebase web config is public by design, and the runner's PUBLIC key is the only key
// the browser ever sees (runner/keygen.py prints it labelled "safe to embed").
import { getApps, initializeApp } from 'firebase/app'
import { connectAuthEmulator, getAuth } from 'firebase/auth'
import { connectFirestoreEmulator, getFirestore } from 'firebase/firestore'

export const USE_EMULATORS = process.env.NEXT_PUBLIC_USE_EMULATORS === '1'
export const RUNNER_PUBLIC_KEY = process.env.NEXT_PUBLIC_RUNNER_PUBLIC_KEY || ''

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || (USE_EMULATORS ? 'demo-api-key' : ''),
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || '',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || (USE_EMULATORS ? 'demo-hisab' : ''),
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '',
}

let cached = null

export function firebase() {
  if (cached) return cached
  const app = getApps()[0] || initializeApp(config)
  const auth = getAuth(app)
  const db = getFirestore(app)
  if (USE_EMULATORS && !auth.emulatorConfig) {
    const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
    connectAuthEmulator(auth, `http://${host}:9099`, { disableWarnings: true })
    connectFirestoreEmulator(db, host, 8080)
    // the Auth emulator never verifies reCAPTCHA; the mock verifier keeps the invisible widget out of the DOM
    auth.settings.appVerificationDisabledForTesting = true
  }
  cached = { app, auth, db }
  return cached
}
