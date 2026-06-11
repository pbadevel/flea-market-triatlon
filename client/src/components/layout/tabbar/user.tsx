// src/components/layout/user-tabbar.tsx
import {
  HomeIcon,
  PackageIcon,
  PlusIcon,
  UserCircle,
} from "lucide-react";
import { Tabbar } from "./tabbar";

// УБРАТЬ проверку авторизации из Tabbar
export const UserTabbar = () => {
  const tabs = [
    {
      to: "/",
      name: "Главная",
      value: "Home",
      icon: <HomeIcon />,
    },
    {
      to: "/create-ad",
      name: "Создать",
      value: "CreateAd",
      icon: <PlusIcon />,
    },
    {
      to: "/my-ads",
      name: "Мои",
      value: "MyAds",
      icon: <PackageIcon />,
    },
    {
      to: "/profile",
      name: "Профиль",
      value: "Profile",
      icon: <UserCircle />,
    },
  ];

  return <Tabbar tabs={tabs} />;
};