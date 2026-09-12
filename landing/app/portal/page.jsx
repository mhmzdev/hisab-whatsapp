'use client'

import { useEffect, useRef, useState } from 'react'
import { useLanguage } from '../LanguageProvider'
import { NONCE, CONNECTED } from '@/content/mock.js'
import styles from './portal.module.css'

const STATES = ['signin', 'signin-code', 'connect', 'check', 'connected', 'revoked']

function SigninState({ t, goTo }) {
  return (
    <>
      <h1>{t('portal_signin_title')}</h1>
      <div className={styles.phoneGroup} dir="ltr">
        <span className={styles.phonePrefix}>+92</span>
        <input type="tel" name="phone" autoComplete="off" placeholder="300 000 0000" className={styles.phoneInput} />
      </div>
      <p className={styles.note}>{t('portal_signin_helper')}</p>
      <button type="button" className={styles.button} onClick={() => goTo('signin-code')}>{t('portal_signin_button')}</button>
      <p className={styles.fine}>{t('portal_signin_fine')}</p>
    </>
  )
}

function SigninCodeState({ t, goTo }) {
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const refs = useRef([])

  function onDigit(i, e) {
    const v = (e.target.value || '').replace(/[^0-9]/g, '').slice(-1)
    const next = otp.slice()
    next[i] = v
    setOtp(next)
    if (v && i < 5 && refs.current[i + 1]) refs.current[i + 1].focus()
  }

  return (
    <>
      <h1>{t('portal_signin_code_title')}</h1>
      <div className={styles.otpRow} dir="ltr">
        {otp.map((v, i) => (
          <input
            key={i}
            ref={(el) => { refs.current[i] = el }}
            inputMode="numeric"
            maxLength={1}
            value={v}
            onChange={(e) => onDigit(i, e)}
            className={styles.otpBox}
          />
        ))}
      </div>
      <p className={styles.note}>{t('portal_signin_code_sent')}</p>
      <button type="button" className={styles.button} onClick={() => goTo('connect')}>{t('portal_signin_code_button')}</button>
      <button type="button" className={styles.linkButton} onClick={() => goTo('signin')}>{t('portal_signin_code_wrong_number')}</button>
    </>
  )
}

function ConnectState({ t, goTo }) {
  const [keyLen, setKeyLen] = useState(0)

  function pasteKey() {
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText()
        .then((txt) => setKeyLen(Math.min((txt || '').length, 40)))
        .catch(() => setKeyLen(32))
    } else {
      setKeyLen(32)
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
        <input type="text" name="agent-name" autoComplete="off" placeholder="Hisab" />
      </label>
      <label className={styles.field}>
        <span>{t('portal_connect_key_label')}</span>
        <div className={styles.keyRow}>
          <input
            dir="ltr"
            type="text"
            name="api-key"
            autoComplete="off"
            placeholder="••••••••••••••••"
            value={'•'.repeat(keyLen)}
            onChange={(e) => setKeyLen((e.target.value || '').length)}
          />
          <button type="button" className={styles.pasteButton} onClick={pasteKey}>{t('portal_connect_paste_button')}</button>
        </div>
      </label>
      <p className={styles.note}>{t('portal_connect_key_note')}</p>
      <button type="button" className={styles.button} onClick={() => goTo('check')}>{t('portal_connect_button')}</button>
      <p className={styles.note}>{t('portal_connect_custody_note')}</p>
    </>
  )
}

function CheckState({ t }) {
  const [copied, setCopied] = useState(false)
  const command = `verify ${NONCE}`

  function copy() {
    try {
      navigator.clipboard.writeText(command)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  return (
    <>
      <h1>{t('portal_verify_title')}</h1>
      <p>{t('portal_verify_instruction').replace('{nonce}', NONCE)}</p>
      <div className={styles.code}>{command}</div>
      <div className={styles.copyRow}>
        <button type="button" onClick={copy}>{copied ? '✓' : t('portal_verify_copy')}</button>
        <button type="button">{t('portal_verify_new_code')}</button>
      </div>
      <div className={styles.waiting}>
        <span className={styles.dot} />
        {t('portal_verify_waiting')}
      </div>
      <p className={styles.expiry}>{t('portal_verify_expiry')}</p>
      <p className={styles.note}>{t('portal_verify_after_caption')}</p>
    </>
  )
}

function ConnectedState({ t, goTo }) {
  const [askingRevoke, setAskingRevoke] = useState(false)
  const quotaPct = Math.min(100, Math.round((CONNECTED.quotaUsed / CONNECTED.quotaTotal) * 100))

  return (
    <>
      <h1>{t('portal_connected_title')}</h1>
      <div className={styles.rows}>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connect_name_label')}</span>
          <span>{CONNECTED.agentName}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_since_label')}</span>
          <span>{CONNECTED.connectedSince}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_activity_label')}</span>
          <span>{CONNECTED.lastActivity}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_entries_label')}</span>
          <span>{CONNECTED.entriesThisMonth}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_language_label')}</span>
          <span>{CONNECTED.language}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>{t('portal_connected_plan_label')}</span>
          <span>{CONNECTED.plan}</span>
        </div>
      </div>

      <div className={styles.quotaBlock}>
        <div className={styles.quotaHeader}>
          <span>{t('portal_connected_quota_label')}</span>
          <span dir="ltr">{CONNECTED.quotaUsed} / {CONNECTED.quotaTotal}</span>
        </div>
        <div className={styles.quotaTrack}>
          <span className={styles.quotaFill} style={{ width: `${quotaPct}%` }} />
        </div>
      </div>

      <p className={styles.hint}>
        {t('portal_connected_export_hint_pre')} <code>export-ledger</code> {t('portal_connected_export_hint_post')}
      </p>
      <p className={styles.note}>{t('portal_connected_export_hint_sub')}</p>

      {askingRevoke ? (
        <div className={styles.confirmBox}>
          <p>{t('portal_connected_revoke_confirm_text')}</p>
          <div className={styles.confirmRow}>
            <button type="button" className={styles.buttonDangerSolid} onClick={() => goTo('revoked')}>{t('portal_connected_revoke_confirm_yes')}</button>
            <button type="button" className={styles.buttonOutline} onClick={() => setAskingRevoke(false)}>{t('portal_connected_revoke_confirm_no')}</button>
          </div>
        </div>
      ) : (
        <button type="button" className={styles.buttonDanger} onClick={() => setAskingRevoke(true)}>{t('portal_connected_revoke_button')}</button>
      )}
    </>
  )
}

function RevokedState({ t, goTo }) {
  return (
    <>
      <h1>{t('portal_revoked_title')}</h1>
      <p>{t('portal_revoked_body')}</p>
      <p className={styles.note}>{t('portal_revoked_retention')}</p>
      <button type="button" className={styles.button} onClick={() => goTo('connect')}>{t('portal_revoked_reconnect_button')}</button>
      <p className={styles.note}>{t('portal_revoked_muted')}</p>
    </>
  )
}

export default function Portal() {
  const { t } = useLanguage()
  const [state, setState] = useState('connect')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const s = params.get('state')
    if (STATES.includes(s)) setState(s)
  }, [])

  function goTo(next) {
    setState(next)
  }

  return (
    <main className={styles.wrap}>
      <div className={styles.frame}>
        <div className={styles.eyebrow}>
          <span className={styles.eyebrowTag}>; portal</span>
          <span className={styles.eyebrowLine} />
        </div>
        <div className={styles.card}>
          {state === 'signin' && <SigninState t={t} goTo={goTo} />}
          {state === 'signin-code' && <SigninCodeState t={t} goTo={goTo} />}
          {state === 'connect' && <ConnectState t={t} goTo={goTo} />}
          {state === 'check' && <CheckState t={t} />}
          {state === 'connected' && <ConnectedState t={t} goTo={goTo} />}
          {state === 'revoked' && <RevokedState t={t} goTo={goTo} />}
        </div>
      </div>
      <div data-demo-only>
        <div className={styles.demoLabel}>Demo state switcher — not part of the product</div>
        <div className={styles.demoRow}>
          {STATES.map((s) => (
            <a key={s} href={`?state=${s}`}>{s}</a>
          ))}
        </div>
      </div>
    </main>
  )
}
