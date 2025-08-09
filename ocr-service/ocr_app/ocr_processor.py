"""OCR processing engine with GPU detection"""
import os
import time
import logging
import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
from django.conf import settings
from .gpu_detector import GPUDetector
from .exceptions import OCRProcessingError

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Handles OCR processing with automatic GPU detection"""
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self.model_name = None
        self.gpu_available = False
        
    def initialize_model(self):
        """Initialize OCR model based on GPU availability"""
        try:
            # Detect GPU and select model
            model_name, gpu_available, device = GPUDetector.get_optimal_model()
            
            logger.info(f"Initializing OCR model: {model_name} on {device}")
            
            # Load processor and model
            self.processor = TrOCRProcessor.from_pretrained(model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
            
            # Move model to appropriate device
            if gpu_available:
                self.model = self.model.cuda()
                self.model.eval()
            else:
                self.model = self.model.cpu()
                self.model.eval()
            
            self.device = device
            self.model_name = model_name
            self.gpu_available = gpu_available
            
            logger.info(f"Model initialized successfully: {model_name} on {device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OCR model: {str(e)}")
            # Fallback to Tesseract
            self.model = None
            self.processor = None
            logger.info("Falling back to Tesseract OCR")
    
    def process_file(self, file_path: str, file_type: str, job_id: str) -> Dict:
        """
        Process a file for OCR
        Returns: {
            'text': str,
            'pages': List[Dict],
            'confidence': float,
            'processing_time': float,
            'model_used': str
        }
        """
        start_time = time.time()
        
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise OCRProcessingError(f"File not found: {file_path}")
            
            # Process based on file type
            if file_type == 'text':
                result = self._process_text_file(file_path)
            elif file_type == 'pdf':
                result = self._process_pdf_file(file_path, job_id)
            elif file_type == 'image':
                result = self._process_image_file(file_path)
            else:
                raise OCRProcessingError(f"Unsupported file type: {file_type}")
            
            # Add processing metadata
            result['processing_time'] = time.time() - start_time
            result['model_used'] = self.model_name if self.model else 'tesseract'
            result['gpu_used'] = self.gpu_available
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise OCRProcessingError(f"OCR processing failed: {str(e)}")
    
    def _process_text_file(self, file_path: str) -> Dict:
        """Process text files (.txt, .rtf)"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            return {
                'text': text,
                'pages': [{'page': 1, 'text': text, 'confidence': 1.0}],
                'confidence': 1.0,
                'page_count': 1
            }
        except Exception as e:
            raise OCRProcessingError(f"Failed to read text file: {str(e)}")
    
    def _process_pdf_file(self, file_path: str, job_id: str) -> Dict:
        """Process PDF files"""
        try:
            # Get DPI and format settings from Django settings
            from django.conf import settings
            DPI = getattr(settings, 'OCR_PDF_DPI', 400)
            FORMAT = getattr(settings, 'OCR_PDF_FORMAT', 'PNG')
            
            logger.info(f"Converting PDF with DPI={DPI}, format={FORMAT}")
            
            # Convert PDF to images with configured settings
            images = pdf2image.convert_from_path(
                file_path,
                dpi=DPI,
                fmt=FORMAT,
                thread_count=4  # Use multiple threads for faster conversion
            )
            
            pages = []
            all_text = []
            total_confidence = 0
            
            for i, image in enumerate(images, 1):
                # Process each page
                page_result = self._ocr_image(image)
                
                pages.append({
                    'page': i,
                    'text': page_result['text'],
                    'confidence': page_result.get('confidence', 0)
                })
                
                all_text.append(page_result['text'])
                total_confidence += page_result.get('confidence', 0)
                
                # Send progress update
                progress = int((i / len(images)) * 100)
                self._send_progress_update(job_id, progress, f"Processing page {i}/{len(images)}")
            
            avg_confidence = total_confidence / len(images) if images else 0
            
            return {
                'text': '\n\n'.join(all_text),
                'pages': pages,
                'confidence': avg_confidence,
                'page_count': len(images)
            }
            
        except Exception as e:
            raise OCRProcessingError(f"Failed to process PDF: {str(e)}")
    
    def _process_image_file(self, file_path: str) -> Dict:
        """Process image files"""
        try:
            # Open image
            image = Image.open(file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Perform OCR
            result = self._ocr_image(image)
            
            return {
                'text': result['text'],
                'pages': [{'page': 1, 'text': result['text'], 'confidence': result.get('confidence', 0)}],
                'confidence': result.get('confidence', 0),
                'page_count': 1
            }
            
        except Exception as e:
            raise OCRProcessingError(f"Failed to process image: {str(e)}")
    
    def _ocr_image(self, image: Image.Image) -> Dict:
        """Perform OCR on a single image"""
        try:
            # Preprocess image
            image = self._preprocess_image(image)
            
            if self.model and self.processor:
                # Use TrOCR model
                return self._ocr_with_trocr(image)
            else:
                # Use Tesseract
                return self._ocr_with_tesseract(image)
                
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            # Fallback to Tesseract if TrOCR fails
            return self._ocr_with_tesseract(image)
    
    def _ocr_with_trocr(self, image: Image.Image) -> Dict:
        """Perform OCR using TrOCR model"""
        try:
            # Prepare image for model
            pixel_values = self.processor(image, return_tensors="pt").pixel_values
            
            # Move to appropriate device
            if self.gpu_available:
                pixel_values = pixel_values.cuda()
            
            # Generate text
            with torch.no_grad():
                generated_ids = self.model.generate(pixel_values)
            
            # Decode text
            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # TrOCR doesn't provide confidence scores directly
            # We'll use a heuristic based on text length and quality
            confidence = min(len(text) / 100, 1.0) * 0.95  # Assume high confidence for TrOCR
            
            return {
                'text': text,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"TrOCR processing failed: {str(e)}")
            raise
    
    def _ocr_with_tesseract(self, image: Image.Image) -> Dict:
        """Perform OCR using Tesseract"""
        try:
            # Convert PIL Image to numpy array
            img_array = np.array(image)
            
            # Get OCR data with confidence scores
            data = pytesseract.image_to_data(img_array, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate average confidence
            text_parts = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Filter out low confidence
                    text_parts.append(data['text'][i])
                    confidences.append(int(data['conf'][i]))
            
            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence / 100  # Convert to 0-1 scale
            }
            
        except Exception as e:
            logger.error(f"Tesseract processing failed: {str(e)}")
            # Last resort: basic text extraction
            text = pytesseract.image_to_string(image)
            return {
                'text': text.strip(),
                'confidence': 0.5  # Unknown confidence
            }
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Convert PIL Image to OpenCV format
            img_array = np.array(image)
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply thresholding to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.medianBlur(binary, 3)
            
            # Convert back to PIL Image
            return Image.fromarray(denoised)
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}")
            return image  # Return original if preprocessing fails
    
    def _send_progress_update(self, job_id: str, progress: int, message: str):
        """Send progress update via WebSocket"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ocr_job_{job_id}',
                {
                    'type': 'ocr_progress',
                    'job_id': job_id,
                    'progress': progress,
                    'message': message,
                    'timestamp': time.time()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send progress update: {str(e)}")
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.model:
                del self.model
            if self.processor:
                del self.processor
            
            if self.gpu_available:
                torch.cuda.empty_cache()
                
            logger.info("OCR processor cleaned up")
            
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}")