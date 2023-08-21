# Key Flow backend REST API

This project is the REST Framework for the KeyFlow Property Management Saas Application

## How to Run
In order to get started you will need a few dependancies to run the application

1. First install PostgreSQL. It can be downloaded [here](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. If not installed already be sure to install [PgAdmin](https://www.pgadmin.org/download/) to view database information
3. Navigate to project directory in your terminal/comand prompt and run `python manage.py runserver` to start up the REST API

## Additional setup
- If you are geettign a CORS error on the front end make sure to add the `ALLOWED_HOSTS` array to settings.py and add `http://localhost:3000` or whatever port the react application is running on.
