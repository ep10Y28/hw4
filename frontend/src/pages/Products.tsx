import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Product } from '../api.ts'
import { fetchProducts } from '../api.ts'
import ProductCard from '../components/ProductCard.tsx'

const CATEGORIES = ['Hoodies', 'Crewnecks', 'T-shirts', 'Quarter-zips', 'Jackets & fleece', 'Long sleeve']
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
type Sort = 'name' | 'price_low' | 'price_high'

// Problem 9: category buttons, sort, and "in stock in my size" filters.
// Filters live in the URL (?category=Hoodies&size=M&sort=price_low), so a
// filtered view can be bookmarked or shared and survives Back.
export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [params, setParams] = useSearchParams()

  const query = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const size = params.get('size') ?? ''
  const sort = (params.get('sort') as Sort) || 'name'

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  useEffect(() => {
    fetchProducts()
      .then((p) => {
        setProducts(p)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [])

  // How many products each category button would show, given the other filters.
  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const p of products) {
      if (size && !p.sizes_in_stock.includes(size)) continue
      c[p.category] = (c[p.category] ?? 0) + 1
    }
    return c
  }, [products, size])

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = products.filter((p) => {
      if (category && p.category !== category) return false
      if (size && !p.sizes_in_stock.includes(size)) return false
      if (q && ![p.name, p.garment_type, p.description, ...p.colors].join(' ').toLowerCase().includes(q)) return false
      return true
    })
    const sorted = [...list]
    if (sort === 'price_low') sorted.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    else if (sort === 'price_high') sorted.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    else sorted.sort((a, b) => a.name.localeCompare(b.name))
    return sorted
  }, [products, query, category, size, sort])

  const filtersOn = Boolean(query || category || size || sort !== 'name')

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Products</h1>
          <p className="muted">
            {status === 'ready' ? `${shown.length} of ${products.length} items` : 'Our full lineup'}
          </p>
        </div>
        <input
          className="search"
          type="search"
          placeholder="Search Berkeley, baseball, navy…"
          value={query}
          onChange={(e) => setParam('q', e.target.value)}
          aria-label="Search products"
        />
      </div>

      <div className="filters">
        <div className="chips-row" role="group" aria-label="Category">
          <button className={`filter-chip ${category === '' ? 'on' : ''}`} onClick={() => setParam('category', '')}>
            All
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c}
              className={`filter-chip ${category === c ? 'on' : ''}`}
              onClick={() => setParam('category', category === c ? '' : c)}
              aria-pressed={category === c}
            >
              {c} <span className="chip-count">{counts[c] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="filter-selects">
          <label>
            In stock in
            <select value={size} onChange={(e) => setParam('size', e.target.value)}>
              <option value="">Any size</option>
              {SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sort
            <select value={sort} onChange={(e) => setParam('sort', e.target.value === 'name' ? '' : e.target.value)}>
              <option value="name">Name (A–Z)</option>
              <option value="price_low">Price: low to high</option>
              <option value="price_high">Price: high to low</option>
            </select>
          </label>
          {filtersOn && (
            <button className="text-link clear-filters" onClick={() => setParams({}, { replace: true })}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      {status === 'loading' && <p className="muted">Loading products…</p>}
      {status === 'error' && (
        <p className="notice">We couldn't load products. Make sure the backend is running on port 8000.</p>
      )}
      {status === 'ready' && shown.length === 0 && (
        <p className="notice">
          Nothing matches those filters.{' '}
          <button className="text-link inline-btn" onClick={() => setParams({}, { replace: true })}>
            Clear filters
          </button>{' '}
          or ask the chat for something close.
        </p>
      )}

      <div className="grid">
        {shown.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </div>
  )
}
