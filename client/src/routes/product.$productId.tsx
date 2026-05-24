// routes/product.$productId.tsx
import { createFileRoute } from '@tanstack/react-router'
import { ProductDetail } from '@/components/features/product-detail'

export const Route = createFileRoute('/product/$productId')({
  component: ProductPage,
})

function ProductPage() {
  return <ProductDetail />
}