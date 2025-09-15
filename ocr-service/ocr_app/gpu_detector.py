"""GPU detection and model selection for OCR service"""
import torch
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class GPUDetector:
    """Handles GPU detection and model selection"""
    
    @staticmethod
    def detect_gpu():
        """
        Detect if GPU is available and has sufficient memory
        Returns: (has_gpu, gpu_name, memory_gb)
        """
        try:
            if not torch.cuda.is_available():
                logger.info("No CUDA-capable GPU detected")
                return False, None, 0
            
            # Get GPU information
            gpu_count = torch.cuda.device_count()
            if gpu_count == 0:
                logger.info("CUDA available but no GPU devices found")
                return False, None, 0
            
            # Use first GPU
            device = torch.cuda.get_device_properties(0)
            gpu_name = device.name
            total_memory_gb = device.total_memory / (1024**3)
            
            # Check if GPU has enough memory
            if total_memory_gb < settings.OCR_GPU_THRESHOLD:
                logger.info(f"GPU detected ({gpu_name}) but insufficient memory: {total_memory_gb:.2f}GB < {settings.OCR_GPU_THRESHOLD}GB")
                return False, gpu_name, total_memory_gb
            
            # Check available memory
            torch.cuda.empty_cache()
            free_memory = torch.cuda.mem_get_info(0)[0] / (1024**3)
            
            if free_memory < settings.OCR_GPU_THRESHOLD:
                logger.info(f"GPU detected ({gpu_name}) but insufficient free memory: {free_memory:.2f}GB < {settings.OCR_GPU_THRESHOLD}GB")
                return False, gpu_name, total_memory_gb
            
            logger.info(f"GPU detected and available: {gpu_name} with {total_memory_gb:.2f}GB total memory, {free_memory:.2f}GB free")
            return True, gpu_name, total_memory_gb
            
        except Exception as e:
            logger.error(f"Error detecting GPU: {str(e)}")
            return False, None, 0
    
    @staticmethod
    def get_optimal_model():
        """
        Select the optimal model based on GPU availability
        Returns: (model_name, use_gpu, device)
        """
        has_gpu, gpu_name, memory_gb = GPUDetector.detect_gpu()
        
        if has_gpu:
            model_name = settings.OCR_MODEL_GPU
            device = "cuda"
            logger.info(f"Using GPU model: {model_name} on {gpu_name}")
        else:
            model_name = settings.OCR_MODEL_CPU
            device = "cpu"
            logger.info(f"Using CPU model: {model_name}")
        
        return model_name, has_gpu, device
    
    @staticmethod
    def get_system_info():
        """Get detailed system information for diagnostics"""
        info = {
            'cuda_available': torch.cuda.is_available(),
            'cuda_version': None,
            'gpu_count': 0,
            'gpus': [],
            'cpu_count': torch.get_num_threads(),
            'torch_version': torch.__version__
        }
        
        if torch.cuda.is_available():
            info['cuda_version'] = torch.version.cuda
            info['gpu_count'] = torch.cuda.device_count()
            
            for i in range(info['gpu_count']):
                device = torch.cuda.get_device_properties(i)
                gpu_info = {
                    'index': i,
                    'name': device.name,
                    'total_memory_gb': device.total_memory / (1024**3),
                    'major': device.major,
                    'minor': device.minor,
                    'multi_processor_count': device.multi_processor_count
                }
                
                # Get current memory usage
                if torch.cuda.is_available():
                    torch.cuda.set_device(i)
                    free_memory, total_memory = torch.cuda.mem_get_info(i)
                    gpu_info['free_memory_gb'] = free_memory / (1024**3)
                    gpu_info['used_memory_gb'] = (total_memory - free_memory) / (1024**3)
                
                info['gpus'].append(gpu_info)
        
        return info