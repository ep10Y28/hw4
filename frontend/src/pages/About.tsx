import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="page narrow">
      <h1>We're Campus Customs.</h1>
      <p className="lead">
        We run Yale Bulldog Blue, an officially licensed Yale shop on Broadway in New Haven. Our
        customers are students, alumni, parents, and fans who want to wear their Yale pride.
      </p>

      <h2>How we do things</h2>
      <p>
        We keep it simple: good gear, honest prices, and straight answers. We'd rather tell you a
        size is sold out than sell you the wrong one. Everything in the store is something we'd wear
        ourselves, from the heavyweight crewneck you'll keep for ten years to the Harvard-Yale tee
        you'll wear on game day.
      </p>

      <h2>Who we make it for</h2>
      <ul className="checklist">
        <li>
          <strong>Students</strong> who need something warm for an 8 a.m. class.
        </li>
        <li>
          <strong>Alumni</strong> who want their class year and college on something that lasts.
        </li>
        <li>
          <strong>Families</strong> showing up for move-in, Family Weekend, or Commencement.
        </li>
        <li>
          <strong>Fans</strong> who never miss The Game.
        </li>
      </ul>

      <h2>Visit us</h2>
      <div className="visit">
        <div>
          <strong>Yale Bulldog Blue by Campus Customs</strong>
          <p>57 Broadway, New Haven, CT 06511</p>
        </div>
        <Link to="/products" className="btn btn-dark">
          Shop online
        </Link>
      </div>
    </div>
  )
}
