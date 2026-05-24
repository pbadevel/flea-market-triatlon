import {
  HeartIcon,
  HomeIcon,
  SearchIcon,
  ShoppingCartIcon,
  UserCircle,
} from "lucide-react";

import { Tabbar } from "./tabbar";

export const UserTabbar = () => {
  const tabs = [
    {
      to: "/",
      name: "Главная",
      value: "Home",
      icon: <HomeIcon />,
    },
    // {
    //   to: "/search",
    //   name: "Поиск",
    //   value: "Search",
    //   icon: <SearchIcon />,
    // },
    {
      to: "/basket",
      name: "Корзина",
      value: "Basket",
      icon: <ShoppingCartIcon />,
    },
    {
      to: "/favorite",
      name: "Избранное",
      value: "favorite",
      icon: <HeartIcon />,
    },
    {
      to: "/profile",
      name: "Профиль",
      value: "Help",
      icon: <UserCircle />,
    },
  ];

  return <Tabbar tabs={tabs} />;
};
