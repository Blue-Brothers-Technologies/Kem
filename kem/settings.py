import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "kem-local-development-only")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
INSTALLED_APPS = ["django.contrib.staticfiles", "pdf_tools"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware",
              "django.middleware.csrf.CsrfViewMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "kem.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"],
              "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request"]}}]
WSGI_APPLICATION = "kem.wsgi.application"
LANGUAGE_CODE = "es"
TIME_ZONE = "Europe/Warsaw"
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
PDF_MAX_FILE_MB = int(os.environ.get("PDF_MAX_FILE_MB", "50"))
PDF_MAX_TOTAL_MB = int(os.environ.get("PDF_MAX_TOTAL_MB", "100"))
PDF_MAX_FILES = 30
PDF_MAX_PAGES = 2000
DATA_UPLOAD_MAX_NUMBER_FILES = PDF_MAX_FILES
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
SECURE_CONTENT_TYPE_NOSNIFF = True
