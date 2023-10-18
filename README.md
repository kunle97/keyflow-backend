# Key Flow Backend REST API

This project is the REST Framework for the KeyFlow Property Management Saas Application

## How to Run (locally)
In order to get started you will need a few dependancies to run the application

1. First install PostgreSQL. It can be downloaded [here](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. If not installed already be sure to install [PgAdmin](https://www.pgadmin.org/download/) to view database information
3. Navigate to project directory in your terminal/comand prompt and run `python manage.py runserver` to start up the REST API

## How to Run (Docker)
In order to get started you will need to install docker

1. run `docker compose up --build`
2. Migrate the database in docker using `docker compose run web python path/to/manage.py migrate`
3. Backend sohould now be running in a container. If you want to rerun the server after shutdown just run `docker compose up`

## Additional setup
- If you are geettign a CORS error on the front end make sure to add the `ALLOWED_HOSTS` array to settings.py and add `http://localhost:3000` or whatever port the react application is running on.
