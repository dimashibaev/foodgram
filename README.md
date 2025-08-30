# Foodgram

**Foodgram** — веб-приложение для публикации и обмена кулинарными рецептами.  
Пользователи могут добавлять рецепты, подписываться на авторов, формировать список покупок и сохранять избранное.

## Технологии
- Python 3.9
- Django + Django REST Framework
- PostgreSQL
- Docker, Docker Compose
- Nginx
- Gunicorn

## Локальный запуск проекта
1. Клонируйте репозиторий:
   ```bash
   git clone <ссылка на репозиторий>
   cd foodgram/infra
2. Создайте файл .env в корне проекта и укажите переменные окружения.

3. Перейдите в папку infra/ соберите и запустите контейнеры:

docker compose up --build

Доступы:

Приложение: http://localhost

API-документация: http://localhost/api/docs/

Автор

Dima Shibaev