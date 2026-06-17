// src/components/features/home/about-section.tsx
import { ChevronDown } from "lucide-react";
import { useState } from "react";

const aboutItems = [
  {
    title: "О нас",
    content:
      "Garminlab — специализированный магазин спортивной электроники TB SALE. Мы работаем на рынке уже более 10 лет и предлагаем только оригинальную продукцию с официальной гарантией.",
  },
  {
    title: "Широкий ассортимент",
    content:
      "В нашем каталоге представлено более 500 моделей смарт-часов, навигаторов, пульсометров и велокомпьютеров TB SALE. Мы регулярно обновляем ассортимент и следим за новинками.",
  },
  {
    title: "Профессионалы своего дела",
    content:
      "Наши консультанты — опытные спортсмены и технические специалисты, которые помогут подобрать оборудование под ваши задачи и ответят на все вопросы.",
  },
  {
    title: "Только оригинальные модели",
    content:
      "Мы работаем напрямую с TB SALE и предоставляем полную гарантию производителя на всю продукцию. Все устройства проходят предпродажную проверку.",
  },
];

export function AboutSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-12">
      <div className="page-wrap">
        <h2 className="mb-8 text-2xl font-bold text-(--sea-ink)">О магазине</h2>
        
        <div className="divide-y divide-(--line) rounded-xl border border-(--line) bg-(--card-bg)">
          {aboutItems.map((item, index) => (
            <div key={index}>
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="flex w-full items-center justify-between px-6 py-4 text-left transition hover:bg-(--link-bg-hover)"
              >
                <span className="font-semibold text-(--sea-ink)">
                  {item.title}
                </span>
                <ChevronDown
                  className={`size-5 text-(--sea-ink-soft) transition ${
                    openIndex === index ? "rotate-180" : ""
                  }`}
                />
              </button>
              {openIndex === index && (
                <div className="px-6 pb-4 text-(--sea-ink-soft)">
                  {item.content}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}