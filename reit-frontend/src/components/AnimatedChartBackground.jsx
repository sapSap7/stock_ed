import { useEffect, useRef } from 'react'

const WIDTH = 800
const HEIGHT = 400
const STEP_X = 20
const SCROLL_SPEED = 4
const TICK_MS = 60

function seedLine(startY) {
  const points = []
  let y = startY
  for (let x = 0; x <= WIDTH + STEP_X; x += STEP_X) {
    y += (Math.random() - 0.5) * 45
    y = Math.max(50, Math.min(HEIGHT - 50, y))
    points.push({ x, y })
  }
  return points
}

function pointsToString(points) {
  return points.map((p) => `${p.x},${p.y}`).join(' ')
}

function useTickerLine(lineRef, arrowRef, startY) {
  useEffect(() => {
    let points = seedLine(startY)

    const interval = setInterval(() => {
      points = points.map((p) => ({ ...p, x: p.x - SCROLL_SPEED }))
      while (points.length > 1 && points[0].x < -STEP_X) points.shift()

      const last = points[points.length - 1]
      if (last.x < WIDTH) {
        const nextY = Math.max(50, Math.min(HEIGHT - 50, last.y + (Math.random() - 0.5) * 45))
        points.push({ x: last.x + STEP_X, y: nextY })
      }

      lineRef.current?.setAttribute('points', pointsToString(points))

      const tip = points[points.length - 1]
      const prev = points[points.length - 2] || tip
      const angle = Math.atan2(tip.y - prev.y, tip.x - prev.x) * (180 / Math.PI)
      arrowRef.current?.setAttribute('transform', `translate(${tip.x}, ${tip.y}) rotate(${angle})`)
    }, TICK_MS)

    return () => clearInterval(interval)
  }, [lineRef, arrowRef, startY])
}

function AnimatedChartBackground() {
  const line1Ref = useRef(null)
  const arrow1Ref = useRef(null)
  const line2Ref = useRef(null)
  const arrow2Ref = useRef(null)

  useTickerLine(line1Ref, arrow1Ref, HEIGHT * 0.4)
  useTickerLine(line2Ref, arrow2Ref, HEIGHT * 0.6)

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full h-full opacity-20 dark:opacity-30"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id="lineGradient1" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#0284c7" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>
        <linearGradient id="lineGradient2" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f97316" />
          <stop offset="100%" stopColor="#fb923c" />
        </linearGradient>
      </defs>

      <polyline ref={line1Ref} fill="none" stroke="url(#lineGradient1)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <polygon ref={arrow1Ref} points="0,-8 16,0 0,8" fill="#38bdf8" />

      <polyline ref={line2Ref} fill="none" stroke="url(#lineGradient2)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <polygon ref={arrow2Ref} points="0,-8 16,0 0,8" fill="#fb923c" />
    </svg>
  )
}

export default AnimatedChartBackground
