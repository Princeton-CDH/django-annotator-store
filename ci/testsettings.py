# minimal django settings required to run tests
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test.db",
    }
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'annotator_store',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',   # default
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

USE_TZ = True

SITE_ID = 1

ROOT_URLCONF = 'annotator_store.test_urls'

# default annotation model
# ANNOTATOR_ANNOTATION_MODEL = "annotator_store.Annotation"

# enable or disable permissions testing based on true/false environment variable
ANNOTATION_OBJECT_PERMISSIONS = (os.environ.get('PERMISSIONS', '') == 'true')

if ANNOTATION_OBJECT_PERMISSIONS:
    print('Enabling per-object permissions and django-guardian')
    INSTALLED_APPS.append('guardian')
    AUTHENTICATION_BACKENDS.append('guardian.backends.ObjectPermissionBackend')
else:
    print('Testing with normal django permissions (no django-guardian)')

# SECRET_KEY = ''
