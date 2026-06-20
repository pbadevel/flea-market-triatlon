import { ProductDetail } from '@/components/features/product-detail'
import { createFileRoute } from '@tanstack/react-router'
import { verifySession } from '@/lib/session'

export const Route = createFileRoute('/_app/product/$productId')({
  loader: async () => {
    const session = await verifySession()
    return { token: session?.token }
  },
  component: ProductPage,
})

function ProductPage() {
  const { token } = Route.useLoaderData()
  return <ProductDetail token={token} />
}1