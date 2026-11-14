import os

import openpyxl
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

try:  # optional: `pip install pypdfium2` (Chrome's PDF engine, usually better reading order)
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None


class DocumentParser:
    @staticmethod
    def parse_file(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            text = DocumentParser._parse_pdf(file_path)
        elif ext == ".docx":
            text = DocumentParser._parse_docx(file_path)
        elif ext == ".xlsx":
            text = DocumentParser._parse_xlsx(file_path)
        elif ext in (".txt", ".md"):
            text = DocumentParser._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        if not text.strip():
            raise ValueError(
                "No readable text found in this file. If it is a scanned PDF or an image-only "
                "document, it needs OCR, which LocalMind does not do."
            )
        return text

    # NOTE: the upload is stored under a random temp name, so page markers never
    # include the file name (main.py already labels every chunk with the real one).

    @staticmethod
    def _parse_pdf(path: str) -> str:
        pages = DocumentParser._pdf_pages_pdfium(path) if pdfium else DocumentParser._pdf_pages_pypdf(path)
        return "".join(
            f"\n\n--- [Page {i}] ---\n{t.strip()}" for i, t in enumerate(pages, start=1) if t and t.strip()
        )

    @staticmethod
    def _pdf_pages_pypdf(path: str) -> list[str]:
        return [page.extract_text() or "" for page in PdfReader(path).pages]

    @staticmethod
    def _pdf_pages_pdfium(path: str) -> list[str]:
        pdf = pdfium.PdfDocument(path)
        try:
            out = []
            for i in range(len(pdf)):
                page = pdf[i]
                textpage = page.get_textpage()
                out.append(textpage.get_text_range().replace("\r\n", "\n"))
                textpage.close()
                page.close()
            return out
        finally:
            pdf.close()

    @staticmethod
    def _parse_docx(path: str) -> str:
        doc = Document(path)
        lines = []
        # Walk the body in order so tables stay next to the paragraphs around them.
        for child in doc.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                text = Paragraph(child, doc).text.strip()
                if text:
                    lines.append(text)
            elif tag == "tbl":
                for row in Table(child, doc).rows:
                    cells = []
                    for cell in row.cells:
                        value = cell.text.strip().replace("\n", " ")
                        if value and (not cells or cells[-1] != value):  # merged cells repeat
                            cells.append(value)
                    if cells:
                        lines.append(" | ".join(cells))
        return "\n".join(lines)

    @staticmethod
    def _parse_xlsx(path: str) -> str:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        text = ""
        for sheet in wb.sheetnames:
            text += f"\n\n--- [Sheet: {sheet}] ---\n"
            for row in wb[sheet].iter_rows(values_only=True):
                # `any(row)` would drop rows whose values are all 0, so test for "empty" explicitly.
                if any(c is not None and str(c).strip() != "" for c in row):
                    text += " | ".join("" if c is None else str(c) for c in row) + "\n"
        wb.close()
        return text

    @staticmethod
    def _parse_text(path: str) -> str:
        with open(path, "rb") as f:
            raw = f.read()
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
                return raw.decode("utf-16", errors="replace")
            return raw.decode("latin-1")