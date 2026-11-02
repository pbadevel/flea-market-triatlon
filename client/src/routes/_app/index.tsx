import { Bestsellers, HeroHome } from '@/components/features/home'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

export const Route = createFileRoute('/_app/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])

  const handleCategoryClick = (key: string) => {
    setSelectedCategories((prev) => (prev.includes(key) ? [] : [key]))
  }

  return (
    <div className="w-full max-w-full overflow-x-hidden">
      <HeroHome onCategoryClick={handleCategoryClick} />
      <div id="catalog">
        <Bestsellers categoriesOverride={selectedCategories} />
      </div>
    </div>
  )
}
