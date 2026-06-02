FROM python:3.12-slim

WORKDIR /app

# Instalar node para tailwind build
RUN apt-get update && apt-get install -y nodejs npm

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node deps
COPY package*.json ./
RUN npm install

# Copiar proyecto
COPY . .

# Build Tailwind
RUN python manage.py tailwind build

# Collect static
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "crm.wsgi:application", "--bind", "0.0.0.0:3010"]