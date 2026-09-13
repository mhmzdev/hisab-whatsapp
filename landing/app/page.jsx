'use client'

import { Fragment, useEffect, useState } from 'react'
import { useLanguage } from './LanguageProvider'
import { readSignedIn } from './signedIn'
import { EXCHANGES, SHOP_EXCHANGES } from '@/content/mock.js'
import styles from './landing.module.css'

const WAVE_HEIGHTS = [6, 12, 16, 9, 13, 7, 11, 5]

function Eyebrow({ n }) {
  return (
    <div className={styles.eyebrow}>
      <span className={styles.eyebrowTag}>; n:{n}</span>
      <span className={styles.eyebrowLine} />
    </div>
  )
}

export default function Home() {
  const { t } = useLanguage()
  const [plan, setPlan] = useState('monthly')
  const [signedIn, setSignedIn] = useState(false)
  useEffect(() => setSignedIn(readSignedIn()), [])

  return (
    <main>
      <section className={styles.hero}>
        <div className={styles.heroText}>
          <h1 className={styles.title}>{t('hero_title')}</h1>
          <p className={styles.subline}>{t('hero_subline')}</p>
          <div className={styles.ctaRow}>
            <a className={styles.cta} href="/portal/">{signedIn ? t('cta_go_to_portal') : t('hero_cta')}</a>
            <a className={styles.ctaSecondary} href="https://github.com/mhmzdev/hisab-whatsapp">{t('hero_cta_secondary')}</a>
          </div>
        </div>

        <div className={styles.phoneWrap}>
          <div className={styles.phone}>
            <div className={styles.phoneScreen}>
              <div className={styles.phoneHeader}>
                <span className={styles.phoneMark} />
                <span className={styles.phoneHeaderText}>
                  <span className={styles.phoneName}>Hisab</span>
                  <span className={styles.phoneSub}>your agent</span>
                </span>
              </div>
              <div className={styles.phoneBody}>
                {EXCHANGES.map((ex, i) => (
                  <Fragment key={i}>
                    {ex.in.startsWith('🎤') ? (
                      <div className={styles.bubbleVoice}>
                        <span className={styles.voiceIcon} />
                        <span className={styles.waveform}>
                          {WAVE_HEIGHTS.map((h, j) => (
                            <span key={j} className={styles.wave} style={{ height: h }} />
                          ))}
                        </span>
                        <span className={styles.voiceTime}>{ex.in.replace('🎤 ', '')}</span>
                      </div>
                    ) : ex.in.startsWith('📷') ? (
                      <div className={styles.bubblePhoto}>
                        <div className={styles.photoSlot}>
                          <span className={styles.photoLabel}>receipt photo</span>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.bubbleOut}>{ex.in}</div>
                    )}
                    <div className={styles.bubbleIn}>{ex.out}</div>
                  </Fragment>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <Eyebrow n={2} />
        <h2>{t('section_ways_title')}</h2>
        <div className={styles.cards}>
          <div className={styles.card}>
            <span className={styles.cardIcon}>Aa</span>
            <div>
              <h3 className={styles.cardTitle}>{t('card_text_title')}</h3>
              <p className={styles.cardBody}>{t('card_text_body')}</p>
            </div>
          </div>
          <div className={styles.card}>
            <span className={styles.cardIcon}>🎤</span>
            <div>
              <h3 className={styles.cardTitle}>{t('card_voice_title')}</h3>
              <p className={styles.cardBody}>{t('card_voice_body')}</p>
            </div>
          </div>
          <div className={styles.card}>
            <span className={styles.cardIcon}>📷</span>
            <div>
              <h3 className={styles.cardTitle}>{t('card_photo_title')}</h3>
              <p className={styles.cardBody}>{t('card_photo_body')}</p>
            </div>
          </div>
        </div>
      </section>

      <section className={`${styles.section} ${styles.band}`}>
        <Eyebrow n={3} />
        <h2>{t('why_title')}</h2>
        <div className={styles.strip}>
          <div className={styles.stripItem}>
            <span className={styles.stripIcon}><span className={styles.stripDot} /></span>
            <p>{t('why_undo')}</p>
          </div>
          <div className={styles.stripItem}>
            <span className={styles.stripIcon}><span className={styles.stripDot} /></span>
            <p>{t('why_linked')}</p>
          </div>
          <div className={styles.stripItem}>
            <span className={styles.stripIcon}><span className={styles.stripDot} /></span>
            <p>{t('why_strict')}</p>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <Eyebrow n={4} />
        <h2>{t('ledger_title')}</h2>
        <div className={styles.ledgerGrid}>
          <div className={styles.ledgerCol}>
            <pre className={styles.ledgerCode}>{'2026-09-12 chai  ; n:2\n    expenses:food:snacks        PKR 300.00\n    assets:wallet:easypaisa'}</pre>
            <div className={styles.ledgerNote}>
              <span>desk dashboard — balance sheet, net worth</span>
            </div>
          </div>
          <p className={styles.ledgerText}>{t('ledger_body')}</p>
        </div>
      </section>

      <section className={styles.section}>
        <Eyebrow n={5} />
        <h2>{t('how_title')}</h2>
        <div className={styles.howSteps}>
          <div className={styles.howStep}>
            <span className={styles.howNum}>1</span>
            <p>{t('how_step1')}</p>
          </div>
          <div className={styles.howStep}>
            <span className={styles.howNum}>2</span>
            <p>{t('how_step2')}</p>
          </div>
          <div className={styles.howStep}>
            <span className={`${styles.howNum} ${styles.howNumLast}`}>3</span>
            <p>{t('how_step3')}</p>
          </div>
        </div>
        <div className={styles.custody}>
          <h3>{t('custody_title')}</h3>
          <p>{t('custody_body')}</p>
          <a href="https://github.com/mhmzdev/hisab-whatsapp">{t('custody_selfhost_label')}</a>
        </div>
      </section>

      <section className={`${styles.section} ${styles.band}`}>
        <Eyebrow n={6} />
        <h2>{t('shop_title')}</h2>
        <div className={styles.shopCard}>
          <div className={styles.shopGrid}>
            <div className={styles.shopCol}>
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
      </section>

      <section id="pricing" className={styles.section}>
        <Eyebrow n={7} />
        <h2>{t('price_title')}</h2>
        <div className={styles.priceCard}>
          <div className={styles.priceOptions}>
            <button
              type="button"
              className={plan === 'monthly' ? `${styles.priceOption} ${styles.priceOptionActive}` : styles.priceOption}
              onClick={() => setPlan('monthly')}
            >
              <span className={styles.priceRadio}>{plan === 'monthly' && <span className={styles.priceDot} />}</span>
              <span className={styles.priceOptionText}>
                <span className={styles.priceAmount}>{t('price_amount')}</span>
                <span className={styles.priceFree}>{t('price_free')}</span>
              </span>
            </button>
            <button
              type="button"
              className={plan === 'yearly' ? `${styles.priceOption} ${styles.priceOptionActive}` : styles.priceOption}
              onClick={() => setPlan('yearly')}
            >
              <span className={styles.priceRadio}>{plan === 'yearly' && <span className={styles.priceDot} />}</span>
              <span className={styles.priceOptionText}>
                <span className={styles.priceAmount}>{t('price_yearly_amount')}</span>
                <span className={styles.priceFree}>{t('price_yearly_free')}</span>
              </span>
            </button>
          </div>
          <div className={styles.priceDetails}>
            <p>{t('price_includes')}</p>
            <div className={styles.priceActions}>
              <a className={styles.priceCta} href="/portal/">{signedIn ? t('cta_go_to_portal') : t('price_cta')}</a>
              <span className={styles.priceNote}>{t('price_payment_note')}</span>
            </div>
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        <span className={styles.footerWatermark} aria-hidden="true" dir="rtl">حساب</span>
        <div className={styles.footerInner}>
          <div className={styles.footerRow}>
            <span className={styles.footerBrand}>Hisab</span>
            <a href="https://github.com/mhmzdev/hisab-whatsapp">{t('footer_selfhost')}</a>
            <span>{t('footer_origin')}</span>
            <span>{t('footer_note')}</span>
          </div>
          <p className={styles.footerNote}>{t('footer_distinction')}</p>
        </div>
      </footer>
    </main>
  )
}
