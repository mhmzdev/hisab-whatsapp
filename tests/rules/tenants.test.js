// firestore.rules, exercised as an attacker and as an owner against the Firestore emulator.
// This is the one part of #7 a phone run structurally cannot cover: testing with your own agent
// tests you as the owner, never as another uid. Run from the repo root with `make rules-test`,
// which boots the emulator (`firebase emulators:exec --only firestore`) around `npm test`.
const { test, before, after } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { initializeTestEnvironment, assertFails, assertSucceeds } = require('@firebase/rules-unit-testing')
const { doc, getDoc, setDoc, updateDoc, deleteDoc } = require('firebase/firestore')

const PROJECT = 'demo-hisab-rules'   // demo-* never touches a real Firebase project
const OWNER = 'uid-owner'
const OTHER = 'uid-other'
const SEALED = 'c2VhbGVkLWJveC1jaXBoZXJ0ZXh0'  // any base64; rules never inspect the ciphertext

let env

before(async () => {
  const [host, port] = (process.env.FIRESTORE_EMULATOR_HOST || 'localhost:8080').split(':')
  env = await initializeTestEnvironment({
    projectId: PROJECT,
    firestore: {
      rules: fs.readFileSync(path.join(__dirname, '..', '..', 'firestore.rules'), 'utf8'),
      host,
      port: Number(port),
    },
  })
})

after(async () => {
  if (env) await env.cleanup()
})

function clientDoc(overrides = {}) {
  return {
    agentName: 'Hisab',
    keyCiphertext: SEALED,
    nonce: '482913',
    nonceExpiresAt: Date.now() + 10 * 60 * 1000,
    createdAt: Date.now(),
    ...overrides,
  }
}

async function seedAsRunner(uid, data) {
  // the Admin SDK bypasses rules; withSecurityRulesDisabled is the emulator's stand-in for it
  await env.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), 'tenants', uid), data)
  })
}

test('an owner can create their own tenant with the client fields only', async () => {
  await env.clearFirestore()
  const db = env.authenticatedContext(OWNER).firestore()
  await assertSucceeds(setDoc(doc(db, 'tenants', OWNER), clientDoc()))
})

test('a signed-in client cannot set status on its own tenant document', async () => {
  await env.clearFirestore()
  const db = env.authenticatedContext(OWNER).firestore()
  await assertFails(setDoc(doc(db, 'tenants', OWNER), clientDoc({ status: 'connected' })))
  await assertSucceeds(setDoc(doc(db, 'tenants', OWNER), clientDoc()))
  await assertFails(updateDoc(doc(db, 'tenants', OWNER), { status: 'connected' }))
  await assertFails(updateDoc(doc(db, 'tenants', OWNER), { nonce: '111111', status: 'connected' }))
})

test('a signed-in client cannot set creatorId on its own tenant document', async () => {
  await env.clearFirestore()
  const db = env.authenticatedContext(OWNER).firestore()
  await assertFails(setDoc(doc(db, 'tenants', OWNER), clientDoc({ creatorId: '923001234567' })))
  await assertSucceeds(setDoc(doc(db, 'tenants', OWNER), clientDoc()))
  await assertFails(updateDoc(doc(db, 'tenants', OWNER), { creatorId: '923001234567' }))
})

test('a signed-in client cannot read or write another uid\'s document', async () => {
  await env.clearFirestore()
  await seedAsRunner(OTHER, { ...clientDoc(), status: 'connected', creatorId: '923001234567' })
  const db = env.authenticatedContext(OWNER).firestore()
  await assertFails(getDoc(doc(db, 'tenants', OTHER)))
  await assertFails(setDoc(doc(db, 'tenants', OTHER), clientDoc()))
  await assertFails(updateDoc(doc(db, 'tenants', OTHER), { nonce: '999999' }))
  await assertFails(deleteDoc(doc(db, 'tenants', OTHER)))
})

test('an owner can update agentName and keyCiphertext, and refresh the nonce, without disturbing runner fields', async () => {
  await env.clearFirestore()
  await seedAsRunner(OWNER, { ...clientDoc(), status: 'pending' })
  const db = env.authenticatedContext(OWNER).firestore()
  await assertSucceeds(updateDoc(doc(db, 'tenants', OWNER), { agentName: 'Ali Traders', keyCiphertext: SEALED + 'x' }))
  await assertSucceeds(updateDoc(doc(db, 'tenants', OWNER), { nonce: '135790', nonceExpiresAt: Date.now() + 600000 }))
  await assertSucceeds(getDoc(doc(db, 'tenants', OWNER)))
  await assertFails(deleteDoc(doc(db, 'tenants', OWNER)))
  // a signed-out client sees nothing at all
  await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(), 'tenants', OWNER)))
  // nothing outside tenants/ is reachable
  await assertFails(setDoc(doc(db, 'anything', OWNER), { a: 1 }))
})
