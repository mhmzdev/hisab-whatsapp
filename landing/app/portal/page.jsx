'use client'

import { useEffect, useState } from 'react'
import { useLanguage } from '../LanguageProvider'
import { NONCE, CONNECTED } from '@/content/mock.js'
import styles from './portal.module.css'

const STATES = ['connect', 'check', 'connected', 'revoked']

function ConnectState({ t }) {
  return (
    <>
      <h1>{t('portal_connect_title')}</h1>
      <label className={styles.field}>
        <span>{t('portal_connect_name_label')}</span>
        <input type="text" name="agent-name" autoComplete="off" />
      </label>
      <label className={styles.field}>
        <span>{t('portal_connect_key_label')}</span>
        <input type="password" name="api-key" autoComplete="off" />
      </label>
      <p className={styles.note}>{t('portal_connect_key_note')}</p>
      <div className={styles.steps}>{t('portal_connect_steps')}</div>
      <button type="button" className={styles.button} disabled title={t('portal_connect_button')}>
        {t('portal_connect_button')}
      </button>
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
      </div>
      <div className={styles.waiting}>
        <span className={styles.dot} />
        {t('portal_verify_waiting')}
      </div>
      <p className={styles.expiry}>{t('portal_verify_expiry')}</p>
    </>
  )
}

function ConnectedState({ t }) {
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
      </div>
      <p className={styles.hint}>{t('portal_connected_export_hint')}</p>
      <button type="button" className={styles.buttonDanger}>{t('portal_connected_revoke_button')}</button>
    </>
  )
}

function RevokedState({ t }) {
  return (
    <>
      <h1>{t('portal_revoked_title')}</h1>
      <p>{t('portal_revoked_body')}</p>
      <p className={styles.note}>{t('portal_revoked_retention')}</p>
      <p>{t('portal_revoked_reconnect')}</p>
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

  return (
    <main className={styles.wrap}>
      <div className={styles.card}>
        {state === 'connect' && <ConnectState t={t} />}
        {state === 'check' && <CheckState t={t} />}
        {state === 'connected' && <ConnectedState t={t} />}
        {state === 'revoked' && <RevokedState t={t} />}
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
