// src/components/features/home/reviews-map.tsx
export function ReviewsMap() {
  return (
    <section className="py-12">
      <div className="page-wrap">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Reviews */}
          <div>
            <h2 className="mb-6 text-2xl font-bold text-(--sea-ink)">
              Отзывы клиентов
            </h2>
            
            <div className="mb-6 flex items-center gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-4xl font-bold text-(--sea-ink)">5,0</span>
                  <div className="flex text-yellow-400">
                    {"★".repeat(5)}
                  </div>
                </div>
                <p className="text-sm text-(--sea-ink-soft)">
                  155 отзывов • 186 оценок
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-(--line) bg-(--card-bg) p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400" />
                    <div>
                      <p className="font-semibold text-(--sea-ink)">
                        Ралиф Хизбуллин
                      </p>
                      <p className="text-xs text-(--sea-ink-soft)">
                        10 января
                      </p>
                    </div>
                  </div>
                  <div className="text-yellow-400">{"★".repeat(5)}</div>
                </div>
                <p className="text-sm text-(--sea-ink-soft)">
                  Была срочность. Так как канун Нового года 28 декабря, а я себе
                  хотел сделать подарок на НГ. Случайно на одном из каналов
                  увидел этот магазин...
                </p>
              </div>

              <div className="rounded-xl border border-(--line) bg-(--card-bg) p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-400" />
                    <div>
                      <p className="font-semibold text-(--sea-ink)">
                        Татьяна К.
                      </p>
                      <p className="text-xs text-(--sea-ink-soft)">
                        19 ноября 2025
                      </p>
                    </div>
                  </div>
                  <div className="text-yellow-400">{"★".repeat(5)}</div>
                </div>
                <p className="text-sm text-(--sea-ink-soft)">
                  Отличный магазин! Профессиональная консультация, быстрый
                  ответ, помогли с выбором...
                </p>
              </div>
            </div>

            <button className="mt-4 w-full rounded-xl border border-(--line) bg-(--chip-bg) py-3 text-sm font-medium text-(--sea-ink) transition hover:bg-(--link-bg-hover)">
              Больше отзывов на Яндекс Картах
            </button>
          </div>

          {/* Map */}
          <div>
            <h2 className="mb-6 text-2xl font-bold text-(--sea-ink)">
              Мы на карте
            </h2>
            
            <div className="overflow-hidden rounded-2xl border border-(--line) bg-(--card-bg)">
              <div className="aspect-square w-full bg-(--chip-bg)">
                <div className="flex h-full items-center justify-center text-(--sea-ink-soft)">
                     <iframe src="https://yandex.ru/map-widget/v1/?ll=37.612536%2C55.743949&mode=poi&poi[point]=37.605233%2C55.747223&poi[uri]=ymapsbm1%3A%2F%2Forg%3Foid%3D1072168294&z=16" 
                      className="w-full h-full"></iframe>
                  
                </div>
              </div>
              
              {/* <div className="border-t border-(--line) p-4">
                <div className="space-y-2 text-sm">
                  <p className="font-semibold text-(--sea-ink)">
                    Garminlab
                  </p>
                  <p className="text-(--sea-ink-soft)">
                     Открыто до 19:00
                  </p>
                  <p className="text-(--sea-ink-soft)">
                    📍 Москва, улица Сущёвский Вал, 5, стр. 1А
                  </p>
                  <p className="text-(--sea-ink-soft)">
                    📞 +7 (999) 573-85-85
                  </p>
                  <p className="text-(--sea-ink-soft)">
                    🚇 Савёловская — 53 м
                  </p>
                </div>
              </div> */}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}