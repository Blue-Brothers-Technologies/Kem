from io import BytesIO
from zipfile import ZipFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, Client, override_settings
from pypdf import PdfReader, PdfWriter


def pdf(name="documento.pdf", widths=(100, 200, 300), encrypted=False):
    buffer = BytesIO()
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=400)
    if encrypted:
        writer.encrypt("secreto")
    writer.write(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="application/pdf")


class PDFToolsTests(SimpleTestCase):
    def download(self, data):
        response = self.client.post("/procesar/", data)
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content)
        response.close()
        return content

    def test_home(self):
        response = self.client.get("/")
        self.assertContains(response, "Tus PDF, en orden.")
        self.assertContains(response, "GESTIÓN DE DOCUMENTOS")
        self.assertContains(response, "selecciona archivos")

    def test_merge_order(self):
        content = self.download(
            {"action": "merge", "files": [pdf(widths=(200, 100)), pdf(widths=(300,))]})
        self.assertEqual([int(p.mediabox.width) for p in PdfReader(
            BytesIO(content)).pages], [200, 100, 300])

    def test_extract_ranges_order_and_repeats(self):
        content = self.download(
            {"action": "extract", "files": pdf(), "pages": "3,1-2,1"})
        self.assertEqual([int(p.mediabox.width) for p in PdfReader(
            BytesIO(content)).pages], [300, 100, 200, 100])

    def test_split_zip(self):
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
        for pages in ["", "0", "4", "3-1", "1,", "a", "1--2", "1-9999999"]:
            with self.subTest(pages=pages):
                self.assertEqual(self.client.post(
                    "/procesar/", {"action": "extract", "files": pdf(), "pages": pages}).status_code, 400)

    def test_invalid_files(self):
        for upload in [SimpleUploadedFile("fake.pdf", b"not pdf"), SimpleUploadedFile("empty.pdf", b""), pdf(name="wrong.txt"), pdf(encrypted=True), SimpleUploadedFile("broken.pdf", b"%PDF-1.7\nbroken")]:
            with self.subTest(name=upload.name):
                self.assertEqual(self.client.post(
                    "/procesar/", {"action": "split", "files": upload}).status_code, 400)

    def test_action_and_file_counts(self):
        for data in [{"action": "merge", "files": pdf()}, {"action": "split", "files": [pdf(), pdf()]}, {"action": "unknown", "files": pdf()}, {"action": "merge"}]:
            self.assertEqual(self.client.post(
                "/procesar/", data).status_code, 400)

    @override_settings(PDF_MAX_FILE_MB=0)
    def test_size_limit(self):
        self.assertEqual(self.client.post(
            "/procesar/", {"action": "split", "files": pdf()}).status_code, 400)

    @override_settings(PDF_MAX_TOTAL_MB=0)
    def test_total_limit(self):
        self.assertEqual(self.client.post(
            "/procesar/", {"action": "split", "files": pdf()}).status_code, 400)

    def test_inspect(self):
        self.assertEqual(self.client.post("/inspeccionar/",
                         {"files": pdf()}).json(), {"pages": 3})

    def test_csrf(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(
            "/procesar/", {"action": "split", "files": pdf()}).status_code, 403)
