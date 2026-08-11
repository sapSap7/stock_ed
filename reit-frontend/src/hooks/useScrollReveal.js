import { useEffect, useRef, useState } from 'react'

/**
 * Tracks whether an element is in the viewport, toggling both ways —
 * so a section fades back out when scrolled away from, not just in once.
 */
export function useScrollReveal(threshold = 0) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // rootMargin pulls the trigger line inward so a section (even a tall one,
    // taller than the viewport) reveals as soon as its edge enters view,
    // rather than needing `threshold` of its whole area on screen at once.
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold, rootMargin: '0px 0px -10% 0px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold])

  return [ref, visible]
}
