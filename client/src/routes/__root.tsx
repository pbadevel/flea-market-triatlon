import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'
import Footer from '@/components/features/Footer'
import Header from '@/components/features/Header'

import appCss from '@/styles.css?url'
import { seo } from "@/lib/seo";
import { queryClient } from '@/lib/query'
import { UserTabbar } from '@/components/layout/tabbar'
import { MobileCatalogProvider } from '@/components/features/mobile-catalog-provider'
import { MobileCatalog } from '@/components/features/mobile-catalog-menu'
import { CountryProvider } from '@/contexts/CountryContext'
import { QueryClientProvider } from '@tanstack/react-query'


const THEME_INIT_SCRIPT = `(function(){try{var stored=window.localStorage.getItem('theme');var mode=(stored==='light'||stored==='dark'||stored==='auto')?stored:'auto';var prefersDark=window.matchMedia('(prefers-color-scheme: dark)').matches;var resolved=mode==='auto'?(prefersDark?'dark':'light'):mode;var root=document.documentElement;root.classList.remove('light','dark');root.classList.add(resolved);if(mode==='auto'){root.removeAttribute('data-theme')}else{root.setAttribute('data-theme',mode)}root.style.colorScheme=resolved;}catch(e){}})();`

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: "utf-8",
      },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1.0, user-scalable=no",
      },
      ...seo({
        title: "PBA SITE",
        description: "Best NFT Gift cases",
      }),
    ],
    links: [
      {
        rel: 'stylesheet',
        href: appCss,
      },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <QueryClientProvider client={queryClient}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <HeadContent />
      </head>
      <body className="font-sans antialiased [overflow-wrap:anywhere] selection:bg-[rgba(79,184,178,0.24)]">
        {/* <MobileCatalogProvider> */}
          {/* <CountryProvider> */}
            <Header />
              {children}
            <UserTabbar />
            {/* <Footer /> */}
          {/* </CountryProvider> */}
          {/* <MobileCatalog/> */}
        {/* </MobileCatalogProvider> */}
        <Scripts />
      </body>
      </QueryClientProvider>
    </html>
  )
}
