// TypeScript mirrors of the backend Pydantic schemas (see docs/API_Spec.md).

export interface User {
  id: number;
  email: string;
  role: string;
}

// Admin-only view of a user row (GET /admin/users). Never includes the hash.
export interface AdminUser {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Stock {
  id: number;
  symbol: string;
  name?: string | null;
  sector?: string | null;
}

export interface StockDetail extends Stock {
  price_count: number;
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketOverviewItem {
  symbol: string;
  name?: string | null;
  sector?: string | null;
  latest_close?: number | null;
  previous_close?: number | null;
  change?: number | null;
  change_pct?: number | null;
}

export interface Forecast {
  forecast_date: string;
  target_date: string;
  model: string;
  direction?: number | null;       // 1 = up, 0 = down
  probability?: number | null;     // model confidence [0, 1]
  predicted_price?: number | null; // legacy
  confidence?: number | null;      // legacy
}

export interface Sentiment {
  sentiment: string;
  confidence: number;
}

export interface NewsArticle {
  id: number;
  title: string;
  source?: string | null;
  url?: string | null;
  published_at?: string | null;
  sentiment?: Sentiment | null;
}

export interface PortfolioSummary {
  id: number;
  name: string;
  holding_count: number;
}

export interface Holding {
  id: number;
  symbol: string;
  shares: number;
  purchase_price: number;
  current_price?: number | null;
  market_value?: number | null;
  cost_basis: number;
  gain_loss?: number | null;
}

export interface PortfolioDetail {
  id: number;
  name: string;
  holdings: Holding[];
  total_cost: number;
  total_value?: number | null;
  total_gain_loss?: number | null;
}

export type PriceRange = "1m" | "3m" | "6m" | "1y" | "max";
export type ForecastModel = "xgboost";
