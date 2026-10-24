import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

// Start each new page at the top, so a card clicked halfway down the page
// opens its product page from the top.
export default function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}
