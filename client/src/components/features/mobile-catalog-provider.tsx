// src/components/features/home/mobile-catalog-provider.tsx
import { createContext, useContext, useState, ReactNode } from "react";

interface MobileCatalogContextType {
  isOpen: boolean;
  open: () => void;
  close: () => void;
}

const MobileCatalogContext = createContext<MobileCatalogContextType | undefined>(undefined);

export function MobileCatalogProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <MobileCatalogContext.Provider
      value={{
        isOpen,
        open: () => setIsOpen(true),
        close: () => setIsOpen(false),
      }}
    >
      {children}
    </MobileCatalogContext.Provider>
  );
}

export function useMobileCatalog() {
  const context = useContext(MobileCatalogContext);
  if (context === undefined) {
    throw new Error("useMobileCatalog must be used within a MobileCatalogProvider");
  }
  return context;
}