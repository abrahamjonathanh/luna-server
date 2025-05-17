# 🌙 Luna Server

**Luna Server** is a monitoring API tool built using **Django REST Framework**, designed for projects that use **PostgreSQL with multiple schemas**. It includes background task support via **Celery** and **Redis**, and can send notifications via **Gmail SMTP** (limited to 200 emails/day).

---

## 🔍 Description

Luna Server is ideal for backend systems that use a shared PostgreSQL database with different schemas. Each schema can be monitored independently, allowing flexible integration across multiple applications or tenants. Email notifications can be configured for alerts, system status, or any periodic update using Celery and Gmail SMTP.

---

## 🛠️ Technology Stack

- **Django REST Framework** – RESTful API backend
- **PostgreSQL** – with multi-schema support
- **Redis** – message broker for Celery
- **Celery** – background task processing
- **Gmail SMTP** – for sending up to 200 emails/day (free Gmail limit)

---

## 🚀 Getting Started

### 1. Create the Database Schema

Make sure your PostgreSQL database is set up and accessible. Then create a schema named `luna`:

```sql
CREATE SCHEMA luna;
```

### 2. Apply Migrations

Run Django migrations targeting the luna schema:

```cmd
python manage.py migrate
```

### 3. Register Applications

Manually add your application records to the `api_applications` table. These records should match the schema names you want to monitor.

## 🔁 Running Redis (Recommended with Docker)

To run Redis using Docker (default port 6379):

```docker
docker run -d --name redis -p 6379:6379 redis
```

## ⚙️ Running Celery

Make sure Redis is running before starting Celery.

### Start the Celery Worker:

```bash
celery -A luna worker --pool=solo --loglevel=info
```

### Start Celery Beat:

```bash
celery -A luna beat --loglevel=info
```

These will handle scheduled tasks such as sending email notifications.

## 🐳 Docker Installation

Luna Server includes a `docker-compose.yml` for easy deployment.

### To start the project:

```bash
docker-compose up --build
```

This command will run:

- PostgreSQL with persistent volume
- Redis server
- Django application server
- Celery worker
- Celery beat for periodic tasks

### Configuration

Before running, ensure your .env file is set up with the required environment variables following .env.example

## 📦 Requirements (If Running Locally Without Docker)

- Python 3.8+
- PostgreSQL 13+
- Redis
- Virtualenv or Poetry for Python dependency management

### 📬 Gmail SMTP Notes

- Gmail SMTP is used to send notification emails.
- A free Gmail account allows sending up to 200 emails/day.
- Use an App Password if you have 2FA enabled on your Google account.

## ✅ Project Status

Luna Server is production-ready and suitable for applications requiring multi-schema monitoring in a single PostgreSQL database.

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

Zhang Hua (2025)
