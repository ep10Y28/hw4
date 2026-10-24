import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="page narrow">
      <h1>Page not found.</h1>
      <Link to="/" className="text-link">
        ← Back home
      </Link>
    </div>
  )
}
