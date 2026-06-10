console.log(import.meta.env.VITE_BACKEND_DOMAIN)
export const BASE_URL = `${import.meta.env.VITE_BACKEND_DOMAIN}/v1`;


export const ADS_LIST_ENDPOINT = `${BASE_URL}/ads`;
export const AUTH_ENDPOINT = `${BASE_URL}/auth`;
export const FILTER_ENDPOINT = `${BASE_URL}/filters`;
export const PRODUCT_ENDPOINT = `${BASE_URL}/products`;
export const MY_ADS_ENDPOINT = `${BASE_URL}/ads/my`;
export const CREATE_AD_ENDPOINT = `${BASE_URL}/ads`;


// Admin
export const ADMIN_STATS_ENDPOINT = `${BASE_URL}/admin/stats`;
export const ADMIN_PENDING_ADS_ENDPOINT = `${BASE_URL}/admin/ads/pending`;
export const ADMIN_ALL_ADS_ENDPOINT = `${BASE_URL}/admin/ads/all`;
export const ADMIN_MODERATE_ENDPOINT = (adId: number) => `${BASE_URL}/admin/ads/${adId}/moderate`;
export const ADMIN_AD_DETAIL_ENDPOINT = (adId: number) => `${BASE_URL}/admin/ads/${adId}`;


// Auth
export const AUTH_TELEGRAM_INIT_ENDPOINT = `${BASE_URL}/auth/telegram/init`;
export const AUTH_TELEGRAM_STATUS_ENDPOINT = `${BASE_URL}/auth/telegram/status`;
export const AUTH_REGISTER_EMAIL_ENDPOINT = `${BASE_URL}/auth/register/email`;
export const AUTH_LOGIN_EMAIL_ENDPOINT = `${BASE_URL}/auth/login/email`;