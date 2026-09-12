// Fake kiryana-store exchanges for the hero phone mock, in the register of sample-vault/2026-Q3.md.
// Invented shop, invented numbers — no personal data.
export const EXCHANGES = [
  { in: '2500 coffee', out: 'posted #1 — coffee 2,500 — month out 2,500' },
  { in: '300 ki chai easypaisa se', out: 'posted #2 — chai 300 — month out 2,800' },
  { in: '🎤 0:07', out: 'posted #3 — debt repaid by friend 50,000 — month out 2,800' },
  { in: '📷 receipt photo', out: 'posted #4 — Rosso Coffee Co 52,500 — month out 55,300' },
]

// Same product, shown in English and Urdu side by side — the shop section.
export const SHOP_EXCHANGES = {
  en: [
    { in: 'aaj ki sale 45000', out: 'posted #35 — today’s sales 45,000 — month in 383,706' },
    { in: 'Metro ko kitna dena hai?', out: 'Metro 94,000' },
  ],
  ur: [
    { in: 'آج کی سیل 45000', out: 'درج ہو گیا #35 — آج کی سیل 45,000 — مہینے کی آمد 383,706' },
    { in: 'میٹرو کو کتنا دینا ہے؟', out: 'میٹرو 94,000' },
  ],
}

// Display-only until #7 — no real nonce generation, matching or expiry exists yet.
export const NONCE = '482913'

export const CONNECTED = {
  agentName: 'Ali Traders',
  connectedSince: '3 September 2026',
  lastActivity: '12 minutes ago',
  entriesThisMonth: 47,
  language: 'Roman Urdu',
  plan: 'PKR 300 / month · first month free',
  quotaUsed: 212,
  quotaTotal: 1000,
}
