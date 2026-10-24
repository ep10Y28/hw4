import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <p className="footer-mark" aria-hidden="true">
        57 Broadway
      </p>
      <div className="footer-inner">
        <div>
          <strong>Campus Customs</strong>
          <p>Yale Bulldog Blue, 57 Broadway, New Haven, CT 06511</p>
        </div>
        <div className="footer-links">
          <Link to="/products">Shop</Link>
          <Link to="/about">About Us</Link>
          <Link to="/login">Log in</Link>
        </div>
      </div>
    </footer>
  )
}
