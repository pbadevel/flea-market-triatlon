// src/components/features/home/categories-grid.tsx
import { Link } from "@tanstack/react-router";
import { Eye } from "lucide-react";

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
    name: "Эхолоты",
    to: "/fishfinders",
    image: "https://static.insales-cdn.com/r/L_v0WZSnrtQ/rs:fit:1408:0:1/q:100/plain/images/articles/1/7032/113528/eho-01.jpg@webp",
    count: 29,
  },
  {
    name: "Велоэлектроника",
    to: "/bike",
    image: "https://ixbt.online/live/images/original/03/53/89/2021/06/05/eb4625f872.jpg?w=877",
    count: 89,
  },
];

export function CategoriesGrid() {
  return (
    <section className="py-8">
      <div className="page-wrap">
        <h2 className="mb-6 text-xl font-semibold text-(--sea-ink)">Категории</h2>
        
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((category) => (
            <Link
              key={category.to}
              to={category.to}
              className="group rounded-lg border border-(--line) bg-white p-3 hover:bg-(--foam)"
            >
              <div className="aspect-[4/3] overflow-hidden rounded-md bg-gray-50">
                <img
                  src={category.image}
                  alt={category.name}
                  className="h-full w-full object-cover transition group-hover:scale-105"
                />
              </div>
              <div className="mt-3">
                <h3 className="text-sm font-medium text-(--sea-ink)">
                  {category.name}
                </h3>
                <div className="mt-1 flex items-center gap-2 text-xs text-(--sea-ink-soft)">
                  <Eye className="size-3.5" />
                  <span>{category.count} товаров</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}