// Fake exchanges for the hero phone mock, in the register of sample-vault/2026-Q3.md.
// Invented shop, invented numbers — no personal data. `kind` picks the bubble: text (default), voice, photo,
// or reply (a quoted earlier message plus the text).
export const EXCHANGES = [
  { in: '2500 coffee', out: 'posted #1 — coffee 2,500 — month out 2,500' },
  { in: '300 ki chai easypaisa se', out: 'posted #2 — chai 300 — month out 2,800' },
  { kind: 'voice', in: '0:07', out: 'posted #3 — debt repaid by friend 50,000 — month out 2,800' },
  { kind: 'photo', in: 'receipt photo', out: 'posted #4 — Rosso Coffee Co 52,500 — month out 55,300' },
  { kind: 'reply', quoteFrom: 'You', quote: 'receipt photo', in: 'undo', out: 'removed #4 — Rosso Coffee Co' },
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

// The ledger block the "Real books" section shows for the chai message.
export const LEDGER_SAMPLE = { in: '300 ki chai easypaisa se', entry: '2026-09-12 chai  ; n:2\n    expenses:food:snacks        PKR 300.00\n    assets:wallet:easypaisa' }

// The Connected screen's plan row. Presentation only — spec 001 takes no payment and has no plan
// tiers; every other row on that screen is live from the tenant document (runner/activity.py).
export const PLAN = 'PKR 300 / month · first month free'
