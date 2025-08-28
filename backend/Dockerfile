FROM python:3.9

WORKDIR /app
COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD ["sh", "-c", "python manage.py migrate --noinput && \
                  python manage.py loaddata data/tags.json && \
                  python manage.py load_list_ingredients data/ingredients.json && \
                  python manage.py collectstatic --noinput && \
                  gunicorn --bind 0.0.0.0:8000 backend.wsgi:application"]