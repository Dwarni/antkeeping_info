# Antkeeping.info
The goal of Antkeeping.info is to provide ant keepers around the world with all the information they are intersted in. For example:
* Detailed information for specific species ( e.g. size, food, distribution, nuptial flight timesetc.)
* Species lists for specific countries/states
* Detailed information about spotted nuptial flights
* Statistical information/charts about nuptial flights
# Requirements
* python > 3.4
* MySQL (shema requires utf-8 binary collation)
# Setup
1. Clone the repository
2. Create a new python virtual environment using the requirements.txt file
3. Create a database user, a database schema and set permissions correctly
4. Edit settings.py and edit db-settings
5. Migrate database:

Windows:
 ```
  python manage.py migrate
 ```
Linux:  
 ```
  python3 manage.py migrate
 ```
6. Load data:

Windows:
  ```
  python .\manage.py loaddata .\antkeeping_info\fixtures\data.json
  ```
Linux:
   ```
  python3 ./manage.py loaddata ./antkeeping_info/fixtures/data.json
  ```
