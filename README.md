# ATLASGAL Analysis

A simple web application to make plots from the [ATLASGAL Source Catalogues](http://atlasgal.mpifr-bonn.mpg.de/cgi-bin/ATLASGAL_DATABASE.cgi)

## Installation

### 1. Install Dependencies

The system runs on Django, so an installation of Python 2.7 with the following dependencies is required:

- django
- matplotlib
- scipys
- numpy
- mpld3

These can all be easily installed using the Python package manager [pip](https://pip.pypa.io/en/stable/installing/). Just run the following command (depending on your system you may need root permissions).

```bash
$ pip install django matplotlib scipy numpy mpld3
```

### 2. Get the Code

To download all of the code for the application, simply clone this repository into your working directory:

```bash
$ git clone https://github.com/calhewitt/atlasgal-analysis
```

### 3: Run it!

To easily run the application in order to test it, or whilst making changes in development, you can use the test server built into Django. Move into the repository...

```bash
$ cd atlasgal-analysis
```

... and start up the server...

```
$ python manage.py runserver
```

By default, the application will then be available on port 8000 of localhost - just navigate to [http://localhost:8000](http://localhost:8000).

Alternatively, the test server can be run so that the application is available to any other computer on the network, by running:

```bash
$ python manage.py runserver 0.0.0.0:8000
```

Then, just navigate to the same address, or from another machine, http://[your IP]:8000.

### 4: Installing on a server

Like any Django application, the application can be configured to work with an Apache server using mod_wsgi - follow the instructions [here](https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/modwsgi/).

## Database Configuration

From this repository, the system is configured to use a test SQLite database, db.sqlite3.

This can be changed to use any other database - either a different SQLite file or different kind of database such as MySQL - by altering the configuration in settings.py.

Change the configuration block which currently reads...

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
```

... to use the new database, following the instructions [here](http://stackoverflow.com/questions/19189813/setting-django-up-to-use-mysql).
