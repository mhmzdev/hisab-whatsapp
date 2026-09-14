import markLight from '@/assets/hisab_light.png'
import markDark from '@/assets/hisab_dark.png'

// Both marks ship in the markup; globals.css shows the one matching <html data-theme>, so the pre-paint
// theme script picks the right one before first paint with no client JS. `light` pins the bright mark for
// surfaces that stay dark in both themes (the footer), where the dark mark would vanish.
export default function BrandMark({ size = 30, radius = 8, light = false }) {
  const style = { width: size, height: size, borderRadius: radius }
  if (light) {
    return <img className="brand-logo" src={markLight.src} alt="" aria-hidden="true" width={size} height={size} style={style} />
  }
  return (
    <span className="brand-logo" style={style} aria-hidden="true">
      <img className="brand-logo-light" src={markLight.src} alt="" width={size} height={size} style={style} />
      <img className="brand-logo-dark" src={markDark.src} alt="" width={size} height={size} style={style} />
    </span>
  )
}
