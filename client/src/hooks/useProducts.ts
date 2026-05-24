// src/hooks/useProducts.ts
import { useQuery } from '@tanstack/react-query';
import { useCountry } from '@/contexts/CountryContext';

export function useProducts() {
  const { country } = useCountry();

  return useQuery({
    queryKey: ['products', country],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (country !== 'all') {
        params.append('country', country);
      }
      
      const response = await fetch(`/api/products?${params}`);
      return response.json();
    },
  });
}