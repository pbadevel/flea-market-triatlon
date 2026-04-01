// src/components/features/home/categories-grid.tsx
import { Link } from "@tanstack/react-router";

const categories = [
  {
    name: "Смарт-часы",
    to: "/smartwatches",
    image: "https://images.samsung.com/is/image/samsung/assets/ru/f2507/pcd/PCD_KV_Galaxy-Watch8_1440x640_pc.jpg?imwidth=1366",
    count: 156,
  },
  {
    name: "Навигаторы",
    to: "/navigators",
    image: "https://s4.stc.all.kpcdn.net/expert/wp-content/uploads/2021/11/nav-960x540.jpg",
    count: 42,
  },
  {
    name: "Пульсометры",
    to: "/heart-rate",
    image: "https://beguza.ru/wp-content/webp-express/webp-images/uploads/2017/01/polar-min.jpg.webp",
    count: 38,
  },
  {
    name: "Велокомпьютеры",
    to: "/bike-computers",
    image: "https://ixbt.online/live/images/original/03/53/89/2021/06/05/eb4625f872.jpg?w=877",
    count: 67,
  },
  {
    name: "Эхолоты",
    to: "/fishfinders",
    image: "https://static.insales-cdn.com/r/L_v0WZSnrtQ/rs:fit:1408:0:1/q:100/plain/images/articles/1/7032/113528/eho-01.jpg@webp",
    count: 29,
  },
];

export function CategoriesGrid() {
  return (
    <section className="py-12">
      <div className="page-wrap">
        <h2 className="mb-8 text-2xl font-bold text-(--sea-ink)">Блог</h2>
        
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((category) => (
            <Link
              key={category.to}
              to={category.to}
              className="group relative overflow-hidden rounded-2xl bg-(--card-bg)"
            >
              <div className="aspect-[16/9] overflow-hidden">
                <img
                  src={category.image}
                  alt={category.name}
                  className="h-full w-full object-cover transition group-hover:scale-105"
                />
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-6">
                <h3 className="mb-1 text-xl font-semibold text-white">
                  {category.name}
                </h3>
                <p className="text-sm text-white/80">
                  {category.count} товаров
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}