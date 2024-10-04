# Antkeeping.info
The goal of Antkeeping.info is to provide ant keepers around the world with all the information they are intersted in. For example:
* Detailed information for specific species ( e.g. size, food, distribution, nuptial flight timesetc.)
* Species lists for specific countries/states
* Detailed information about spotted nuptial flights
* Statistical information/charts about nuptial flights
# Requirements
* python > 3.10
* PostgreSQL (Other databases are possible for testing, but .env file has to be changed)
* Redis
# Setup
1. Clone the repository
2. Create a new python virtual environment
3. Install packages with:
 ```
  pip install -r requirements/dev.txt
 ```
4. Create a database user, a database schema and set permissions correctly
5. Copy .env.example to .env
6. Edit .env
7. Switch to virtual environment
8. Run migrations:

 ```
  python manage.py migrate
 ```
9. Run dev server
```
 python manage.py runserver
```
