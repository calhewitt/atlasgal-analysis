# ATLASGAL Analysis

A web application for making plots from ATLASGAL data

## Installation

### 1. Install Dependencies

The system runs on Django, so an installation of Python 2.7 with the following dependencies is required:

- django
- matplotlib
- scipys
- numpy
- mpld3

With pip, these can be easily installed with the command

```bash
$ pip install django matplotlib scipy numpy mpld3
```

### 2. Get the Code

Simply clone this repository:

```bash
$ git clone https://github.com/calhewitt/atlasgal-analysis
```

### 3: Run it!

To test the system, or whilst still in development, you can run a test server with the utility built into Django:

```bash
$ cd atlasgal-analysis
$ python manage.py runserver
```

This will start a server on port 8000 that can be accessed by localhost - to view the system, navigate to http://localhost:8000 in your browser.

To start the server so that the system can be accessed by other computers on the network, use the command:

```bash
$ python manage.py runserver 0.0.0.0:8000
```

### 4: Installing on a server

Like any Django application, the system can be configured to work with Apache using mod_wsgi - follow the instructions [here](https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/modwsgi/).

## Database Configuration

From this repository, the system is configured to use a test SQLite database, db.sqlite3.

This can be changed to use a live MySQL server or similar by changing the configuration in settings.py to use a different database engine, and supplying the relevant server, username, and password using the instrucions [here](http://stackoverflow.com/questions/19189813/setting-django-up-to-use-mysql).

The configuration block currently reads:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
```
