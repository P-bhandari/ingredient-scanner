import { Route, Routes } from 'react-router-dom'
import { Header } from './components/Header'
import { BrowsePage } from './pages/BrowsePage'
import { ProductDetailPage } from './pages/ProductDetailPage'

export default function App() {
  return (
    <div className="min-h-screen bg-paper">
      <Header />
      <Routes>
        <Route path="/" element={<BrowsePage />} />
        <Route path="/product/:id" element={<ProductDetailPage />} />
      </Routes>
    </div>
  )
}
