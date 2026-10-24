import { Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar.tsx'
import Footer from './components/Footer.tsx'
import ChatWidget from './components/ChatWidget.tsx'
import ChatResults from './components/ChatResults.tsx'
import ScrollToTop from './components/ScrollToTop.tsx'
import Home from './pages/Home.tsx'
import Products from './pages/Products.tsx'
import ProductDetail from './pages/ProductDetail.tsx'
import About from './pages/About.tsx'
import Login from './pages/Login.tsx'
import CreateAccount from './pages/CreateAccount.tsx'
import NotFound from './pages/NotFound.tsx'

export default function App() {
  return (
    <div className="app">
      <ScrollToTop />
      <NavBar />
      <main className="main">
        <ChatResults />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}
