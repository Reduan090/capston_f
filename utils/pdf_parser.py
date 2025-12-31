import fitz
from typing import List

def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = ""
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("blocks")  # blocks preserve reading order better
        
        for block in blocks:
            # block = (x0, y0, x1, y1, "text", block_no, block_type)
            if block[4].strip():  # only if text exists
                text += block[4] + "\n"
    
    doc.close()
    return text.strip()