import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// ✅ Добавили 'all' в тип
export type Country = 'all' | 'ru' | 'kz' | 'kg';

interface CountryContextType {
  country: Country;
  setCountry: (country: Country) => void;
  countryName: string;
}

const CountryContext = createContext<CountryContextType | undefined>(undefined);

const countries: Record<Country, { name: string; flag: string; count?: number }> = {
  all: { name: 'Все', flag: '' },
  ru: { name: 'Россия', flag: '🇷🇺' },
  kz: { name: 'Казахстан', flag: '🇰🇿' },
  kg: { name: 'Кыргызстан', flag: '🇰🇬' },
};

export function CountryProvider({ children }: { children: ReactNode }) {
  const [country, setCountryState] = useState<Country>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('country') as Country;
      // ✅ Проверяем, что значение валидно
      return stored && countries[stored] ? stored : 'all';
    }
    return 'all';
  });

  useEffect(() => {
    localStorage.setItem('country', country);
  }, [country]);

  const setCountry = (newCountry: Country) => {
    setCountryState(newCountry);
    console.log(`Country changed to: ${countries[newCountry].name}`);
  };

  return (
    <CountryContext.Provider value={{ 
      country, 
      setCountry, 
      countryName: countries[country].name 
    }}>
      {children}
    </CountryContext.Provider>
  );
}

export function useCountry() {
  const context = useContext(CountryContext);
  if (!context) {
    throw new Error('useCountry must be used within CountryProvider');
  }
  return context;
}

export { countries };