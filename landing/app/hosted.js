// Is Hosted Hisab open to the public in this build? NEXT_PUBLIC_HOSTED=1 at build time (a static export has no
// server to ask). Off, the default: every "Get started" points at the self-host README, pricing reads as planned,
// and /portal/ says coming soon without ever calling Firebase. `make up` and `make dev` build it on.
export const HOSTED = process.env.NEXT_PUBLIC_HOSTED === '1'
