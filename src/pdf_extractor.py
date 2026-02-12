"""
PDF Text Extraction Module
Extracts text from Supreme Court opinion PDFs.
"""

import logging
from pathlib import Path
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a single string
    """
    logger.info(f"Extracting text from: {pdf_path.name}")
    
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            else:
                logger.warning(f"Page {page_num + 1} in {pdf_path.name} yielded no text")
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages")
        return full_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        raise


def extract_all_pdfs(data_dir: Path, output_dir: Path) -> dict[str, Path]:
    """
    Extract text from all PDF files in the data directory.
    
    Args:
        data_dir: Directory containing the PDF files
        output_dir: Directory to save extracted text files
        
    Returns:
        Dictionary mapping case names to extracted text file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted_files = {}
    
    pdf_files = sorted(data_dir.glob("*full*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_path in pdf_files:
        # Extract case name from filename (e.g., "1 Ontario v. Quon")
        case_name = pdf_path.stem.replace(" full case", "").replace(" full text", "")
        
        # Extract text
        text = extract_text_from_pdf(pdf_path)
        
        # Save to output file
        output_path = output_dir / f"{case_name}.txt"
        output_path.write_text(text, encoding="utf-8")
        
        extracted_files[case_name] = output_path
        logger.info(f"Saved extracted text to: {output_path.name}")
    
    return extracted_files
