import openai
import numpy as np
import logging
import time
from typing import List, Dict, Optional
from django.conf import settings
import json

logger = logging.getLogger('embedding')


class EmbeddingGenerator:
    """Handles OpenAI embedding generation with retry logic."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.max_retries = settings.EMBEDDING_RETRY_MAX_ATTEMPTS
        self.retry_delay = settings.EMBEDDING_RETRY_DELAY
    
    def generate_embedding(self, text: str, retry_count: int = 0) -> Optional[List[float]]:
        """
        Generate embedding for a single text using OpenAI API.
        
        Args:
            text: Text to generate embedding for
            retry_count: Current retry attempt number
            
        Returns:
            List of floats representing the embedding vector, or None if failed
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.info(f"Successfully generated embedding of dimension {len(embedding)}")
            return embedding
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit reached: {str(e)}")
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry {retry_count + 1}")
                time.sleep(wait_time)
                return self.generate_embedding(text, retry_count + 1)
            else:
                logger.error("Max retries reached for rate limit")
                raise
                
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.info(f"Waiting {wait_time} seconds before retry {retry_count + 1}")
                time.sleep(wait_time)
                return self.generate_embedding(text, retry_count + 1)
            else:
                logger.error("Max retries reached for API error")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {str(e)}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embeddings (or None for failed items)
        """
        embeddings = []
        
        for i, text in enumerate(texts):
            logger.info(f"Generating embedding for chunk {i + 1}/{len(texts)}")
            try:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i + 1}: {str(e)}")
                embeddings.append(None)
        
        return embeddings
    
    @staticmethod
    def serialize_embedding(embedding: List[float]) -> str:
        """Convert embedding vector to JSON string for storage."""
        return json.dumps(embedding)
    
    @staticmethod
    def deserialize_embedding(embedding_str: str) -> List[float]:
        """Convert JSON string back to embedding vector."""
        return json.loads(embedding_str)
    
    @staticmethod
    def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)