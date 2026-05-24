import { queryOptions } from "@tanstack/react-query";
import { apiRequest } from "./api-request";
import { FILTER_ENDPOINT } from "./endpoints";

export interface FilterConfig {
  categories: { key: string; label: string; items: { key: string; label: string }[] }[];
  countries: { key: string; name: string; flag: string }[];
  conditions: { key: string; label: string }[];
  sizes: string[];
  ad_types: { key: string; label: string }[];
}

export const fetchFilters = async (): Promise<FilterConfig> => {
  return apiRequest<FilterConfig>(FILTER_ENDPOINT, { method: "GET" });
};

export const filtersQueryOptions = () =>
  queryOptions({
    queryKey: ["filters"],
    queryFn: fetchFilters,
    staleTime: 60 * 60 * 1000, // 1 час
  });