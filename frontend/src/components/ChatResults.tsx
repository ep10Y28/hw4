import { useEffect, useRef } from 'react'
import { useChatResults } from '../chatResults.tsx'
import ProductCard from './ProductCard.tsx'

// Shows the chat agent's latest product matches as cards at the top of the
// page, on whatever page the shopper is on. Clicking a card opens the normal
// single-item page and folds this section into a slim bar.
export default function ChatResults() {
  const { label, products, query, version, expanded, setExpanded, clear } = useChatResults()
  const ref = useRef<HTMLElement>(null)

  // New results: bring them into view.
  useEffect(() => {
    if (version > 0 && ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [version])

  if (products.length === 0) return null

  const count = `${products.length} ${products.length === 1 ? 'item' : 'items'}`

  if (!expanded) {
    return (
      <section className="chat-results collapsed" ref={ref} aria-label="Chat results">
        <div className="chat-results-bar">
          <span>
            <strong>From your chat:</strong> {label} · {count}
          </span>
          <div className="chat-results-actions">
            <button onClick={() => setExpanded(true)}>Show</button>
            <button onClick={clear} aria-label="Dismiss chat results">
              ×
            </button>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="chat-results" ref={ref} aria-label="Chat results" key={version}>
      <div className="chat-results-inner">
        <div className="chat-results-head">
          <div>
            <p className="results-kicker">Pulled from the back room for you</p>
            <h2>{label}</h2>
            {query && <p className="muted small">You asked: “{query}” · {count}</p>}
          </div>
          <div className="chat-results-actions">
            <button onClick={() => setExpanded(false)}>Hide</button>
            <button onClick={clear}>Clear</button>
          </div>
        </div>
        <div className="grid">
          {products.map((p) => (
            <ProductCard key={p.product_id} product={p} onOpen={() => setExpanded(false)} />
          ))}
        </div>
      </div>
    </section>
  )
}
