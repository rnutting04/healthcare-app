import os
import hashlib
import logging
import tempfile
from typing import List, Dict, Tuple
import PyPDF2
import docx
from django.conf import settings

logger = logging.getLogger('embedding')


class DocumentProcessor:
    """Handles document processing and text extraction."""
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file."""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
        return text.strip()
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from a DOCX file."""
        text = ""
        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise
        return text.strip()
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from a TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            raise
    
    @classmethod
    def extract_text(cls, file_path: str, file_type: str) -> str:
        """Extract text from a file based on its type."""
        file_type = file_type.lower()
        
        if file_type == '.pdf':
            return cls.extract_text_from_pdf(file_path)
        elif file_type in ['.doc', '.docx']:
            return cls.extract_text_from_docx(file_path)
        elif file_type == '.txt':
            return cls.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    @staticmethod
    def chunk_text(text: str, max_tokens: int = None) -> List[str]:
        """
        Split text into chunks that don't exceed max_tokens.
        Uses a simple character-based approximation (1 token ≈ 4 characters).
        """
        if max_tokens is None:
            max_tokens = settings.OPENAI_MAX_TOKENS_PER_CHUNK
        
        # Approximate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the limit
            if len(current_chunk) + len(paragraph) + 2 > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # If the paragraph itself is too long, split it
                if len(paragraph) > max_chars:
                    words = paragraph.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > max_chars:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word
                        else:
                            temp_chunk += " " + word if temp_chunk else word
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    @classmethod
    def process_document(cls, file_path: str, file_type: str) -> Tuple[str, List[str], str]:
        """
        Process a document and return its hash, text chunks, and full text.
        
        Returns:
            Tuple of (file_hash, text_chunks, full_text)
        """
        # Calculate file hash
        file_hash = cls.calculate_file_hash(file_path)
        
        # Extract text
        full_text = cls.extract_text(file_path, file_type)
        
        # Chunk text
        text_chunks = cls.chunk_text(full_text)
        
        logger.info(f"Processed document: {os.path.basename(file_path)}, "
                   f"Hash: {file_hash}, Chunks: {len(text_chunks)}")
        
        return file_hash, text_chunks, full_text