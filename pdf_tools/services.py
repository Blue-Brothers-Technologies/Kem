"""Validar documentos PDF e interpretar selecciones de páginas."""

import re

from django.conf import settings
from pypdf import PdfReader


class PDFError(ValueError):
    """Indicar un error de validación que se puede mostrar al usuario."""

    pass


def read_pdf(upload):
    """Validar un archivo cargado y devolver su lector PDF.

    Comprobar extensión, tamaño, cabecera, cifrado y número de páginas.
    El archivo debe permanecer abierto mientras se utilice el lector.
    Lanzar PDFError si el documento no cumple las condiciones.
    """
    if not upload.name.lower().endswith(".pdf"):
        raise PDFError("Selecciona únicamente archivos con extensión .pdf.")
    if not upload.size or upload.size > settings.PDF_MAX_FILE_MB * 1024 * 1024:
        raise PDFError(
            f"Cada PDF debe contener datos y pesar como máximo {settings.PDF_MAX_FILE_MB} MB.")
    upload.seek(0)
    if not upload.read(1024).lstrip().startswith(b"%PDF-"):
        raise PDFError(
            "El contenido de uno de los archivos no es un PDF válido.")
    # Volver al inicio tras leer la cabecera para abrir el archivo completo.
    upload.seek(0)
    try:
        reader = PdfReader(upload)
        if reader.is_encrypted:
            raise PDFError(
                "Los PDF protegidos deben desbloquearse antes de procesarlos.")
        if not 1 <= len(reader.pages) <= settings.PDF_MAX_PAGES:
            raise PDFError(
                f"Cada PDF debe tener entre 1 y {settings.PDF_MAX_PAGES} páginas.")
        return reader
    except PDFError:
        raise
    except Exception as exc:
        raise PDFError(
            "No se pudo leer el PDF. Comprueba que no esté dañado.") from exc


def parse_pages(expression, total):
    """Convertir páginas y rangos en índices de base cero.

    Interpretar expression con páginas numeradas desde uno y total como
    número de páginas disponibles. Conservar el orden y las repeticiones.
    Lanzar PDFError si la sintaxis o los límites no son válidos.
    """
    if not expression.strip() or len(expression) > 10000:
        raise PDFError("Indica páginas o rangos, por ejemplo: 1,3,5-8.")
    pages = []
    for part in expression.split(","):
        match = re.fullmatch(
            r"\s*([0-9]{1,7})(?:\s*-\s*([0-9]{1,7}))?\s*", part)
        if not match:
            raise PDFError(
                "Formato incorrecto. Usa páginas o rangos como 1,3,5-8.")
        start = int(match[1])
        end = int(match[2] or start)
        if not 1 <= start <= end <= total:
            raise PDFError(
                f"Los rangos deben ser ascendentes y estar entre 1 y {total}.")
        if len(pages) + end - start + 1 > settings.PDF_MAX_PAGES:
            raise PDFError(
                f"El resultado no puede superar {settings.PDF_MAX_PAGES} páginas.")
        # El extremo final exclusivo incluye la última página indicada.
        pages.extend(range(start - 1, end))
    return pages
