import { AboutSection, Bestsellers, CategoriesGrid, HeroBanner, ReviewsMap } from '@/components/features/home'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: App })

function App() {
  return (
    <div className="min-h-screen">
      <HeroBanner />
      <Bestsellers />
      <CategoriesGrid />
      <AboutSection />
      <ReviewsMap />
    </div>
  )
}
