import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.tsx'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <span className="brand-mark">CC</span>
          <span className="brand-text">
            Campus Customs
            <small>Officially licensed Yale gear</small>
          </span>
        </Link>
        <nav className="nav-links" aria-label="Main">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className="nav-link">
              {l.label}
            </NavLink>
          ))}
          {ready && user ? (
            <>
              <span className="nav-user">Hi, {user.first_name}</span>
              <button className="nav-link nav-button" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="nav-link">
                Log in
              </NavLink>
              <NavLink to="/create-account" className="nav-link nav-cta">
                Create account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
