# 🌙 Luna Server

Luna Server is the backend service for the **[Luna Client](https://github.com/abrahamjonathanh/luna-client)** monitoring application. It is built using Django Rest Framework and designed specifically to support **multi-schema PostgreSQL** projects.

> **Note**: Luna Server is intended for use with **PostgreSQL only** projects.

---

## ⚙️ Tech Stack

- **Django Rest Framework** – RESTful API backend
- **PostgreSQL** – Relational database with multi-schema support
- **Redis** – Caching and message broker
- **Celery** – Background task queue
- **Gmail SMTP** – Email service (up to 200 emails/day)
- **Docker (optional)** – Containerized deployment

---

## ✅ Prerequisites

Make sure the following dependencies are installed before continuing:

- **Python**: 3.9+
- **PostgreSQL**: 14+
- **Redis**: 7.0+
- **Gmail SMTP**: [Gmail SMTP Support Guide](https://support.google.com/mail/answer/185833)

🔐 Generate a Gmail app password at:  
[https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

---

## 📦 Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/abrahamjonathanh/luna-server.git
   ```

2. Change directory:

   ```bash
   cd luna-server
   ```

3. Create the Database Schema
   Make sure your PostgreSQL database is set up and accessible. Then create a schema named **`luna`**:
   ```sql
   CREATE SCHEMA luna;
   ```

## 🚀 Getting Started

### 🔹 Using Docker (Recommended)

1. Start Docker Desktop.

2. Set up environment variables:
   Copy the `.env.example` file and customize it.

   ```bash
   cp .env.example .env
   ```

3. Generate a `FERNET_KEY` here: https://fernetkeygen.com

4. Build and start the containers:
   ```ps
   docker-compose up -d --build
   ```

### 🔸 Local Development (Without Docker)

1. Set up virtual environment (if not using Docker):
   ```ps
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```ps
   pip install -r requirements.txt
   ```
3. Set up environment variables:

   ```ps
   cp .env.example .env
   ```

   Adjust values as needed

4. Generate `FERNET_KEY` from: https://fernetkeygen.com

5. Run migrations and seed data:
   ```ps
   python manage.py migrate
   python manage.py seed_configuration
   python manage.py seed_role
   python manage.py setup_celery_beat
   ```
6. Start Celery Worker and Beat (follow the order):
   ```ps
   celery -A luna worker --pool=solo --loglevel=info
   ```
   ```ps
   celery -A luna beat --loglevel=info
   ```
7. Start the development server:
   ```ps
   python manage.py runserver
   ```
   It will run in http://localhost:8000.

---

## 👤 Creating an Admin User

To create an admin user:

1. Register a new user via the registration endpoint/page.

2. Manually update the user record in the **PostgreSQL** database:

   - Set `is_active` to `True`
   - Set `role` to `ADMIN`

   Tip: You can use `pgAdmin` or any SQL client to modify the user data directly.

---

## 🧾 Storing API Request Logs (For App You Want to Monitored)

Luna Server includes a request logging module to help you track and audit all incoming API calls.

### 🔧 Setup Instructions

1. **Copy the Logging Modules**

   Copy the following folders from this repository into the **root of your project**:

- /request_log/
- /geoip/

### 📁 Example Project Structure

```bash
your_project/
├── geoip/ # Copied
│ └── ...
├── request_log/ # Copied
│ └── ...
├── your_project/
│ └── settings.py
├── manage.py
└── ...
```

2. **Register the App in `settings.py`**

   Add `request_log` to your `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
      ...
      'request_log',  # Request Logging App
   ]
   ```

3. **Set the Custom Exception Handler**

   Add the following to your `settings.py` under `REST_FRAMEWORK`:

   ```python
   REST_FRAMEWORK = {
      'EXCEPTION_HANDLER': 'request_log.exceptions.custom_exception.custom_exception_handler',
      ...
   }
   ```

4. Add the Middleware

   Also in `settings.py`, add the logging middleware:

   ```python
   MIDDLEWARE = [
      ...
      'request_log.middlewares.request_log_middleware.RequestLogMiddleware',
   ]
   ```

5. Add GEO IP

   ```python
   import os

   GEOIP_PATH = os.path.join(BASE_DIR, 'geoip')
   ```

6. Run the Migration

   After copying and configuring everything, run the following command to apply the request log model migrations:

   ```ps
   python manage.py migrate request_log
   ```

### 📍 What It Does

- Logs IP address, HTTP method, status code, execution time, and more.

- Enriches log with geo-location info from IP (via geoip).

- Captures uncaught exceptions through DRF’s custom exception handler.

## 📫 Contact & Support

For issues or questions, feel free to open an issue or contribute via pull request.
