// tabbar.tsx
import { Link, useLocation } from "@tanstack/react-router";
import { classNames } from "@/lib/css";

export const Tabbar: React.FC<{
  tabs: {
    to: string;
    name: string;
    value: string;
    icon: React.ReactNode;
  }[];
}> = ({ tabs }) => {
  const location = useLocation();

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 w-screen border-t-blue-300 border-t backdrop-blur-xl bg-(--bg-base) lg:hidden">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-around px-2">
        {tabs.map((tab) => (
          <Link
            to={tab.to}
            key={tab.value}
            className={classNames(
              "relative flex flex-col items-center justify-center gap-1 rounded-lg p-2 transition-all active:scale-95",
              location.pathname === tab.to
                ? "text-blue-600 dark:text-blue-400"
                : "text-stone-500 dark:text-stone-400 hover:text-stone-700 dark:hover:text-stone-300"
            )}
          >
            {location.pathname === tab.to && (
              <div className="absolute -top-0.5 left-1/2 h-1 w-8 -translate-x-1/2 rounded-full bg-blue-600 dark:bg-blue-400" />
            )}
            <div className="[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-5">
              {tab.icon}
            </div>
            <span className="text-[11px] font-medium">{tab.name}</span>
          </Link>
        ))}
      </div>
    </div>
  );
};