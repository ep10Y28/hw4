// The hero's chenille-letter wordmark. Three stacked layers of the same text:
//   1. a darker "thickness" layer offset down-right (felt letters are raised),
//   2. the white chenille fill, revealed bottom-to-top like it's being embroidered,
//   3. a dashed blue stitch line on the letter edge that sews itself in.
// Animation runs once on load and is skipped under prefers-reduced-motion (CSS).
type Props = { lines: string[] }

export default function StitchedWordmark({ lines }: Props) {
  const lineHeight = 132
  const height = lineHeight * lines.length + 24
  return (
    <svg
      className="wordmark"
      viewBox={`0 0 1000 ${height}`}
      role="img"
      aria-label={lines.join(' ')}
      preserveAspectRatio="xMinYMin meet"
    >
      <defs>
        <clipPath id="wm-fill">
          <rect className="wordmark-fill-rect" x="0" y="0" width="1000" height={height} />
        </clipPath>
      </defs>
      {lines.map((line, i) => {
        const y = lineHeight * (i + 1) - 6
        const common = { x: 6, y, textLength: i === 0 ? 960 : undefined, lengthAdjust: 'spacingAndGlyphs' as const }
        return (
          <g key={line}>
            <text {...common} className="wordmark-depth" transform="translate(6 7)">
              {line}
            </text>
            <text {...common} className="wordmark-fill" clipPath="url(#wm-fill)">
              {line}
            </text>
            <text {...common} className="wordmark-stitch">
              {line}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
