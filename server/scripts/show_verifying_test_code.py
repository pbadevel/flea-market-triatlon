import hashlib
import sys
import redis

# 1. Проверяем, передан ли аргумент командной строки
if len(sys.argv) < 2:
    print("Ошибка: Укажите номер телефона!")
    print("Пример использования: python t.py 79099696905")
    sys.exit(1)

# 2. Получаем номер телефона из аргументов
phone_input = sys.argv[1]

# Форматируем ключ: если плюс не передан, добавляем его в начало
if not phone_input.startswith('+'):
    phone_input = f"+{phone_input}"

redis_key = f"phone_verify:code:{phone_input}"
print(f"Ищем хэш для ключа: {redis_key}")

# 3. Подключаемся к Redis и получаем хэш
r = redis.Redis(db=2, decode_responses=True)
target = r.get(redis_key)

if not target:
    print(f"Ошибка: Код для номера {phone_input} не найден в Redis (возможно, срок действия истек).")
    sys.exit(1)

print('Stored hash:', target)
print('Запуск подбора кода (000000 - 999999)...')

# 4. Брутфорс хэша
for i in range(1_000_000):
    candidate = f'{i:06d}'
    if hashlib.sha256(candidate.encode()).hexdigest() == target:
        print(f'>>> CODE FOUND: {candidate}')
        break
else:
    print('Код не найден.')
2