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
    <div className="fixed bottom-0 w-screen z-50 lg:hidden" style={{ paddingBottom: "var(--v-safe-area-inset-bottom, 0px)" }}>
      <div className="px-3 pb-2">
        <div
          className="mx-auto max-w-md rounded-[22px] border border-white/20"
          style={{
            background: "rgba(255, 255, 255, 0.72)",
            backdropFilter: "blur(20px) saturate(180%)",
            WebkitBackdropFilter: "blur(20px) saturate(180%)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.6)",
          }}
        >
          <div className="flex h-14 items-center justify-around px-2">
            {tabs.map((tab) => (
              <Link
                to={tab.to}
                key={tab.value}
                className={classNames(
                  "relative flex flex-col items-center justify-center gap-[2px] rounded-xl p-2 transition-all duration-200 active:scale-90",
                  location.pathname === tab.to
                    ? "text-(--palm)"
                    : "text-(--sea-ink-soft) hover:text-(--sea-ink)"
                )}
              >
                <div className={classNames(
                  "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-5 transition-transform duration-200",
                  location.pathname === tab.to ? "scale-110" : ""
                )}>
                  {tab.icon}
                </div>
                <span className={classNames(
                  "text-[10px]",
                  location.pathname === tab.to ? "font-semibold" : "font-medium"
                )}>{tab.name}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
