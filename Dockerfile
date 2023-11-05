# Use an official Python runtime as a parent image
FROM python:3.9

# Set environment variables
ENV PYTHONPATH "${PYTHONPATH}:/backend"
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=keyflow_backend.settings

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y libpq-dev

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy your Django project into the container
COPY . /app/

# Install 'wait-for-it'
RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh && \
    chmod +x wait-for-it.sh

# Apply migrations after waiting for the database to be ready
CMD ./wait-for-it.sh db:5432 -- python manage.py makemigrations && python manage.py migrate


# Expose the port the application runs onp
EXPOSE 8000

# Define the command to start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
