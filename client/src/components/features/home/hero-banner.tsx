// src/components/features/home/hero-banner.tsx
export function HeroBanner() {
  const advantages = [
    "10 лет на рынке",
    "Безупречная репутация",
    "Гибкая система скидок",
    "Гарантия от 12 месяцев",
    "Консультация лучших специалистов",
  ];

  return (
    <section className="relative overflow-hidden text-black">
      <div className="page-wrap grid gap-8 py-12 md:grid-cols-2 md:py-16 lg:gap-12">
        {/* Left content */}
        <div className="flex flex-col justify-center">
          <div className="mb-6">
            <h1 className="mb-2 text-4xl font-bold tracking-tight md:text-5xl">
              TB <span className="text-cyan-400">SALE</span>
            </h1>
            <p className="text-sm uppercase tracking-wider text-cyan-600 dark:text-white">
              ЛАБОРАТОРИЯ СПОРТИВНОЙ ЭЛЕКТРОНИКИ
            </p>
          </div>
          
          <ul className="space-y-3">
            {advantages.map((item, index) => (
              <li key={index} className="flex items-center gap-3 text-base dark:text-white md:text-lg">
                <span className="h-2 w-2 flex-shrink-0 rounded-full bg-cyan-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Right content - QR Code placeholder */}
        
      </div>
    </section>
  );
}