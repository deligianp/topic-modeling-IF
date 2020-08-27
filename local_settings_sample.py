# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

ALLOWED_HOSTS = [""]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'change-this-to-your-secret-key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': 5432,
    }
}

# File system path pointing to the directory where SFTP retrieved resources will be stored into
RESOURCES_DIRECTORY = "site-resources"
