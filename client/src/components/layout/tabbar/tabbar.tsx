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
    <div className="fixed bottom-4 left-0 right-0 z-50 w-screen px-4 lg:hidden">
      <div className="mx-auto flex max-w-md items-center justify-center">
        <div className="flex px-5 items-center gap-1 rounded-2xl border border-white/20 bg-white/10 py-2 shadow-2xl backdrop-blur-xl">
          {tabs.map((tab) => (
            <Link
              to={tab.to}
              key={tab.value}
              className={classNames(
                "relative flex flex-col items-center justify-center gap-1 rounded-xl p-2.5 transition-all duration-200 active:scale-90",
                location.pathname === tab.to
                  ? "bg-blue-500/20 text-blue-600 "
                  : "text-stone-600 dark:text-stone-400 hover:bg-stone-200/50 "
              )}
            >
              <div className="[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-6">
                {tab.icon}
              </div>
              <span className="text-[10px] font-medium">{tab.name}</span>
              
              {/* Indicator dot for active tab */}
              {location.pathname === tab.to && (
                <div className="absolute -bottom-1 h-1 w-1 rounded-full bg-blue-60" />
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};