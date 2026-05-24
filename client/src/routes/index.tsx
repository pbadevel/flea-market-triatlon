import { AboutSection, Bestsellers, ReviewsMap } from '@/components/features/home'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: App })

function App() {
  return (
    <div className="min-h-screen">
      <Bestsellers />
      {/* <AboutSection /> */}
      {/* <ReviewsMap /> */}
    </div>
  )
}
