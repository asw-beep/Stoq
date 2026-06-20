"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type {
  AdminUser,
  Forecast,
  ForecastModel,
  Holding,
  MarketOverviewItem,
  NewsArticle,
  Page,
  PortfolioDetail,
  PortfolioSummary,
  PriceBar,
  PriceRange,
  Stock,
  StockDetail,
  User,
} from "@/lib/types";

const enc = encodeURIComponent;

// ---- auth ----
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me"),
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (creds: { email: string; password: string }) =>
      apiFetch<{ user: User | null }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(creds),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (creds: { email: string; password: string }) =>
      apiFetch<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(creds),
      }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => qc.clear(),
  });
}

// ---- admin ----
export function useAdminUsers(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["admin-users", limit, offset],
    queryFn: () =>
      apiFetch<Page<AdminUser>>(`/admin/users?limit=${limit}&offset=${offset}`),
    retry: false, // a 403 (non-admin) shouldn't be retried
  });
}

// ---- market / stocks ----
export function useMarketOverview() {
  return useQuery({
    queryKey: ["market-overview"],
    queryFn: () => apiFetch<MarketOverviewItem[]>("/market/overview"),
  });
}

export function useStocks(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["stocks", limit, offset],
    queryFn: () => apiFetch<Page<Stock>>(`/stocks?limit=${limit}&offset=${offset}`),
  });
}

export function useStock(symbol: string) {
  return useQuery({
    queryKey: ["stock", symbol],
    queryFn: () => apiFetch<StockDetail>(`/stocks/${enc(symbol)}`),
    enabled: !!symbol,
  });
}

export function usePrices(symbol: string, range: PriceRange = "1y") {
  return useQuery({
    queryKey: ["prices", symbol, range],
    queryFn: () => apiFetch<PriceBar[]>(`/stocks/${enc(symbol)}/prices?range=${range}`),
    enabled: !!symbol,
  });
}

// ---- forecasts ----
export function useForecasts(symbol: string, model?: ForecastModel) {
  const q = model ? `?model=${model}` : "";
  return useQuery({
    queryKey: ["forecasts", symbol, model ?? "all"],
    queryFn: () => apiFetch<Forecast[]>(`/stocks/${enc(symbol)}/forecasts${q}`),
    enabled: !!symbol,
  });
}

export function useGenerateForecast(symbol: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (model: ForecastModel) =>
      apiFetch<Forecast[]>(`/stocks/${enc(symbol)}/forecasts?model=${model}`, {
        method: "POST",
        body: JSON.stringify({ horizons: [1, 7, 30] }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forecasts", symbol] }),
  });
}

// ---- news / sentiment ----
export function useNews(symbol: string) {
  return useQuery({
    queryKey: ["news", symbol],
    queryFn: () => apiFetch<NewsArticle[]>(`/stocks/${enc(symbol)}/news?limit=50`),
    enabled: !!symbol,
  });
}

export function useIngestNews(symbol: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<unknown>(`/stocks/${enc(symbol)}/news?days=7`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["news", symbol] }),
  });
}

// ---- portfolios ----
export function usePortfolios(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["portfolios", limit, offset],
    queryFn: () =>
      apiFetch<Page<PortfolioSummary>>(`/portfolios?limit=${limit}&offset=${offset}`),
  });
}

export function usePortfolio(id: number) {
  return useQuery({
    queryKey: ["portfolio", id],
    queryFn: () => apiFetch<PortfolioDetail>(`/portfolios/${id}`),
    enabled: Number.isFinite(id),
  });
}

export function useCreatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<PortfolioSummary>("/portfolios", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolios"] }),
  });
}

export function useDeletePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/portfolios/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolios"] }),
  });
}

export function useAddHolding(portfolioId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      symbol: string;
      shares: number;
      purchase_price: number;
    }) =>
      apiFetch<Holding>(`/portfolios/${portfolioId}/holdings`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio", portfolioId] }),
  });
}

export function useRemoveHolding(portfolioId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (holdingId: number) =>
      apiFetch<void>(`/portfolios/${portfolioId}/holdings/${holdingId}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio", portfolioId] }),
  });
}
