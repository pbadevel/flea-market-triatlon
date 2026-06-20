console.log(import.meta.env.VITE_BACKEND_DOMAIN)
export const BASE_URL = `${import.meta.env.VITE_BACKEND_DOMAIN}/v1`;


export const ADS_LIST_ENDPOINT = `${BASE_URL}/ads`;
export const AUTH_ENDPOINT = `${BASE_URL}/auth`;
export const FILTER_ENDPOINT = `${BASE_URL}/filters`;
export const PRODUCT_ENDPOINT = `${BASE_URL}/products`;
export const MY_ADS_ENDPOINT = `${BASE_URL}/ads/my`;
export const CREATE_AD_ENDPOINT = `${BASE_URL}/ads`;
export const REVIEWS_ENDPOINT = `${BASE_URL}/reviews`;


// Admin
export const ADMIN_STATS_ENDPOINT = `${BASE_URL}/admin/stats`;
export const ADMIN_PENDING_ADS_ENDPOINT = `${BASE_URL}/admin/ads/pending`;
export const ADMIN_ALL_ADS_ENDPOINT = `${BASE_URL}/admin/ads/all`;
export const ADMIN_MODERATE_ENDPOINT = (adId: number) => `${BASE_URL}/admin/ads/${adId}/moderate`;
export const ADMIN_AD_DETAIL_ENDPOINT = (adId: number) => `${BASE_URL}/admin/ads/${adId}`;


// Admin Categories
export const ADMIN_CATEGORIES_ENDPOINT = `${BASE_URL}/admin/categories`;
export const ADMIN_CATEGORIES_SUBCATEGORIES_ENDPOINT = `${BASE_URL}/admin/categories/subcategories`;

// Admin Users
export const ADMIN_USERS_ENDPOINT = `${BASE_URL}/admin/users`;
export const ADMIN_USER_ADS_ENDPOINT = (userId: number) => `${ADMIN_USERS_ENDPOINT}/${userId}/ads`;
export const ADMIN_USER_AD_STATUS_ENDPOINT = (userId: number, adId: number) => `${ADMIN_USERS_ENDPOINT}/${userId}/ads/${adId}/status`;
export const ADMIN_USER_MAKE_ADMIN_ENDPOINT = (userId: number) => `${ADMIN_USERS_ENDPOINT}/${userId}/make-admin`;

// Auth
export const AUTH_TELEGRAM_INIT_ENDPOINT = `${BASE_URL}/auth/telegram/init`;
export const AUTH_TELEGRAM_STATUS_ENDPOINT = `${BASE_URL}/auth/telegram/status`;
export const AUTH_REGISTER_EMAIL_ENDPOINT = `${BASE_URL}/auth/register/email`;
export const AUTH_LOGIN_EMAIL_ENDPOINT = `${BASE_URL}/auth/login/email`;
export const AUTH_RESEND_CONFIRM_ENDPOINT = `${BASE_URL}/auth/resend-confirmation`;

// PROFILE
export const PROFILE_ME_ENDPOINT = `${BASE_URL}/users/me`;
export const PROFILE_STATS_ENDPOINT = `${BASE_URL}/users/me/stats`;