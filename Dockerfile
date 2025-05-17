FROM python:3.13-alpine

# Install system dependencies
# Install necessary packages:
# - gcc: GNU Compiler Collection, required for compiling C/C++ extensions or dependencies.
# - musl-dev: Development files for musl, a lightweight standard C library.
# - postgresql-dev: Development files for PostgreSQL, needed for building PostgreSQL-related Python packages.
# - postgresql-client: PostgreSQL client tools, useful for interacting with PostgreSQL databases.
# - python3-dev: Python 3 development headers, required for building Python C extensions.
# - netcat-openbsd: Netcat utility, useful for debugging and testing network connections.
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    postgresql-client \
    python3-dev \
    netcat-openbsd

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Wait for the database to be ready before starting the server
# This script will check if the PostgreSQL database is ready before starting the Django server.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start the application
CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:8000"]