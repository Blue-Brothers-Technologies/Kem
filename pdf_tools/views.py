import logging
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED
from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pypdf import PdfWriter
from .services import PDFError, parse_pages, read_pdf

logger = logging.getLogger(__name__)


@require_GET
def home(request):
    return render(request, "home.html", {"max_file_mb": settings.PDF_MAX_FILE_MB, "max_total_mb": settings.PDF_MAX_TOTAL_MB})


@require_POST
def inspect_pdf(request):
    try:
        files = request.FILES.getlist("files")
        if len(files) != 1:
            raise PDFError("Selecciona un PDF para comprobarlo.")
        return JsonResponse({"pages": len(read_pdf(files[0]).pages)})
    except PDFError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_POST
def process(request):
    output = None
    try:
        action = request.POST.get("action")
        files = request.FILES.getlist("files")
        if action not in {"merge", "extract", "split"}:
            raise PDFError("Elige una herramienta válida.")
        if not files or len(files) > settings.PDF_MAX_FILES:
            raise PDFError(
                f"Selecciona entre 1 y {settings.PDF_MAX_FILES} archivos.")
        if action == "merge" and len(files) < 2:
            raise PDFError("Selecciona al menos dos PDF para unirlos.")
        if action != "merge" and len(files) != 1:
            raise PDFError("Selecciona un único PDF para dividirlo.")
        if sum(f.size for f in files) > settings.PDF_MAX_TOTAL_MB * 1024 * 1024:
            raise PDFError(
                f"La carga total no puede superar {settings.PDF_MAX_TOTAL_MB} MB.")
        readers = [read_pdf(f) for f in files]
        if sum(len(r.pages) for r in readers) > settings.PDF_MAX_PAGES:
            raise PDFError(
                f"Procesa como máximo {settings.PDF_MAX_PAGES} páginas por operación.")
        output = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        if action == "split":
            with ZipFile(output, "w", ZIP_DEFLATED) as archive:
                for index, page in enumerate(readers[0].pages, 1):
                    with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as page_buffer:
                        writer = PdfWriter()
                        writer.add_page(page)
                        writer.write(page_buffer)
                        writer.close()
                        page_buffer.seek(0)
                        with archive.open(f"pagina-{index:04d}.pdf", "w") as target:
                            copyfileobj(page_buffer, target)
            filename, content_type = "kem-paginas.zip", "application/zip"
        else:
            writer = PdfWriter()
            if action == "merge":
                for reader in readers:
                    for page in reader.pages:
                        writer.add_page(page)
            else:
                for index in parse_pages(request.POST.get("pages", ""), len(readers[0].pages)):
                    writer.add_page(readers[0].pages[index])
            writer.write(output)
            writer.close()
            filename = "kem-unido.pdf" if action == "merge" else "kem-extraido.pdf"
            content_type = "application/pdf"
        output.seek(0)
        response = FileResponse(
            output, as_attachment=True, filename=filename, content_type=content_type)
        response["Cache-Control"] = "no-store"
        return response
    except PDFError as exc:
        if output:
            output.close()
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception:
        if output:
            output.close()
        logger.exception("Error al procesar PDF")
        return JsonResponse({"error": "No se pudo procesar el documento. Comprueba que sea un PDF válido y vuelve a intentarlo."}, status=400)
