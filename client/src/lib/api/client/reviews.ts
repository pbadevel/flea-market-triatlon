import { apiRequest } from '../api-request'
import { REVIEWS_ENDPOINT } from '../endpoints'
import type { ReviewCreate, Review } from '@/types/products'


export const createReview = async (
  token: string,
  data: ReviewCreate,
): Promise<Review> => {
  return apiRequest<Review>(REVIEWS_ENDPOINT, {
    method: 'POST',
    token,
    body: data,
  })
}
