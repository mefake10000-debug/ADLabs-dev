export function EdgeDevice() {
  return (
    <svg viewBox="0 0 480 340" className="h-auto w-full" role="img" aria-label="Compact edge AI device">
      <defs>
        <linearGradient id="devBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2c2c2e" />
          <stop offset="100%" stopColor="#1c1c1e" />
        </linearGradient>
        <linearGradient id="devFace" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3a3a3c" />
          <stop offset="100%" stopColor="#242426" />
        </linearGradient>
        <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#d4ad5e" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#d4ad5e" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* halo */}
      <circle cx="240" cy="170" r="150" fill="url(#glow)" />

      {/* body */}
      <rect x="120" y="110" width="240" height="120" rx="26" fill="url(#devBody)" stroke="#3a3a3c" strokeWidth="1.5" />
      <rect x="120" y="110" width="240" height="120" rx="26" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />

      {/* lens */}
      <circle cx="170" cy="170" r="34" fill="#000000" />
      <circle cx="170" cy="170" r="34" fill="none" stroke="#3a3a3c" strokeWidth="2" />
      <circle cx="170" cy="170" r="20" fill="#101010" />
      <circle cx="170" cy="170" r="20" fill="none" stroke="rgba(212,173,94,0.5)" strokeWidth="1.2" />
      <circle cx="163" cy="163" r="5" fill="rgba(212,173,94,0.85)" />

      {/* status led */}
      <rect x="222" y="146" width="56" height="20" rx="10" fill="#101010" />
      <circle cx="262" cy="156" r="4" fill="#d4ad5e">
        <animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite" />
      </circle>
      <rect x="222" y="146" width="56" height="20" rx="10" fill="none" stroke="#3a3a3c" strokeWidth="1" />

      {/* edge label */}
      <text x="300" y="166" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="9" letterSpacing="1.6" fill="#98989d" fontWeight="700">EDGE</text>
      <text x="300" y="181" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="11" letterSpacing="0.8" fill="#f5f5f7" fontWeight="700">AD LABS</text>

      {/* ports */}
      <rect x="222" y="196" width="40" height="10" rx="5" fill="#0a0a0a" />
      <rect x="268" y="196" width="40" height="10" rx="5" fill="#0a0a0a" />
      <text x="222" y="222" fontFamily="-apple-system, sans-serif" fontSize="7.5" letterSpacing="0.6" fill="#6e6e73">ETHERNET · POWER · POE</text>

      {/* size coin comparison */}
      <circle cx="404" cy="118" r="34" fill="#b8860b" opacity="0.2" />
      <circle cx="404" cy="118" r="30" fill="#8B7CF6" stroke="#6E5CE6" strokeWidth="1.5" />
      <circle cx="404" cy="118" r="26" fill="none" stroke="#8a6d1f" strokeWidth="1" />
      <circle cx="404" cy="118" r="18" fill="#b8860b" />
      <circle cx="404" cy="118" r="10" fill="#8a6d1f" />
      <text x="404" y="170" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="9" fill="#98989d">≈ 2× CARDS</text>
      <text x="404" y="183" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="8.5" fill="#6e6e73">93 × 61 × 27 mm</text>
      <text x="404" y="196" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="8.5" fill="#6e6e73">240 g · fanless · silent</text>

      {/* dims */}
      <line x1="120" y1="94" x2="360" y2="94" stroke="#6e6e73" strokeWidth="1" strokeDasharray="3 3" />
      <text x="240" y="88" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="9" fill="#98989d">93 mm — smaller than a smartphone</text>

      {/* local-processing badge */}
      <rect x="132" y="248" width="216" height="34" rx="17" fill="#d4ad5e" />
      <text x="240" y="270" textAnchor="middle" fontFamily="-apple-system, sans-serif" fontSize="11" fill="#16161f" fontWeight="700">100% ON-PREMISE · NO CLOUD</text>
    </svg>
  )
}
