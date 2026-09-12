// Fake kiryana-store exchanges for the hero phone mock, in the register of sample-vault/2026-Q3.md.
// Invented shop, invented numbers — no personal data.
export const EXCHANGES = [
  { in: 'aaj ki sale 45000', out: '#312 posted · sale PKR 45,000 · September in 1,184,500 / out 396,300' },
  { in: '🎤 0:04', out: '#313 posted · Metro stock PKR 31,000 on udhaar · Metro balance PKR 79,000' },
  { in: 'Metro ko kitna dena hai', out: 'Metro: PKR 79,000 outstanding' },
]

// Display-only until #7 — no real nonce generation, matching or expiry exists yet.
export const NONCE = '482913'

export const CONNECTED = {
  agentName: 'Ali Traders',
  connectedSince: '3 September 2026',
  lastActivity: '12 minutes ago',
  entriesThisMonth: 47,
  language: 'Roman Urdu',
}
