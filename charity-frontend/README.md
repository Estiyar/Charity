# е-Көмек — Frontend (React + Tailwind)

Публичная часть платформы: главная, каталог, карточка сбора и демо-пожертвование.

## Стек
- React + Vite
- Tailwind CSS
- React Router

## Запуск
1. Установить зависимости:
   ```
   npm install
   ```
2. Скопировать `.env.example` в `.env` (при необходимости изменить URL API).
3. Запустить API gateway на `http://localhost:8080` (`docker compose up` или локально).
4. Запустить frontend:
   ```
   npm run dev
   ```
   Приложение: http://localhost:5173

## E2E
1. Поднять backend через gateway в тестовом compose-окружении:
   ```
   docker compose -f ../docker-compose.yml -f ../docker-compose.e2e.yml up -d --build
   ```
2. Выполнить seed-команды из корневого `README.md`.
3. Установить браузер:
   ```
   npx playwright install chromium
   ```
4. Запустить E2E:
   ```
   npm run test:e2e
   ```

Playwright поднимает отдельный Vite frontend на `http://127.0.0.1:4173` с `VITE_ECP_ALLOW_DEV=true`, но все API-запросы идут только через `http://127.0.0.1:18080/api`.

## Страницы
- `/` — главная (баннер, статистика, активные сборы, как это работает)
- `/catalog` — каталог с фильтрами
- `/cards/:id` — подробная страница сбора, эскроу-блок и форма пожертвования
