FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
<<<<<<< HEAD
    && apt-get install -y --no-install-recommends build-essential libpq-dev postgresql-client \
=======
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]
