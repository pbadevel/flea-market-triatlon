console.log(import.meta.env.VITE_BACKEND_DOMAIN)
export const BASE_URL = `${import.meta.env.VITE_BACKEND_DOMAIN}/v1`;


export const ADS_LIST_ENDPOINT = `${BASE_URL}/ads`;
export const FILTER_ENDPOINT = `${BASE_URL}/filters`;
export const PRODUCT_ENDPOINT = `${BASE_URL}/products`;