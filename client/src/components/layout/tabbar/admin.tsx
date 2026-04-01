import {
  BriefcaseIcon,
  GiftIcon,
  HomeIcon,
  LoaderPinwheel,
  User2Icon,
} from "lucide-react";

import { Tabbar } from "./tabbar";

export const AdminTabbar = () => {
  const tabs = [
    {
      to: "/admin/users",
      name: "Юзеры",
      value: "users",
      icon: <User2Icon />,
    },
    {
      to: "/admin/rolls",
      name: "Rolls",
      value: "rolls",
      icon: <LoaderPinwheel />,
    },
    {
      to: "/admin",
      name: "Главная",
      value: "main",
      icon: <HomeIcon />,
    },
    {
      to: "/admin/items",
      name: "Гифты",
      value: "gifts",
      icon: <GiftIcon />,
    },
    {
      to: "/admin/cases",
      name: "Кейсы",
      value: "cases",
      icon: <BriefcaseIcon />,
    },
  ];

  return <Tabbar tabs={tabs} />;
};
