"""Comprobar las operaciones PDF, las validaciones y la protección CSRF."""

from io import BytesIO
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, Client, override_settings
from pypdf import PdfReader, PdfWriter


def pdf(name="documento.pdf", widths=(100, 200, 300), encrypted=False):
    """Crear una carga PDF de prueba con anchos de página identificables."""
    buffer = BytesIO()
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=400)
    if encrypted:
        writer.encrypt("secreto")
    writer.write(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="application/pdf")


class PDFToolsTests(SimpleTestCase):
    """Verificar las herramientas PDF sin utilizar una base de datos."""

    def download(self, data):
        """Enviar una operación y devolver el contenido de su descarga."""
        response = self.client.post("/procesar/", data)
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content)
        response.close()
        return content

    def test_home(self):
        """Comprobar que la página principal muestra los textos esperados."""
        response = self.client.get("/")
        self.assertContains(response, "Tus PDF, en orden.")
        self.assertContains(response, "GESTIÓN DE DOCUMENTOS")
        # El formato de la plantilla puede separar palabras con saltos de línea.
        content = " ".join(response.content.decode().split())
        self.assertIn("selecciona archivos", content)

    def test_merge_order(self):
        """Verificar que la unión conserva el orden de archivos y páginas."""
        content = self.download(
            {"action": "merge", "files": [pdf(widths=(200, 100)), pdf(widths=(300,))]})
        self.assertEqual([int(p.mediabox.width) for p in PdfReader(
            BytesIO(content)).pages], [200, 100, 300])

    def test_extract_ranges_order_and_repeats(self):
        """Verificar que la extracción conserva los rangos y repeticiones."""
        content = self.download(
            {"action": "extract", "files": pdf(), "pages": "3,1-2,1"})
        self.assertEqual([int(p.mediabox.width) for p in PdfReader(
            BytesIO(content)).pages], [300, 100, 200, 100])

    def test_split_zip(self):
        """Comprobar que el ZIP contiene un PDF válido por cada página."""
        content = self.download({"action": "split", "files": pdf()})
        with ZipFile(BytesIO(content)) as archive:
            self.assertEqual(archive.namelist(), [
                             "pagina-0001.pdf", "pagina-0002.pdf", "pagina-0003.pdf"])
            for index, name in enumerate(archive.namelist(), 1):
                reader = PdfReader(BytesIO(archive.read(name)))
                self.assertEqual(len(reader.pages), 1)
                self.assertEqual(
                    int(reader.pages[0].mediabox.width), index * 100)

    def test_invalid_ranges(self):
        """Rechazar rangos mal formados o fuera del documento."""
        for pages in ["", "0", "4", "3-1", "1,", "a", "1--2", "1-9999999"]:
            with self.subTest(pages=pages):
                self.assertEqual(self.client.post(
                    "/procesar/", {"action": "extract", "files": pdf(), "pages": pages}).status_code, 400)

    def test_invalid_files(self):
        """Rechazar archivos vacíos, falsos, dañados o cifrados."""
        for upload in [SimpleUploadedFile("fake.pdf", b"not pdf"), SimpleUploadedFile("empty.pdf", b""), pdf(name="wrong.txt"), pdf(encrypted=True), SimpleUploadedFile("broken.pdf", b"%PDF-1.7\nbroken")]:
            with self.subTest(name=upload.name):
                self.assertEqual(self.client.post(
                    "/procesar/", {"action": "split", "files": upload}).status_code, 400)

    def test_action_and_file_counts(self):
        """Rechazar acciones desconocidas y cantidades de archivos inválidas."""
        for data in [{"action": "merge", "files": pdf()}, {"action": "split", "files": [pdf(), pdf()]}, {"action": "unknown", "files": pdf()}, {"action": "merge"}]:
            self.assertEqual(self.client.post(
                "/procesar/", data).status_code, 400)

    @override_settings(PDF_MAX_FILE_MB=0)
    def test_size_limit(self):
        """Rechazar un archivo que supera el límite individual configurado."""
        self.assertEqual(self.client.post(
            "/procesar/", {"action": "split", "files": pdf()}).status_code, 400)

    @override_settings(PDF_MAX_TOTAL_MB=0)
    def test_total_limit(self):
        """Rechazar una carga que supera el límite total configurado."""
        self.assertEqual(self.client.post(
            "/procesar/", {"action": "split", "files": pdf()}).status_code, 400)

    def test_inspect(self):
        """Comprobar el número de páginas devuelto por la inspección."""
        self.assertEqual(self.client.post("/inspeccionar/",
                         {"files": pdf()}).json(), {"pages": 3})

    def test_csrf(self):
        """Rechazar una operación POST que carece del token CSRF."""
        self.assertEqual(Client(enforce_csrf_checks=True).post(
            "/procesar/", {"action": "split", "files": pdf()}).status_code, 403)
