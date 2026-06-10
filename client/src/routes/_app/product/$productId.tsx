import { ProductDetail } from '@/components/features/product-detail'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/product/$productId')({
  component: ProductPage,
})

function ProductPage() {
  return <ProductDetail />
}1