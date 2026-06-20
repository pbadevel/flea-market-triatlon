export interface AdminStats {
  total_users: number;
  total_ads: number;
  pending_ads: number;
  approved_ads: number;
  rejected_ads: number;
  ads_by_status: Record<string, number>;
}

export interface AdminAd {
  id: number;
  title: string;
  price: number;
  cover_url: string | null;
  city: string;
  country?: string;
  category: string;
  subcategory?: string;
  condition: string;
  status: 'pending' | 'approved' | 'rejected' | 'sold' | 'removed';
  rejection_reason?: string;
  created_at: string;
  channel_message_id?: number;
}

export interface AdminAdsResponse {
  data: AdminAd[];
  total: number;
  page: number;
  limit: number;
}

export type ModerationAction = 'approve' | 'reject';

export interface ModerateAdPayload {
  action: ModerationAction;
  rejection_reason?: string;
}


export interface AdminAdPhoto {
  id: number;
  file_id: string | null;
  storage_path: string | null;
  position: number;
  url?: string; // Вычисляемое поле
}

export interface AdminSeller {
  id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  is_trusted_seller: boolean;
  is_moderator: boolean;
  rating: number;
  review_count: number;
  reviews: Array<{
    id: number;
    reviewer_username: string | null;
    reviewer_user_id: number;
    rating: number;
    comment: string | null;
    created_at: string;
  }>;
}

// --- Categories ---
export interface SubcategoryOut {
  key: string;
  name: string;
  icon: string | null;
  display_order: number;
  requires_size: boolean;
  is_active: boolean;
  group_key: string | null;
}

export interface SubcategoryGroupOut {
  key: string;
  name: string;
  icon: string | null;
  display_order: number;
  subcategories: SubcategoryOut[];
}

export interface Category {
  key: string;
  name: string;
  icon: string | null;
  display_order: number;
  is_active: boolean;
  available_for: string | null;
  groups: SubcategoryGroupOut[];
  subcategories: SubcategoryOut[];
}

export interface CategoryCreate {
  key: string;
  name: string;
  icon?: string;
  display_order?: number;
  available_for?: string;
}

export interface Subcategory {
  key: string;
  name: string;
  icon: string | null;
  display_order: number;
  requires_size: boolean;
  is_active: boolean;
  group_key: string | null;
}

export interface SubcategoryCreate {
  key: string;
  name: string;
  category_key: string;
  group_key?: string;
  icon?: string;
  display_order?: number;
  requires_size?: boolean;
}

// --- Users (admin) ---
export interface AdminUser {
  id: number;
  tg_user_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  role: string;
  is_trusted_seller: boolean;
  phone: string | null;
  created_at: string;
}

export interface AdminUsersResponse {
  data: AdminUser[];
  total: number;
  page: number;
  limit: number;
}

export interface AdminAdDetail extends AdminAd {
  size?: string;
  description?: string;
  ad_type: string;
  delivery_method?: string;
  contact_method: string;
  published_at?: string;
  photos: AdminAdPhoto[];
  seller?: AdminSeller;
  tags: string[];
}