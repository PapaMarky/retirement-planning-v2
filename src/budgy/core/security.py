"""
Security module for retirement planning application.

Provides:
- Master password collection and validation
- Key derivation using Argon2id
- Secure password storage via system keyring
- Database and file encryption key management
"""

import os
import secrets
import getpass
import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logging.warning("keyring not available - passwords will not be stored")

try:
    from argon2 import PasswordHasher
    from argon2.low_level import hash_secret, Type
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    logging.error("argon2-cffi not available - key derivation disabled")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logging.error("cryptography not available - file encryption disabled")


class SecurityError(Exception):
    """Base exception for security-related errors"""
    pass


class KeyDerivationError(SecurityError):
    """Raised when key derivation fails"""
    pass


class SecurityManager:
    """
    Manages encryption keys and passwords for the retirement planning application.
    
    Uses a single master password to derive separate keys for:
    - Database encryption (SQLCipher)
    - OFX file encryption
    """
    
    SERVICE_NAME = "budgy-retirement-planning"
    USERNAME = "default"
    
    def __init__(self):
        self.master_password = None
        self.database_key = None
        self.file_key = None
        
    def check_dependencies(self) -> Tuple[bool, list]:
        """Check if all required security dependencies are available"""
        missing = []
        
        if not ARGON2_AVAILABLE:
            missing.append("argon2-cffi")
        if not CRYPTOGRAPHY_AVAILABLE:
            missing.append("cryptography")
            
        return len(missing) == 0, missing
    
    def generate_salt(self, length: int = 32) -> bytes:
        """Generate a cryptographically secure random salt"""
        return secrets.token_bytes(length)
    
    def derive_key(self, password: str, salt: bytes, purpose: str) -> bytes:
        """
        Derive a key from password using Argon2id.
        
        Args:
            password: Master password
            salt: Random salt (32 bytes recommended)
            purpose: Purpose string to create domain separation
            
        Returns:
            32-byte derived key
        """
        if not ARGON2_AVAILABLE:
            raise KeyDerivationError("argon2-cffi not available")
            
        # Add purpose to create domain separation between database and file keys
        purpose_salt = salt + purpose.encode('utf-8')
        
        try:
            # Use Argon2id with secure parameters
            derived_key = hash_secret(
                secret=password.encode('utf-8'),
                salt=purpose_salt[:32],  # Ensure salt is exactly 32 bytes
                time_cost=3,            # Number of iterations
                memory_cost=65536,      # Memory usage in KB (64MB)
                parallelism=1,          # Number of parallel threads
                hash_len=32,            # Output length in bytes
                type=Type.ID            # Use Argon2id variant
            )
            return derived_key
            
        except Exception as e:
            raise KeyDerivationError(f"Key derivation failed: {e}")
    
    def get_stored_password(self) -> Optional[str]:
        """Retrieve stored password from system keyring"""
        if not KEYRING_AVAILABLE:
            return None
            
        try:
            return keyring.get_password(self.SERVICE_NAME, self.USERNAME)
        except Exception as e:
            logging.warning(f"Failed to retrieve stored password: {e}")
            return None
    
    def store_password(self, password: str) -> bool:
        """Store password in system keyring"""
        if not KEYRING_AVAILABLE:
            logging.warning("Cannot store password - keyring not available")
            return False
            
        try:
            keyring.set_password(self.SERVICE_NAME, self.USERNAME, password)
            return True
        except Exception as e:
            logging.error(f"Failed to store password: {e}")
            return False
    
    def prompt_for_password(self, confirm: bool = False) -> str:
        """
        Securely prompt user for master password.
        
        Args:
            confirm: If True, prompt twice and ensure passwords match
            
        Returns:
            Master password
        """
        while True:
            password = getpass.getpass("Enter master password: ")
            
            if not password:
                print("Password cannot be empty. Please try again.")
                continue
                
            if len(password) < 8:
                print("Password must be at least 8 characters. Please try again.")
                continue
                
            if confirm:
                confirm_password = getpass.getpass("Confirm master password: ")
                if password != confirm_password:
                    print("Passwords do not match. Please try again.")
                    continue
                    
            return password
    
    def setup_encryption(self, db_path: Path, master_password: Optional[str] = None) -> Tuple[str, bytes]:
        """
        Set up encryption for a database.
        
        Args:
            db_path: Path to database file
            master_password: Master password (will prompt if None)
            
        Returns:
            Tuple of (database_key_hex, salt) for SQLCipher
        """
        available, missing = self.check_dependencies()
        if not available:
            raise SecurityError(f"Missing required dependencies: {', '.join(missing)}")
        
        # Get or prompt for master password
        if master_password is None:
            stored_password = self.get_stored_password()
            if stored_password:
                response = input("Use stored password? (y/n): ").lower()
                if response == 'y':
                    master_password = stored_password
                    
            if master_password is None:
                master_password = self.prompt_for_password(confirm=True)
                
                # Offer to store password
                if KEYRING_AVAILABLE:
                    response = input("Store password in system keyring? (y/n): ").lower()
                    if response == 'y':
                        self.store_password(master_password)
        
        # Generate or load salt for this database
        salt_file = db_path.with_suffix('.salt')
        if salt_file.exists():
            with open(salt_file, 'rb') as f:
                salt = f.read()
                if len(salt) != 32:
                    raise SecurityError(f"Invalid salt file: {salt_file}")
        else:
            salt = self.generate_salt()
            with open(salt_file, 'wb') as f:
                f.write(salt)
            # Set restrictive permissions on salt file
            os.chmod(salt_file, 0o600)
        
        # Derive database key
        database_key = self.derive_key(master_password, salt, "database")
        database_key_hex = database_key.hex()
        
        # Also derive file encryption key for later use
        self.file_key = self.derive_key(master_password, salt, "files")
        
        # Store for this session
        self.master_password = master_password
        self.database_key = database_key_hex
        
        logging.info(f"Encryption setup complete for {db_path}")
        return database_key_hex, salt
    
    def get_file_encryption_key(self) -> bytes:
        """Get the file encryption key for this session"""
        if self.file_key is None:
            raise SecurityError("File encryption not initialized - call setup_encryption first")
        return self.file_key
    
    def encrypt_file(self, file_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file using the derived file encryption key.
        
        Args:
            file_path: Path to file to encrypt
            output_path: Output path (defaults to file_path + '.enc')
            
        Returns:
            Path to encrypted file
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise SecurityError("cryptography not available")
            
        if self.file_key is None:
            raise SecurityError("File encryption not initialized")
            
        if output_path is None:
            output_path = file_path.with_suffix(file_path.suffix + '.enc')
            
        # Use Fernet for symmetric encryption
        key = base64.urlsafe_b64encode(self.file_key)
        cipher = Fernet(key)
        
        with open(file_path, 'rb') as infile:
            data = infile.read()
            
        encrypted_data = cipher.encrypt(data)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(encrypted_data)
            
        # Set restrictive permissions
        os.chmod(output_path, 0o600)
        
        logging.info(f"File encrypted: {file_path} -> {output_path}")
        return output_path
    
    def decrypt_file(self, encrypted_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file using the derived file encryption key.
        
        Args:
            encrypted_path: Path to encrypted file
            output_path: Output path (defaults to removing '.enc' suffix)
            
        Returns:
            Path to decrypted file
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise SecurityError("cryptography not available")
            
        if self.file_key is None:
            raise SecurityError("File encryption not initialized")
            
        if output_path is None:
            if encrypted_path.suffix == '.enc':
                output_path = encrypted_path.with_suffix('')
            else:
                output_path = encrypted_path.with_suffix('.dec')
                
        # Use Fernet for symmetric encryption
        key = base64.urlsafe_b64encode(self.file_key)
        cipher = Fernet(key)
        
        with open(encrypted_path, 'rb') as infile:
            encrypted_data = infile.read()
            
        try:
            decrypted_data = cipher.decrypt(encrypted_data)
        except Exception as e:
            raise SecurityError(f"Decryption failed - wrong password or corrupted file: {e}")
            
        with open(output_path, 'wb') as outfile:
            outfile.write(decrypted_data)
            
        logging.info(f"File decrypted: {encrypted_path} -> {output_path}")
        return output_path
    
    def secure_delete(self, file_path: Path) -> bool:
        """
        Securely delete a file by overwriting it before removal.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if successful
        """
        try:
            if file_path.exists():
                # Get file size
                file_size = file_path.stat().st_size
                
                # Overwrite with random data
                with open(file_path, 'wb') as f:
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
                
                # Remove the file
                file_path.unlink()
                
                logging.info(f"Securely deleted: {file_path}")
                return True
                
        except Exception as e:
            logging.error(f"Secure deletion failed for {file_path}: {e}")
            return False