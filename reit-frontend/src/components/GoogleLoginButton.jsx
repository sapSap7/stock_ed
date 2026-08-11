import { useEffect, useRef } from 'react'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID
const SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

function loadGoogleScript() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve()
      return
    }
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`)
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('Failed to load Google Sign-In script')))
      return
    }
    const script = document.createElement('script')
    script.src = SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Google Sign-In script'))
    document.head.appendChild(script)
  })
}

function GoogleLoginButton({ onCredential }) {
  const buttonRef = useRef(null)

  useEffect(() => {
    let cancelled = false

    loadGoogleScript().then(() => {
      if (cancelled || !buttonRef.current) return
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (response) => onCredential(response.credential),
      })
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'filled_black',
        size: 'medium',
        shape: 'pill',
      })
    })

    return () => {
      cancelled = true
    }
  }, [onCredential])

  if (!CLIENT_ID) {
    return <p className="text-xs text-red-400">Missing VITE_GOOGLE_CLIENT_ID in .env</p>
  }

  return <div ref={buttonRef} />
}

export default GoogleLoginButton
