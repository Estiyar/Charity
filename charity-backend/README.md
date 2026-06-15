# Charity Platform — Backend (Django + DRF)

Веб-платформа цифровизации пожертвований и благотворительности.

## Стек
- Django + Django REST Framework
- PostgreSQL
- JWT-авторизация (simplejwt)

## Структура
```
config/             — настройки проекта
apps/
  common/           — маскирование, статусная машина, валидаторы
  users/            — пользователи, роли, admin API
  cards/            — карточки сборов + справочники городов и диагнозов
  documents/        — документы и их проверка
  donations/        — пожертвования (демо-платёж)
  expenses/         — расходы и эскроу
  moderation/       — модерация, перераспределение средств
```

## 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

## 2. Настройка БД (PostgreSQL)
1. Создайте базу: `createdb charity`
2. Скопируйте `.env.example` в `.env` и укажите параметры подключения:
   ```
   DB_NAME=charity
   DB_USER=postgres
   DB_PASSWORD=ваш_пароль
   DB_HOST=localhost
   DB_PORT=5432
   ```

## 3. Запуск backend
```bash
python manage.py migrate
python manage.py seed_data          # тестовые данные (ТЗ раздел 29)
python manage.py runserver
```
- API: http://localhost:8000/api/
- Django admin: http://localhost:8000/admin/

## 4. Запуск frontend
Проект находится рядом: `../charity-frontend`
```bash
cd ../charity-frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

## 5. Логин и пароль тестового администратора

Пароль: `demo123456`

Email: `admin@charity.test`

## 6. Логин и пароль тестового модератора

Пароль: `demo123456`

Email: `moderator1@charity.test`, `moderator2@charity.test`

## 7. Логин и пароль тестового автора

Пароль: `demo123456`

Email: `author1@charity.test`, `author2@charity.test`, `author3@charity.test`

## 8. Логин и пароль тестового донора

Пароль: `demo123456`

Email: `donor1@charity.test` … `donor4@charity.test`

Повторная загрузка сидов: `python manage.py seed_data --clear`

## Заглушки (ТЗ раздел 33)
Интерфейс и логика заложены под будущее подключение:
- демо-платёж (без реального банка)
- эскроу-счёт (внутренний учёт)
- авто-проверка PDF
- SMS/email уведомления
- интеграция eGov

Настройки заглушек: панель администратора → Настройки (`/admin/settings`).

## Основные сценарии (ТЗ раздел 30)
1. **Создание сбора** — автор регистрируется → создаёт карточку → отправляет на модерацию
2. **Проверка модератором** — `/moderator` → одобрить / отклонить / на доработку
3. **Пожертвование** — каталог → карточка → демо-оплата
4. **Добавление расхода** — ЛК автора → форма расхода → модератор одобряет
5. **Перераспределение** — `/moderator/redistribution` → выбор решения → история на карточке

## Тесты
```bash
python manage.py test apps.users apps.cards apps.documents apps.donations apps.moderation apps.expenses
```

## Прогресс по ТЗ
См. `REQUIREMENTS_CHECKLIST.md`. Закрыты Фазы 0–6.
