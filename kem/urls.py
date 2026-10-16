from django.urls import path
from pdf_tools.views import home, process, inspect_pdf

urlpatterns = [path("", home, name="home"), path("procesar/", process, name="process"), path("inspeccionar/", inspect_pdf, name="inspect")]
