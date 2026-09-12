'use client'

import { useLanguage } from './LanguageProvider'
import { EXCHANGES } from '@/content/mock.js'
import styles from './landing.module.css'

export default function Home() {
  const { t } = useLanguage()

  return (
    <main className="page">
      <section className={styles.hero}>
        <div className={styles.heroText}>
          <h1 className={styles.title}>{t('hero_title')}</h1>
          <p className={styles.subline}>{t('hero_subline')}</p>
          <a className={styles.cta} href="/portal/">{t('hero_cta')}</a>
        </div>
        <div className={styles.phone}>
          {EXCHANGES.map((ex, i) => (
            <div key={i}>
              <div className={styles.bubbleIn}>{ex.in}</div>
              <div className={styles.bubbleOut}>{ex.out}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.cards}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>{t('card_text_title')}</h3>
            <p className={styles.cardBody}>{t('card_text_body')}</p>
          </div>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>{t('card_voice_title')}</h3>
            <p className={styles.cardBody}>{t('card_voice_body')}</p>
          </div>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>{t('card_photo_title')}</h3>
            <p className={styles.cardBody}>{t('card_photo_body')}</p>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.custody}>
          <h2>{t('custody_title')}</h2>
          <p>{t('custody_body')}</p>
          <p>
            <a href="https://github.com/mhmzdev/hisab-whatsapp">{t('custody_selfhost_label')}</a>
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.why}>
          <h2>{t('why_title')}</h2>
          <ul>
            <li>{t('why_undo')}</li>
            <li>{t('why_linked')}</li>
            <li>{t('why_strict')}</li>
          </ul>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.price}>
          <h2>{t('price_title')}</h2>
          <span className={styles.priceFree}>{t('price_free')}</span>
          <div className={styles.priceAmount}>{t('price_amount')}</div>
          <p>{t('price_includes')}</p>
          <a className={styles.priceCta} href="/portal/">{t('price_cta')}</a>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>{t('footer_distinction')}</p>
        <p>
          <a href="https://github.com/mhmzdev/hisab-whatsapp">{t('footer_selfhost')}</a>
        </p>
      </footer>
    </main>
  )
}
