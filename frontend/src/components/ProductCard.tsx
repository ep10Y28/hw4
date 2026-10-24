import { Link } from 'react-router-dom'
import { formatPrice, shortDescription } from '../api.ts'

// The fields a card needs. Both the Products page (full Product) and the chat
// results (ChatProduct) satisfy this, so both render the exact same card and
// link to the same single-item page.
export type CardProduct = {
  product_id: string
  name: string
  price: number
  image_url: string
  total_stock: number
  description?: string
  short_description?: string
}

type Props = {
  product: CardProduct
  onOpen?: () => void
}

// Presented like merch on a rack: the photo, with a kraft hang tag on a string
// carrying the name and price. Sold-out items get a crimson rubber stamp.
export default function ProductCard({ product, onOpen }: Props) {
  const soldOut = product.total_stock === 0
  const blurb = product.short_description ?? shortDescription(product.description ?? '')
  return (
    <Link to={`/products/${product.product_id}`} className={`card ${soldOut ? 'card-sold-out' : ''}`} onClick={onOpen}>
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="stamp">Sold out</span>}
      </div>
      <div className="tag">
        <span className="tag-hole" aria-hidden="true" />
        <div className="tag-top">
          <h3>{product.name}</h3>
          <span className="price">{formatPrice(product.price)}</span>
        </div>
        <p>{blurb}</p>
      </div>
    </Link>
  )
}
