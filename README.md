# KEM PDF

Aplicación local con Django + pypdf, HTML, CSS y TypeScript puro. Diseño basado en `ux-preview.svg` y `logo.png`.

## Ejecutar en PowerShell

Reutiliza el entorno `.venv` existente:

```powershell
# Setup de aplicación
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npm run build
# Correr Applicación
python manage.py runserver
```

Abre http://127.0.0.1:8000/. Si no puedes activar el entorno, usa `.\.venv\Scripts\python.exe` en lugar de `python`.

Las dependencias ya se han instalado y `static/js/app.js` contiene la compilación. Para arrancar ahora basta `.\.venv\Scripts\python.exe manage.py runserver`. Node/npm solo se necesitan para instalar o compilar TypeScript. No hay base de datos ni migraciones en esta versión.

## Uso

- **Unir:** añade dos o más PDF, ajusta su orden con las flechas y descarga el documento unido.
- **Extraer:** en Dividir PDF, indica páginas como `1,3,5-8`. Se conserva el orden indicado y se permiten repeticiones.
- **Separar:** elige «Un PDF por página» para obtener un ZIP con páginas numeradas.
- Los documentos cifrados deben desbloquearse antes de cargarlos.

## Desarrollo y pruebas

```powershell
npm run watch
```

En otra terminal:

```powershell
npm run check
python manage.py check
python manage.py test
```

Archivos principales: `frontend/app.ts`, `templates/home.html`, `static/css/app.css`, `pdf_tools/views.py` y `pdf_tools/services.py`.

## Límites y archivos temporales

Por defecto: 50 MB por archivo, 100 MB por operación, 30 archivos y 2.000 páginas. Configura `PDF_MAX_FILE_MB` y `PDF_MAX_TOTAL_MB` mediante variables de entorno; los otros límites están en `kem/settings.py`.

Django procesa los documentos en el servidor. Cuando lo ejecutas en tu equipo, el procesamiento es local. El navegador envía cada PDF para comprobar sus páginas y vuelve a enviarlo para generar el resultado. No hay historial ni almacenamiento permanente. Django limpia los temporales de entrada al cerrar la petición; el resultado se cierra al finalizar la respuesta. Los resultados mayores de 8 MB usan el directorio temporal del sistema. El navegador recibe el resultado completo antes de guardarlo.

La configuración es para uso local. Un despliegue público requiere servidor de producción, HTTPS, `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` privada, `DJANGO_ALLOWED_HOSTS` y límites de carga y recursos en el servidor. No expongas el servidor de desarrollo a internet.
