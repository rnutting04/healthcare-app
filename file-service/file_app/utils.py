import hashlib
import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


def calculate_file_hash(file_data):
    """Calculate SHA-256 hash of file data"""
    sha256_hash = hashlib.sha256()
    
    if hasattr(file_data, 'chunks'):
        # Handle Django uploaded file
        for chunk in file_data.chunks():
            sha256_hash.update(chunk)
    else:
        # Handle bytes or string data
        if isinstance(file_data, str):
            file_data = file_data.encode()
        sha256_hash.update(file_data)
    
    return sha256_hash.hexdigest()


def encrypt_file(file_data, encryption_key):
    """Encrypt file data using Fernet encryption"""
    try:
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        
        if hasattr(file_data, 'read'):
            # Handle file-like objects
            file_data = file_data.read()
        elif hasattr(file_data, 'chunks'):
            # Handle Django uploaded file
            chunks = []
            for chunk in file_data.chunks():
                chunks.append(chunk)
            file_data = b''.join(chunks)
        
        encrypted_data = fernet.encrypt(file_data)
        return encrypted_data
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        raise


def decrypt_file(encrypted_data, encryption_key):
    """Decrypt file data using Fernet decryption"""
    try:
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        decrypted_data = fernet.decrypt(encrypted_data)
        return decrypted_data
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        raise


def save_encrypted_file(encrypted_data, storage_path):
    """Save encrypted data to file system"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        with open(storage_path, 'wb') as f:
            f.write(encrypted_data)
        
        return True
    except Exception as e:
        logger.error(f"File save error: {str(e)}")
        raise


def read_encrypted_file(storage_path):
    """Read encrypted file from file system"""
    try:
        with open(storage_path, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.error(f"File read error: {str(e)}")
        raise


def delete_file(storage_path):
    """Delete file from file system"""
    try:
        if os.path.exists(storage_path):
            os.remove(storage_path)
            return True
        return False
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        raise