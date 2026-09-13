'use client'

import { useEffect, useRef, useState } from 'react'
import { onAuthStateChanged, RecaptchaVerifier, signInWithPhoneNumber, signOut } from 'firebase/auth'
import { doc, onSnapshot, setDoc, updateDoc } from 'firebase/firestore'
import { useLanguage } from '../LanguageProvider'
import { PLAN } from '@/content/mock.js'
import { firebase, RUNNER_PUBLIC_KEY } from './firebase'
import { generateNonce, NONCE_TTL_MS, sealKey } from './crypto'
import styles from './portal.module.css'

// The screen is derived from two facts, never chosen by hand: is someone signed in, and what does
// their own tenants/{uid} document say. The runner owns `status`; the browser can only write the
// client fields (firestore.rules), so "connected" on this page always means the runner said so.
function screenFor(user, tenant, phase) {
  if (phase === 'reconnect') return tenant?.status === 'revoked' ? 'connect' : screenFor(user, tenant, null)
  if (phase) return phase                       // signin-code is a UI-only transition
  if (!user) return 'signin'
  if (!tenant) return 'connect'
  if (tenant.status === 'connected') return 'connected'
  if (tenant.status === 'revoked') return 'revoked'
  if (tenant.status === 'error') return 'connect'
  return 'check'                                // pending, or written by the client and not yet accepted
}

function errorKey(code) {
  // every lastError code the runner can emit has a portal string — tests/check_landing.py enforces it
  return code ? `portal_error_${code}` : null
}

function SigninState({ t, onSent, setError }) {
  const [digits, setDigits] = useState('')
  const [busy, setBusy] = useState(false)
  const verifierRef = useRef(null)

  async function send() {
    const local = digits.replace(/\D/g, '')
    if (local.length < 9) return setError('portal_signin_error')
    setBusy(true)
    setError(null)
    try {
      const { auth } = firebase()
      if (!verifierRef.current) {
        verifierRef.current = new RecaptchaVerifier(auth, 'recaptcha-anchor', { size: 'invisible' })
      }
      const phone = `+92${local}`
      const confirmation = await signInWithPhoneNumber(auth, phone, verifierRef.current)
      onSent(phone, confirmation)
    } catch (e) {
      console.error('signInWithPhoneNumber', e)
      if (verifierRef.current) { try { verifierRef.current.clear() } catch {} ; verifierRef.current = null }
      setError('portal_signin_error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h1>{t('portal_signin_title')}</h1>
      <div className={styles.phoneGroup} dir="ltr">
        <span className={styles.phonePrefix}>+92</span>
        <input
          type="tel"
          name="phone"
          autoComplete="tel-national"
          placeholder="300 000 0000"
          className={styles.phoneInput}
          value={digits}
          onChange={(e) => setDigits(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') send() }}
        />
      </div>
      <p className={styles.note}>{t('portal_signin_helper')}</p>
      <button type="button" className={styles.button} disabled={busy} onClick={send}>
        {busy ? t('portal_working') : t('portal_signin_button')}
      </button>
      <p className={styles.fine}>{t('portal_signin_fine')}</p>
      <div id="recaptcha-anchor" />
    </>
  )
}

function SigninCodeState({ t, phone, confirmation, onBack, setError }) {
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [busy, setBusy] = useState(false)
  const refs = useRef([])

  function onDigit(i, e) {
    const raw = (e.target.value || '').replace(/[^0-9]/g, '')
    if (raw.length > 1) {
      // a pasted code fills every box
      const next = otp.slice()
      for (let k = 0; k < 6; k++) next[k] = raw[k] || ''
      setOtp(next)
      const last = Math.min(raw.length, 6) - 1
      if (refs.current[last]) refs.current[last].focus()
      return
    }
    const next = otp.slice()
    next[i] = raw
    setOtp(next)
    if (raw && i < 5 && refs.current[i + 1]) refs.current[i + 1].focus()
  }

  function onKey(i, e) {
    if (e.key === 'Backspace' && !otp[i] && i > 0 && refs.current[i - 1]) refs.current[i - 1].focus()
    if (e.key === 'Enter') confirm()
  }

  async function confirm() {
    const code = otp.join('')
    if (code.length !== 6) return setError('portal_signin_code_error')
    setBusy(true)
    setError(null)
    try {
      await confirmation.confirm(code)     // onAuthStateChanged takes it from here
    } catch (e) {
      console.error('confirm', e)
      setError('portal_signin_code_error')
      setBusy(false)
    }
  }

  const masked = `${phone.slice(0, 3)} ${phone.slice(3, 4)}•• ••• ${phone.slice(-4)}`   // +92 3•• ••• 4567

  return (
    <>
      <h1>{t('portal_signin_code_title')}</h1>
      <div className={styles.otpRow} dir="ltr">
        {otp.map((v, i) => (
          <input
            key={i}
            ref={(el) => { refs.current[i] = el }}
            inputMode="numeric"
            autoComplete={i === 0 ? 'one-time-code' : 'off'}
            value={v}
            onChange={(e) => onDigit(i, e)}
            onKeyDown={(e) => onKey(i, e)}
            className={styles.otpBox}
          />
        ))}
      </div>
      <p className={styles.note}>{t('portal_signin_code_sent').replace('{phone}', masked)}</p>
      <button type="button" className={styles.button} disabled={busy} onClick={confirm}>
        {busy ? t('portal_working') : t('portal_signin_code_button')}
      </button>
      <button type="button" className={styles.linkButton} onClick={onBack}>{t('portal_signin_code_wrong_number')}</button>
    </>
  )
}

function ConnectState({ t, user, tenant, setError }) {
  const [agentName, setAgentName] = useState(tenant?.agentName || '')
  const [apiKey, setApiKey] = useState('')
  const [busy, setBusy] = useState(false)

  function pasteKey() {
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText().then((txt) => setApiKey((txt || '').trim())).catch(() => {})
    }
  }

  async function connect() {
    const key = apiKey.trim()
    if (!key) return setError('portal_connect_key_missing')
    if (!RUNNER_PUBLIC_KEY) return setError('portal_error_unknown')
    setBusy(true)
    setError(null)
    try {
      const keyCiphertext = await sealKey(key, RUNNER_PUBLIC_KEY)
      const { db } = firebase()
      const now = Date.now()
      // exactly the five client fields — never status or creatorId, which firestore.rules rejects
      await setDoc(doc(db, 'tenants', user.uid), {
        agentName: agentName.trim() || 'Hisab',
        keyCiphertext,
        nonce: generateNonce(),
        nonceExpiresAt: now + NONCE_TTL_MS,
        createdAt: now,
      }, { merge: true })
      setApiKey('')                            // the plaintext leaves memory as soon as it is sealed
    } catch (e) {
      console.error('connect', e)
      setError('portal_error_unknown')
    } finally {
      setBusy(false)
    }
  }

  const steps = [t('portal_connect_step1'), t('portal_connect_step2'), t('portal_connect_step3'), t('portal_connect_step4')]

  return (
    <>
      <h1>{t('portal_connect_title')}</h1>
      <p className={styles.subtitle}>{t('portal_connect_subtitle')}</p>
      <ol className={styles.stepsList}>
        {steps.map((step, i) => (
          <li key={i}>
            <span className={styles.stepNum}>{i + 1}</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <label className={styles.field}>
        <span>{t('portal_connect_name_label')}</span>
        <input type="text" name="agent-name" autoComplete="off" placeholder="Hisab" value={agentName} onChange={(e) => setAgentName(e.target.value)} />
      </label>
      <label className={styles.field}>
        <span>{t('portal_connect_key_label')}</span>
        <div className={styles.keyRow}>
          <input
            dir="ltr"
            type="password"
            name="api-key"
            autoComplete="off"
            placeholder="••••••••••••••••"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <button type="button" className={styles.pasteButton} onClick={pasteKey}>{t('portal_connect_paste_button')}</button>
        </div>
      </label>
      <p className={styles.note}>{t('portal_connect_key_note')}</p>
      <button type="button" className={styles.button} disabled={busy} onClick={connect}>
        {busy ? t('portal_working') : t('portal_connect_button')}
      </button>
      <p className={styles.note}>{t('portal_connect_custody_note')}</p>
    </>
  )
}

function CheckState({ t, user, tenant, setError }) {
  const [copied, setCopied] = useState(false)
  const [now, setNow] = useState(Date.now())
  const nonce = tenant?.nonce || ''
  const command = `verify ${nonce}`
  const expired = !!tenant?.nonceExpiresAt && now > tenant.nonceExpiresAt

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(id)
  }, [])

  function copy() {
    try {
      navigator.clipboard.writeText(command)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  async function newCode() {
    setError(null)
    try {
      const { db } = firebase()
      await updateDoc(doc(db, 'tenants', user.uid), { nonce: generateNonce(), nonceExpiresAt: Date.now() + NONCE_TTL_MS })
    } catch (e) {
      console.error('newCode', e)
      setError('portal_error_unknown')
    }
  }

  return (
    <>
      <h1>{t('portal_verify_title')}</h1>
      <p>{t('portal_verify_instruction').replace('{nonce}', nonce)}</p>
      <div className={styles.code} dir="ltr">{command}</div>
      <div className={styles.copyRow}>
        <button type="button" onClick={copy}>{copied ? '✓' : t('portal_verify_copy')}</button>
        <button type="button" onClick={newCode}>{t('portal_verify_new_code')}</button>
      </div>
      {expired ? (
        <p className={styles.errorText}>{t('portal_verify_expired')}</p>
      ) : (
        <>
          <div className={styles.waiting}>
            <span className={styles.dot} />
            {t('portal_verify_waiting')}
          </div>
          <p className={styles.expiry}>{t('portal_verify_expiry')}</p>
        </>
      )}
      <p className={styles.note}>{t('portal_verify_after_caption')}</p>
    </>
  )
}

function formatDate(ms) {
  if (!ms) return '—'
  try {
    return new Date(ms).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })
  } catch {
    return '—'
  }
}

// "12 minutes ago" in the page language, English or Urdu.
function relative(ms, lang, now) {
  if (!ms) return null
  const diff = Math.round((ms - now) / 1000)   // negative = in the past
  const abs = Math.abs(diff)
  const [value, unit] = abs < 60 ? [diff, 'second'] : abs < 3600 ? [Math.round(diff / 60), 'minute']
    : abs < 86400 ? [Math.round(diff / 3600), 'hour'] : [Math.round(diff / 86400), 'day']
  try {
    return new Intl.RelativeTimeFormat(lang === 'ur' ? 'ur' : 'en', { numeric: 'auto' }).format(value, unit)
  } catch {
    return new Date(ms).toLocaleString()
  }
}

function ConnectedState({ t, lang, user, tenant, setError }) {
  const [askingRevoke, setAskingRevoke] = useState(false)
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(id)
  }, [])

  // every row is the runner's: it computes these from the worker's own files and writes them to the
  // tenant document (runner/activity.py); the browser never sees an entry, an amount or a description
  const revoking = !!tenant?.revokeRequestedAt
  const used = tenant?.usedThisMonth ?? 0
  const limit = tenant?.quotaLimit ?? null
  const quotaPct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const language = tenant?.language ? t(`portal_lang_${tenant.language}`) : t('portal_connected_not_yet')

  async function confirmRevoke() {
    setError(null)
    try {
      const { db } = firebase()
      await updateDoc(doc(db, 'tenants', user.uid), { revokeRequestedAt: Date.now() })
    } catch (e) {
      console.error('revoke', e)
      setError('portal_error_unknown')
    }
  }

  return (
    <>
      <h1>{t('portal_connected_title')}</h1>
      <div className={styles.rows}>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connect_name_label')}</span>
          <span>{tenant?.agentName || 'Hisab'}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_since_label')}</span>
          <span>{formatDate(tenant?.connectedAt)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_activity_label')}</span>
          <span>{relative(tenant?.lastSeenAt, lang, now) || t('portal_connected_not_yet')}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_entries_label')}</span>
          <span>{tenant?.entriesThisMonth ?? 0}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_language_label')}</span>
          <span>{language}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_plan_label')}</span>
          <span>{PLAN}</span>
        </div>
      </div>

      {limit ? (
        <div className={styles.quotaBlock}>
          <div className={styles.quotaHeader}>
            <span>{t('portal_connected_quota_label')}</span>
            <span dir="ltr">{used} / {limit}</span>
          </div>
          <div className={styles.quotaTrack}>
            <span className={styles.quotaFill} style={{ width: `${quotaPct}%` }} />
          </div>
        </div>
      ) : null}

      <p className={styles.hint}>
        {t('portal_connected_export_hint_pre')} <code>export-ledger</code> {t('portal_connected_export_hint_post')}
      </p>
      <p className={styles.note}>{t('portal_connected_export_hint_sub')}</p>

      {revoking ? (
        <div className={styles.waiting}>
          <span className={styles.dot} />
          {t('portal_connected_revoking')}
        </div>
      ) : askingRevoke ? (
        <div className={styles.confirmBox}>
          <p>{t('portal_connected_revoke_confirm_text')}</p>
          <div className={styles.confirmRow}>
            <button type="button" className={styles.buttonDangerSolid} onClick={confirmRevoke}>{t('portal_connected_revoke_confirm_yes')}</button>
            <button type="button" className={styles.buttonOutline} onClick={() => setAskingRevoke(false)}>{t('portal_connected_revoke_confirm_no')}</button>
          </div>
        </div>
      ) : (
        <button type="button" className={styles.buttonDanger} onClick={() => setAskingRevoke(true)}>{t('portal_connected_revoke_button')}</button>
      )}
    </>
  )
}

function RevokedState({ t, tenant, onReconnect }) {
  return (
    <>
      <h1>{t('portal_revoked_title')}{tenant?.agentName ? ` · ${tenant.agentName}` : ''}</h1>
      <p>{t('portal_revoked_body')}</p>
      <p className={styles.note}>{t('portal_revoked_retention')}</p>
      <button type="button" className={styles.button} onClick={onReconnect}>{t('portal_revoked_reconnect_button')}</button>
      <p className={styles.note}>{t('portal_revoked_muted')}</p>
    </>
  )
}

// a modal, not inline: it covers the page, Escape or a tap on the backdrop cancels, and focus starts on
// the safe choice so Enter on a stray open keeps the session
function SignOutDialog({ t, onConfirm, onCancel }) {
  const cancelRef = useRef(null)

  useEffect(() => {
    if (cancelRef.current) cancelRef.current.focus()
  }, [])

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div className={styles.modalBackdrop} onClick={onCancel}>
      <div className={styles.modal} role="alertdialog" aria-modal="true" aria-labelledby="signout-title"
        aria-describedby="signout-text" onClick={(e) => e.stopPropagation()}>
        <h2 id="signout-title">{t('portal_signout_confirm_title')}</h2>
        <p id="signout-text">{t('portal_signout_confirm_text')}</p>
        <div className={styles.confirmRow}>
          <button type="button" ref={cancelRef} className={styles.buttonOutline} onClick={onCancel}>{t('portal_signout_confirm_no')}</button>
          <button type="button" className={styles.buttonDangerSolid} onClick={onConfirm}>{t('portal_signout_confirm_yes')}</button>
        </div>
      </div>
    </div>
  )
}

export default function Portal() {
  const { t, lang } = useLanguage()
  const [user, setUser] = useState(undefined)       // undefined = auth not resolved yet
  const [tenant, setTenant] = useState(undefined)   // undefined = no subscription yet, null = no document
  const [phase, setPhase] = useState(null)          // 'signin-code' while an OTP is pending, else null
  const [pending, setPending] = useState(null)      // { phone, confirmation }
  const [error, setError] = useState(null)          // a strings.json key, rendered through t()
  const [askingSignOut, setAskingSignOut] = useState(false)

  useEffect(() => {
    const { auth } = firebase()
    return onAuthStateChanged(auth, (u) => {
      setUser(u || null)
      setPhase(null)
      setPending(null)
      setAskingSignOut(false)
      if (!u) setTenant(undefined)
    })
  }, [])

  useEffect(() => {
    if (!user) return undefined
    const { db } = firebase()
    return onSnapshot(doc(db, 'tenants', user.uid), (snap) => {
      const data = snap.exists() ? snap.data() : null
      setTenant(data)
      // the reconnect form is a UI-only phase over a revoked document; the runner's admission
      // (status → pending) is what moves on from it
      if (data?.status !== 'revoked') setPhase((p) => (p === 'reconnect' ? null : p))
    }, (e) => {
      console.error('tenant snapshot', e)
      setError('portal_error_unknown')
    })
  }, [user])

  function onSent(phone, confirmation) {
    setPending({ phone, confirmation })
    setPhase('signin-code')
  }

  // signing back in costs an SMS code, so a stray tap on the eyebrow button only asks
  async function confirmSignOut() {
    setAskingSignOut(false)
    setError(null)
    try {
      await signOut(firebase().auth)
    } catch (e) {
      console.error('signOut', e)
      setError('portal_error_unknown')
    }
  }

  const resolved = user !== undefined && (user === null || tenant !== undefined)
  const screen = resolved ? screenFor(user, tenant, phase) : 'loading'
  const bannerKey = error || (screen === 'connect' && tenant?.status === 'error' ? errorKey(tenant.lastError) : null)

  return (
    <main className={styles.wrap}>
      <div className={styles.frame}>
        <div className={styles.eyebrow}>
          <span className={styles.eyebrowTag}>; portal</span>
          <span className={styles.eyebrowLine} />
          {user ? (
            <button type="button" className={styles.signOut} onClick={() => setAskingSignOut(true)}>{t('portal_signout')}</button>
          ) : null}
        </div>
        <div className={styles.card} data-screen={screen}>
          {bannerKey ? <p className={styles.errorBox} role="alert">{t(bannerKey)}</p> : null}
          {screen === 'loading' && <p className={styles.note}>{t('portal_loading')}</p>}
          {screen === 'signin' && <SigninState t={t} onSent={onSent} setError={setError} />}
          {screen === 'signin-code' && pending && (
            <SigninCodeState t={t} phone={pending.phone} confirmation={pending.confirmation} setError={setError}
              onBack={() => { setPhase(null); setPending(null); setError(null) }} />
          )}
          {screen === 'connect' && <ConnectState t={t} user={user} tenant={tenant} setError={setError} />}
          {screen === 'check' && <CheckState t={t} user={user} tenant={tenant} setError={setError} />}
          {screen === 'connected' && <ConnectedState t={t} lang={lang} user={user} tenant={tenant} setError={setError} />}
          {screen === 'revoked' && <RevokedState t={t} tenant={tenant} onReconnect={() => { setError(null); setPhase('reconnect') }} />}
        </div>
      </div>
      {user && askingSignOut ? (
        <SignOutDialog t={t} onConfirm={confirmSignOut} onCancel={() => setAskingSignOut(false)} />
      ) : null}
    </main>
  )
}
