// src/types/admin.ts

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
    reviewer_tg_id: number;
    rating: number;
    comment: string | null;
    created_at: string;
  }>;
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