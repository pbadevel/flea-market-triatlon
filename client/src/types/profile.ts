// src/types/profile.ts
export interface UserProfile {
  id: number;
  tg_user_id: number;
  username: string | null;  // Telegram username
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  email: string | null;  // Email
  is_email_verified: boolean;
  is_moderator: boolean;
  is_trusted_seller: boolean;
  agreed_to_terms: boolean;
  subscribed_to_channel: boolean;
  created_at: string;
}

export interface UserProfileUpdate {
  first_name?: string;
  last_name?: string;
  phone?: string;
  email?: string;
}

export interface UserStats {
  total_ads: number;
  active_ads: number;
  pending_ads: number;
  approved_ads: number;
  rejected_ads: number;
  sold_ads: number;
}