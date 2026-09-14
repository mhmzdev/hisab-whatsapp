'use client'

import { Fragment, useEffect, useState } from 'react'
import { AudioLines, Camera, Lock, MessageSquareText, Mic, ScrollText, Undo2 } from 'lucide-react'
import { useLanguage } from './LanguageProvider'
import { readSignedIn } from './signedIn'
import BrandMark from './BrandMark'
import { EXCHANGES, LEDGER_SAMPLE, SHOP_EXCHANGES } from '@/content/mock.js'
import styles from './landing.module.css'

const GITHUB_URL = 'https://github.com/mhmzdev/hisab-whatsapp'
const WAVE_HEIGHTS = [6, 12, 16, 9, 13, 7, 11, 5]

// every GitHub link opens beside the landing page, never in place of it
function External({ href = GITHUB_URL, className, children }) {
  return (
    <a className={className} href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  )
}

function Eyebrow({ n }) {
  return (
    <div className={styles.eyebrow} dir="ltr">
      <span className={styles.eyebrowTag}>; n:{n}</span>
      <span className={styles.eyebrowLine} />
    </div>
  )
}

function Section({ n, title, band, id, children }) {
  return (
    <section id={id} className={band ? `${styles.section} ${styles.band}` : styles.section}>
      <div className={styles.inner}>
        <Eyebrow n={n} />
        <h2 className={styles.h2}>{title}</h2>
        {children}
      </div>
    </section>
  )
}

function OutBubble({ ex }) {
  if (ex.kind === 'voice') {
    return (
      <div className={`${styles.bubbleOut} ${styles.bubbleVoice}`}>
        <span className={styles.voiceIcon}><Mic size={12} strokeWidth={2.5} aria-hidden="true" /></span>
        <span className={styles.waveform}>
          {WAVE_HEIGHTS.map((h, j) => (
            <span key={j} className={styles.wave} style={{ height: h }} />
          ))}
        </span>
        <span className={styles.voiceTime}>{ex.in}</span>
      </div>
    )
  }
  if (ex.kind === 'photo') {
    return (
      <div className={`${styles.bubbleOut} ${styles.bubblePhoto}`}>
        <div className={styles.photoSlot}>
          <span className={styles.photoLabel}>{ex.in}</span>
        </div>
      </div>
    )
  }
  if (ex.kind === 'reply') {
    return (
      <div className={`${styles.bubbleOut} ${styles.bubbleReply}`}>
        <div className={styles.quote}>
          <span className={styles.quoteFrom}>{ex.quoteFrom}</span>
          <span className={styles.quoteText}>{ex.quote}</span>
        </div>
        <div className={styles.replyText}>{ex.in}</div>
      </div>
    )
  }
  return <div className={styles.bubbleOut}>{ex.in}</div>
}

export default function Home() {
  const { t, lang } = useLanguage()
  const [plan, setPlan] = useState('monthly')
  const [signedIn, setSignedIn] = useState(false)
  useEffect(() => setSignedIn(readSignedIn()), [])
  const startLabel = signedIn ? t('cta_go_to_portal') : t('hero_cta')

  const plans = [
    { key: 'monthly', amount: t('price_amount'), billing: t('price_monthly_billing'), free: t('price_free') },
    { key: 'yearly', amount: t('price_yearly_amount'), billing: t('price_yearly_billing'), free: t('price_yearly_free') },
  ]

  return (
    <main>
      <div className={styles.heroWrap}>
        <span className={styles.heroRules} aria-hidden="true" />
        <section className={styles.hero}>
          <div className={styles.heroText}>
            <h1 className={styles.title}>
              {t('hero_title')}
              <span className={styles.titleDot}>{lang === 'ur' ? '۔' : '.'}</span>
            </h1>
            <p className={styles.subline}>{t('hero_subline')}</p>
            <div className={styles.ctaRow}>
              <a className={styles.cta} href="/portal/">{startLabel}</a>
              <External className={styles.ctaSecondary}>{t('hero_cta_secondary')}</External>
            </div>
            <p className={styles.platforms}>{t('hero_platforms')}</p>
          </div>

          <div className={styles.phoneWrap} dir="ltr">
            <div className={styles.phone}>
              <div className={styles.phoneScreen}>
                <div className={styles.phoneHeader}>
                  <BrandMark size={30} radius={9} />
                  <span className={styles.phoneHeaderText}>
                    <span className={styles.phoneName}>Hisab</span>
                    <span className={styles.phoneSub}>{t('phone_agent_label')}</span>
                  </span>
                </div>
                <div className={styles.phoneBody}>
                  {EXCHANGES.map((ex, i) => (
                    <Fragment key={i}>
                      <OutBubble ex={ex} />
                      <div className={styles.bubbleIn}>{ex.out}</div>
                    </Fragment>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <Section n={2} title={t('section_ways_title')}>
        <div className={styles.cols3}>
          {[
            { Icon: MessageSquareText, key: 'text' },
            { Icon: AudioLines, key: 'voice' },
            { Icon: Camera, key: 'photo' },
          ].map(({ Icon, key }) => (
            <div key={key} className={styles.card}>
              <span className={styles.cardIcon}><Icon size={20} strokeWidth={1.8} aria-hidden="true" /></span>
              <div className={styles.itemText}>
                <h3 className={styles.cardTitle}>{t(`card_${key}_title`)}</h3>
                <p className={styles.body15}>{t(`card_${key}_body`)}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section n={3} title={t('why_title')} band>
        <div className={`${styles.cols3} ${styles.strip}`}>
          {[
            { Icon: Undo2, key: 'undo' },
            { Icon: ScrollText, key: 'linked' },
            { Icon: Lock, key: 'private' },
          ].map(({ Icon, key }) => (
            <div key={key} className={styles.stripItem}>
              <span className={styles.stripIcon}><Icon size={18} strokeWidth={1.8} aria-hidden="true" /></span>
              <h3 className={styles.stripTitle}>{t(`why_${key}_title`)}</h3>
              <p className={styles.body15}>{t(`why_${key}_body`)}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section n={4} title={t('ledger_title')}>
        <div className={styles.cols2}>
          <div className={styles.ledgerCol} dir="ltr">
            <div className={styles.connector}>
              <span className={styles.connectorBubble}>{LEDGER_SAMPLE.in}</span>
              <span className={styles.connectorDash} />
              <span className={styles.connectorDot} />
              <span className={styles.connectorDash} />
            </div>
            <div className={styles.receipt}>
              <pre className={styles.ledgerCode}>{LEDGER_SAMPLE.entry}</pre>
              <span className={`${styles.receiptEdge} ${styles.receiptTop}`} />
              <span className={`${styles.receiptEdge} ${styles.receiptBottom}`} />
            </div>
            <div className={styles.dashboardFrame}>
              <div className={styles.dashboardSlot}>
                <span>{t('ledger_dashboard_caption')}</span>
              </div>
            </div>
          </div>
          <p className={styles.bodyLarge}>{t('ledger_body')}</p>
        </div>
      </Section>

      <Section n={5} title={t('how_title')} band>
        <div className={styles.cols3}>
          {[1, 2, 3].map((n) => (
            <div key={n} className={styles.howStep}>
              <span className={styles.howHead}>
                <span className={n === 3 ? `${styles.howNum} ${styles.howNumLast}` : styles.howNum}>{n}</span>
                {n < 3 && <span className={styles.howLine} />}
              </span>
              <h3 className={styles.howTitle}>{t(`how_step${n}_title`)}</h3>
              <p className={styles.body15}>{t(`how_step${n}_body`)}</p>
            </div>
          ))}
        </div>
        <p className={styles.hostedNote}>{t('how_hosted_note')}</p>
        <div className={styles.custody}>
          <h3>{t('custody_title')}</h3>
          <p>{t('custody_body')}</p>
          <External>{t('custody_selfhost_label')}</External>
        </div>
      </Section>

      <Section n={6} title={t('shop_title')}>
        <div className={styles.shopCard}>
          <div className={styles.cols2}>
            <div className={styles.shopCol} dir="ltr">
              {SHOP_EXCHANGES.en.map((ex, i) => (
                <Fragment key={i}>
                  <div className={styles.shopBubbleOut}>{ex.in}</div>
                  <div className={styles.shopBubbleIn}>{ex.out}</div>
                </Fragment>
              ))}
            </div>
            <div className={`${styles.shopCol} ${styles.shopColUrdu} urdu`} dir="rtl">
              {SHOP_EXCHANGES.ur.map((ex, i) => (
                <Fragment key={i}>
                  <div className={styles.shopBubbleOut}>{ex.in}</div>
                  <div className={styles.shopBubbleIn}>{ex.out}</div>
                </Fragment>
              ))}
            </div>
          </div>
          <p className={styles.shopFoot}>{t('shop_body')}</p>
        </div>
      </Section>

      <Section n={7} title={t('price_title')} band id="pricing">
        <div className={styles.priceCard}>
          <div className={styles.priceOptions} role="radiogroup" aria-label={t('price_title')}>
            {plans.map((p) => (
              <button
                key={p.key}
                type="button"
                role="radio"
                aria-checked={plan === p.key}
                className={plan === p.key ? `${styles.priceOption} ${styles.priceOptionActive}` : styles.priceOption}
                onClick={() => setPlan(p.key)}
              >
                <span className={styles.priceRadio}>{plan === p.key && <span className={styles.priceDot} />}</span>
                <span className={styles.priceOptionText}>
                  <span className={styles.priceAmount}>{p.amount}</span>
                  <span className={styles.priceBilling}>{p.billing}</span>
                  <span className={styles.priceFree}>{p.free}</span>
                </span>
              </button>
            ))}
          </div>
          <div className={styles.priceDetails}>
            <ul className={styles.priceFeatures}>
              {['agent', 'inputs', 'quota', 'export', 'revoke'].map((k) => (
                <li key={k}><span className={styles.priceBullet} />{t(`price_feature_${k}`)}</li>
              ))}
            </ul>
            <div className={styles.priceActions}>
              <a className={styles.cta} href="/portal/">{signedIn ? t('cta_go_to_portal') : t('price_cta')}</a>
              <span className={styles.priceNote}>{t('price_payment_note')}</span>
            </div>
          </div>
        </div>
      </Section>

      <footer className={styles.footer}>
        <span className={`${styles.footerWatermark} urdu`} aria-hidden="true" dir="rtl">حساب</span>
        <div className={styles.footerInner}>
          <div className={styles.footerRow}>
            <BrandMark size={34} radius={9} light />
            <span className={styles.footerBrand}>Hisab</span>
            <span>{t('hero_title')}</span>
            <External>{t('footer_github')}</External>
            <span>{t('footer_origin')}</span>
            <span>{t('footer_note')}</span>
          </div>
          <p className={styles.footerNote}>{t('footer_privacy')}</p>
        </div>
      </footer>
    </main>
  )
}
