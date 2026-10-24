import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Product } from '../api.ts'
import { fetchProducts } from '../api.ts'
import ProductCard from '../components/ProductCard.tsx'
import StitchedWordmark from '../components/StitchedWordmark.tsx'

const FEATURED_IDS = [
  'basic-hoodie-big-yale',
  'baseball-left-chest-crewneck',
  '2025-yale-vs-harvard-t-shirt',
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  const [total, setTotal] = useState<number | null>(null)

  useEffect(() => {
    fetchProducts()
      .then((all) => {
        setTotal(all.length)
        const picks = FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter(
          (p): p is Product => Boolean(p),
        )
        const extra = all.filter((p) => p.total_stock > 0 && !FEATURED_IDS.includes(p.product_id))
        setFeatured([...picks, ...extra].slice(0, 4))
      })
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="hero-kicker">Officially licensed Yale gear from 57 Broadway, New Haven</p>
          <h1 className="hero-title">
            <StitchedWordmark lines={['BULLDOG', 'BLUE']} />
          </h1>
          <p className="hero-sub">
            Hoodies, crewnecks, tees, and quarter-zips for game days, early classes, and the walk across Old Campus in
            January. No filler, just pieces you'll actually wear.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light">
              Shop {total ?? 'all'} styles
            </Link>
            <Link to="/products?category=Hoodies" className="btn btn-ghost">
              Start with hoodies
            </Link>
          </div>
        </div>
        <div className="hero-seam" aria-hidden="true" />
      </section>

      <section className="section">
        <div className="values">
          <div>
            <h3>Officially licensed</h3>
            <p>Every piece is licensed by Yale. No knockoffs, no guesswork.</p>
          </div>
          <div>
            <h3>XS to XXL</h3>
            <p>Every style comes in six sizes, and each product page shows live stock for every one.</p>
          </div>
          <div>
            <h3>Straight answers</h3>
            <p>Ask the counter about price, color, or stock. If we don't have it, we'll tell you.</p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>On the counter this week</h2>
          <Link to="/products" className="text-link">
            See all products
          </Link>
        </div>
        <div className="grid">
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="section">
        <div className="band">
          <div>
            <h2>Come by the shop</h2>
            <p>57 Broadway, New Haven. Try it on, grab a gift, and say hi.</p>
          </div>
          <Link to="/about" className="btn btn-dark">
            Visit info
          </Link>
        </div>
      </section>
    </>
  )
}
