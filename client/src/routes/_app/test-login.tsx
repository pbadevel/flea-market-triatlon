// src/routes/test-login.tsx
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { testLoginFn } from "@/lib/session";

export const Route = createFileRoute("/_app/test-login")({
  component: TestLoginPage,
});

function TestLoginPage() {
  const navigate = useNavigate();
  
  const loginMutation = useMutation({
    mutationFn: () => testLoginFn(),
    onSuccess: () => {
      navigate({ to: "/" });
    },
    onError: (error) => {
      console.error("Login failed:", error);
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-bold">Тестовый вход</h1>
        <p className="text-sm text-gray-500">
          Только для разработки!
        </p>
        <button
          onClick={() => loginMutation.mutate()}
          disabled={loginMutation.isPending}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
        >
          {loginMutation.isPending ? "Вход..." : "Войти как тестовый пользователь"}
        </button>
        {loginMutation.isError && (
          <p className="text-red-500 text-sm">
            Ошибка: {loginMutation.error.message}
          </p>
        )}
      </div>
    </div>
  );
}