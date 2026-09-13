// "Is someone signed in?" for the landing page, answered without Firebase. The portal writes the flag from
// onAuthStateChanged (set on a user, removed on sign-out); the landing page only reads it. A session that
// expires elsewhere leaves the flag behind until the next portal visit — the button then says "Go to
// portal" and the portal shows sign-in, which is the price of keeping Firebase off the landing bundle.
export const SIGNED_IN_KEY = 'hisab-signed-in'

export function readSignedIn() {
  try {
    return localStorage.getItem(SIGNED_IN_KEY) === '1'
  } catch {
    return false
  }
}
