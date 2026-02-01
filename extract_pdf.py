
from pypdf import PdfReader
import sys

try:
    reader = PdfReader("Assignment_2_SciProg_2025.pdf")
    with open("assignment_text.txt", "w", encoding="utf-8") as f:
        for page in reader.pages:
            f.write(page.extract_text())
            f.write("\n")
    print("Successfully extracted text to assignment_text.txt")
except Exception as e:
    print(f"Error: {e}")
