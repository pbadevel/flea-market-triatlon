import type { ReactNode } from "react";
import { toast as originalToast, type ToasterProps } from "sonner";
import {
  hapticFeedback,
  type NotificationHapticFeedbackType,
} from "@telegram-apps/sdk-react";

type ToastFunction = typeof originalToast;

const beforeToast = (type: NotificationHapticFeedbackType) => {
  hapticFeedback.notificationOccurred.ifAvailable(type);
};

const handler: ProxyHandler<ToastFunction> = {
  apply(
    target: ToastFunction,
    thisArg: any,
    argArray: any[],
  ): ReturnType<ToastFunction> {
    beforeToast("success");
    return Reflect.apply(target, thisArg, argArray);
  },
  get(target: ToastFunction, prop: string | symbol, receiver: any) {
    const value = Reflect.get(target, prop, receiver);
    if (typeof value === "function") {
      const methodType = value as (
        message: ReactNode,
        options?: ToasterProps,
      ) => string | number;
      return new Proxy(methodType, {
        apply(
          methodTarget: typeof methodType,
          methodThisArg: any,
          methodArgs: any[],
        ): ReturnType<typeof methodType> {
          beforeToast(
            prop === "warning"
              ? "warning"
              : prop === "error"
                ? "error"
                : "success",
          );
          return Reflect.apply(methodTarget, methodThisArg, methodArgs);
        },
      });
    }
    return value;
  },
};

const proxiedToast: ToastFunction = new Proxy(originalToast, handler);

export { proxiedToast as toast };
