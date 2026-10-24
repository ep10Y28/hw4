import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { Product } from '../api.ts'
import { ApiError, fetchProduct, formatPrice } from '../api.ts'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'missing' | 'error'>('loading')

  useEffect(() => {
    setStatus('loading')
    fetchProduct(productId)
      .then((p) => {
        setProduct(p)
        setStatus('ready')
      })
      .catch((err) => setStatus(err instanceof ApiError && err.status === 404 ? 'missing' : 'error'))
  }, [productId])

  if (status === 'loading') return <div className="page muted">Loading…</div>
  if (status === 'missing' || status === 'error' || !product) {
    return (
      <div className="page narrow">
        <h1>{status === 'missing' ? "We couldn't find that item." : 'Something went wrong.'}</h1>
        <Link to="/products" className="text-link">
          ← Back to all products
        </Link>
      </div>
    )
  }

  const soldOut = product.total_stock === 0

  return (
    <div className="page">
      <Link to="/products" className="text-link back">
        ← All products
      </Link>
      <div className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow eyebrow-dark">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">
            <span className="tag-hole" aria-hidden="true" />
            {formatPrice(product.price)}
          </p>
          <p className="detail-desc">{product.description}</p>

          <h2 className="detail-label">Colors</h2>
          <div className="chips">
            {product.colors.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>

          <h2 className="detail-label">
            Sizes &amp; stock {soldOut && <span className="badge badge-out inline">Sold out</span>}
          </h2>
          <div className="sizes">
            {product.inventory?.map((s) => (
              <div key={s.size} className={`size ${s.quantity === 0 ? 'size-out' : s.quantity <= LOW_STOCK ? 'size-low' : ''}`}>
                <strong>{s.size}</strong>
                <span>
                  {s.quantity === 0
                    ? 'Sold out'
                    : s.quantity <= LOW_STOCK
                      ? `Only ${s.quantity} left`
                      : `${s.quantity} in stock`}
                </span>
              </div>
            ))}
          </div>
          <p className="muted small">
            Questions about fit or a color? Tap “Ask the counter” in the corner. It knows which item you're looking at.
          </p>
        </div>
      </div>
    </div>
  )
}
