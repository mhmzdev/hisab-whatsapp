// Pakistani mobiles only (#37): +92, then 3 and nine digits. Accepts the ways people actually type or
// paste one (0346 0159889, 346-0159889, +92 346 0159889, 0092…) and returns null for anything else, so
// the portal never requests an OTP for a malformed number. Other countries come when WhatsApp opens
// agents to them. Dependency-free: tests/smoke.py runs it through node.
export function normalizePkMobile(input) {
  let d = String(input || '').replace(/\D/g, '')
  if (d.startsWith('0092')) d = d.slice(4)
  else if (d.startsWith('92') && d.length === 12) d = d.slice(2)
  else if (d.startsWith('0') && d.length === 11) d = d.slice(1)
  return /^3\d{9}$/.test(d) ? `+92${d}` : null
}
