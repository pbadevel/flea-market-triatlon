/* eslint-disable  @typescript-eslint/no-explicit-any */

export function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

export function classNames(...values: any[]): string {
  return values
    .map((value) => {
      if (typeof value === "string") {
        return value;
      }

      if (isRecord(value)) {
        return classNames(
          Object.entries(value).map((entry) => entry[1] && entry[0]),
        );
      }

      if (Array.isArray(value)) {
        return classNames(...value);
      }
    })
    .filter(Boolean)
    .join(" ");
}

type UnionStringKeys<U> = U extends U
  ? { [K in keyof U]-?: U[K] extends string | undefined ? K : never }[keyof U]
  : never;

type UnionRequiredKeys<U> = U extends U
  ? {
      [K in UnionStringKeys<U>]: object extends Pick<U, K> ? never : K;
    }[UnionStringKeys<U>]
  : never;

type UnionOptionalKeys<U> = Exclude<UnionStringKeys<U>, UnionRequiredKeys<U>>;

export type MergeClassNames<Tuple extends any[]> =
  // Removes all types from union that will be ignored by the mergeClassNames function.
  Exclude<
    Tuple[number],
    number | string | null | undefined | any[] | boolean
  > extends infer Union
    ? { [K in UnionRequiredKeys<Union>]: string } & {
        [K in UnionOptionalKeys<Union>]?: string;
      }
    : never;

export function mergeClassNames<T extends any[]>(
  ...partials: T
): MergeClassNames<T> {
  return partials.reduce<MergeClassNames<T>>((acc, partial) => {
    if (isRecord(partial)) {
      Object.entries(partial).forEach(([key, value]) => {
        const className = classNames((acc as any)[key], value);
        if (className) {
          (acc as any)[key] = className;
        }
      });
    }
    return acc;
  }, {} as MergeClassNames<T>);
}
