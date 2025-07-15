# Key Flow Backend REST API

This project is the REST Framework for the KeyFlow Property Management Saas Application

## Installing PostgreSQL
This project is integrated with a PostgreSQL database and requires an installation of the latest verion of PostgreSQL (and optionally PgAdmin). The following steps will help install PostgreSQL on any operating system.
1. First install PostgreSQL. It can be downloaded [here](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)

2. If not installed already be sure to install [PgAdmin](https://www.pgadmin.org/download/) to view database tables

## How to Run (locally)
#### In order to get started you will need a few dependancies to run the application

1. When cloning the repository for the first time `keyflow_backend_app/migrations` directory should have several migration files. DO NOT DELETE them. They are needed in order to create all appropriate tables in the database.
 <!-- only have a `__init__.py` file in it. If not delete all other files and folders EXCEPT `__init__.py` -->

2. Navigate to the project directory

3. Install all dependancies for the project

```
pip install -r requirements.txt
```

5. Create a  virtual env (optional)

```
virtualenv venv
```

6. Start Virtual environment

```
source venv/bin/activate
```

7. Run the make migrations script 

```
python3 manage.py makemigrations
```

8. Migrate all changes

```
python3 manage.py migrate
```

9. Navigate to project directory in your terminal/comand prompt and run `python manage.py runserver` to start up the REST API

```
python manage.py runserver
```

<!-- ## How to Run (Docker)
In order to get started you will need to install docker

1. run `docker compose up --build` (docker build -t my-django-app .)
2. Migrate the database in docker using `docker compose run web python manage.py migrate`
3. Backend should now be running in a container. If you want to rerun the server after shutdown just run `docker compose up --build` -->

## Additional setup
- If you are geettign a CORS error on the front end make sure to add the `ALLOWED_HOSTS` array to settings.py and add `http://localhost:3000` or whatever port the react application is running on.
