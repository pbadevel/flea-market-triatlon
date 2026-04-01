import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import Footer from '@/components/features/Footer'
import Header from '@/components/features/Header'

import appCss from '@/styles.css?url'
import { seo } from "@/lib/seo";
import { UserTabbar } from '@/components/layout/tabbar'
import { MobileCatalogProvider } from '@/components/features/mobile-catalog-provider'
import { MobileCatalog } from '@/components/features/mobile-catalog-menu'


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
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <HeadContent />
      </head>
      <body className="font-sans antialiased [overflow-wrap:anywhere] selection:bg-[rgba(79,184,178,0.24)]">
        <MobileCatalogProvider>
          <Header />
          {children}
          <UserTabbar />
          <Footer />
          <MobileCatalog/>
        </MobileCatalogProvider>
        <Scripts />
      </body>
    </html>
  )
}
