import os
from pypdf import PdfReader
from docx import Document
import openpyxl

class DocumentParser:
    @staticmethod
    def parse_file(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return DocumentParser._parse_pdf(file_path)
        elif ext == ".docx":
            return DocumentParser._parse_docx(file_path)
        elif ext == ".xlsx":
            return DocumentParser._parse_xlsx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _parse_pdf(path: str) -> str:
        reader = PdfReader(path)
        text = ""
        for i, page in enumerate(reader.pages):
            extracted = page.extract_text()
            if extracted:
                text += f"\n\n--- [Source: {os.path.basename(path)}, Page {i+1}] ---\n" + extracted
        return text

    @staticmethod
    def _parse_docx(path: str) -> str:
        doc = Document(path)
        text = f"\n\n--- ---\n"
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
        return text

    @staticmethod
    def _parse_xlsx(path: str) -> str:
        wb = openpyxl.load_workbook(path, data_only=True)
        text = f"\n\n--- [Source: {os.path.basename(path)}] ---\n"
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            text += f"\n[Sheet: {sheet}]\n"
            for row in ws.iter_rows(values_only=True):
                if any(row):
                    text += " | ".join([str(cell) if cell is not None else "" for cell in row]) + "\n"
        return text