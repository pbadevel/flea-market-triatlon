export class AppError extends Error {
  constructor(detail: string) {
    super(detail);
    this.name = "AppError";
  }
}

export class ResourceNotFound extends AppError {
  constructor(detail: string) {
    super(detail);
    this.name = "ResourceNotFound";
  }
}

type ApiRequestOptions = {
  method?: "GET" | "POST" | "DELETE" | "PUT" | "PATCH";
  token?: string;
  body?: object | FormData;
  headers?: HeadersInit;
  timeout?: number;
};

const parseBody = (body?: object | FormData) => {
  if (body instanceof FormData) return body;
  if (!body) return;
  return JSON.stringify(body);
};

export const rawApiRequest = async <T>(
  url: RequestInfo | URL,
  init: RequestInit,
  timeout?: number,
): Promise<T> => {
  const response = await Promise.race<Response>([
    fetch(url, init),
    new Promise((_, reject): undefined => {
      setTimeout(() => reject(new Error("Request timeout")), timeout || 5000);
    }),
  ]);

  const json = await response.json();

  if (!response.ok) {
    const errorName = json["error"];
    const errorDetail = JSON.stringify(json["detail"]);

    if (json["error"] == "ResourceNotFound") {
      throw new ResourceNotFound(errorDetail);
    }

    throw new Error(`${errorName} - ${errorDetail}`);
  }

  return json;
};

const defaultHeaders = {
  Accept: "application/json",
  "Content-Type": "application/json",
};

export const apiRequest = async <T>(
  url: string,
  { method, token, body, headers, timeout }: ApiRequestOptions = {
    method: "GET",
  },
): Promise<T> => {
  const isFormData = body instanceof FormData;
  
  return await rawApiRequest(
    url,
    {
      method,
      body: isFormData ? body : parseBody(body),
      headers: isFormData
        ? {
            // Для FormData НЕ устанавливаем Content-Type - браузер сам добавит с boundary
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            Accept: "application/json",
            ...headers,
          }
        : {
            // Для JSON используем стандартные заголовки
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...defaultHeaders,
            ...headers,
          },
    },
    timeout,
  );
  // return await rawApiRequest(
  //   url,
  //   {
  //     method,
  //     body: parseBody(body),
  //     headers: token
  //       ? { Authorization: `Bearer ${token}`, ...defaultHeaders, ...headers }
  //       : { ...defaultHeaders, ...headers },
  //   },
  //   timeout,
  // );
};
