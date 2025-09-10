# Ruta: core/security/encryption_manager.py
# encryption_manager.py - Gestor de encriptación enterprise
# Ubicación: C:\TradingBot_v10\security\encryption_manager.py

import os
import json
import logging
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncryptionManager:
    """Gestor de encriptación enterprise"""
    
    def __init__(self):
        """Inicializar el gestor de encriptación"""
        config_manager = EnterpriseConfigManager()
        self.config = config_manager.load_config()
        self.security_config = self.config.get_security_config()
        self.encryption_config = self.security_config.get("encryption", {})
        
        # Configuración de encriptación
        self.algorithm = self.encryption_config.get("algorithm", "AES-256-GCM")
        self.key_derivation = self.encryption_config.get("key_derivation", "PBKDF2")
        self.iterations = self.encryption_config.get("iterations", 100000)
        self.salt_length = self.encryption_config.get("salt_length", 16)
        
        # Campos sensibles a encriptar
        self.sensitive_fields = self.encryption_config.get("sensitive_fields", [])
        
        # Paths de almacenamiento de claves
        self.key_storage = self.encryption_config.get("key_storage", {})
        self.master_key_path = self.key_storage.get("master_key_path", "security/keys/master.key")
        self.encryption_keys_path = self.key_storage.get("encryption_keys_path", "security/keys/encryption/")
        self.backup_keys_path = self.key_storage.get("backup_keys_path", "backups/security/keys/")
        
        # Claves de encriptación
        self.master_key: Optional[bytes] = None
        self.encryption_keys: Dict[str, bytes] = {}
        
        # Métricas
        self.metrics = {
            "encryptions_total": 0,
            "decryptions_total": 0,
            "key_rotations_total": 0,
            "encryption_errors": 0,
            "decryption_errors": 0,
            "last_encryption_time": None,
            "last_decryption_time": None
        }
        
        logger.info("EncryptionManager inicializado")
    
    async def start(self):
        """Iniciar el gestor de encriptación"""
        try:
            logger.info("Iniciando EncryptionManager...")
            
            # Crear directorios de claves si no existen
            self._create_key_directories()
            
            # Cargar o generar clave maestra
            await self._load_or_generate_master_key()
            
            # Cargar claves de encriptación
            await self._load_encryption_keys()
            
            logger.info("EncryptionManager iniciado exitosamente")
            
        except Exception as e:
            logger.error(f"Error iniciando EncryptionManager: {e}")
            raise
    
    async def stop(self):
        """Detener el gestor de encriptación"""
        try:
            logger.info("Deteniendo EncryptionManager...")
            
            # Limpiar claves de memoria
            self.master_key = None
            self.encryption_keys.clear()
            
            logger.info("EncryptionManager detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo EncryptionManager: {e}")
    
    def _create_key_directories(self):
        """Crear directorios de claves"""
        try:
            # Crear directorio de claves maestras
            master_key_dir = Path(self.master_key_path).parent
            master_key_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear directorio de claves de encriptación
            encryption_keys_dir = Path(self.encryption_keys_path)
            encryption_keys_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear directorio de backup de claves
            backup_keys_dir = Path(self.backup_keys_path)
            backup_keys_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("Directorios de claves creados")
            
        except Exception as e:
            logger.error(f"Error creando directorios de claves: {e}")
            raise
    
    async def _load_or_generate_master_key(self):
        """Cargar o generar clave maestra"""
        try:
            master_key_file = Path(self.master_key_path)
            
            if master_key_file.exists():
                # Cargar clave existente
                with open(master_key_file, 'rb') as f:
                    self.master_key = f.read()
                logger.info("Clave maestra cargada desde archivo")
            else:
                # Generar nueva clave maestra
                self.master_key = Fernet.generate_key()
                
                # Guardar clave maestra
                with open(master_key_file, 'wb') as f:
                    f.write(self.master_key)
                
                # Establecer permisos restrictivos
                os.chmod(master_key_file, 0o600)
                
                logger.info("Nueva clave maestra generada y guardada")
            
        except Exception as e:
            logger.error(f"Error cargando/generando clave maestra: {e}")
            raise
    
    async def _load_encryption_keys(self):
        """Cargar claves de encriptación"""
        try:
            encryption_keys_dir = Path(self.encryption_keys_path)
            
            if not encryption_keys_dir.exists():
                return
            
            # Cargar todas las claves de encriptación
            for key_file in encryption_keys_dir.glob("*.key"):
                key_name = key_file.stem
                
                with open(key_file, 'rb') as f:
                    encrypted_key = f.read()
                
                # Desencriptar clave usando la clave maestra
                fernet = Fernet(self.master_key)
                decrypted_key = fernet.decrypt(encrypted_key)
                
                self.encryption_keys[key_name] = decrypted_key
                logger.debug(f"Clave de encriptación cargada: {key_name}")
            
            logger.info(f"{len(self.encryption_keys)} claves de encriptación cargadas")
            
        except Exception as e:
            logger.error(f"Error cargando claves de encriptación: {e}")
            raise
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derivar clave de encriptación"""
        try:
            if self.key_derivation == "PBKDF2":
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=self.iterations
                )
                return kdf.derive(password.encode())
            else:
                raise ValueError(f"Método de derivación de clave no soportado: {self.key_derivation}")
                
        except Exception as e:
            logger.error(f"Error derivando clave: {e}")
            raise
    
    def encrypt_data(self, data: str, key_name: str = "default") -> Dict[str, Any]:
        """Encriptar datos"""
        try:
            # Generar salt
            salt = secrets.token_bytes(self.salt_length)
            
            # Obtener o generar clave de encriptación
            if key_name not in self.encryption_keys:
                self._generate_encryption_key(key_name)
            
            encryption_key = self.encryption_keys[key_name]
            
            # Derivar clave de encriptación
            derived_key = self._derive_key(encryption_key.decode(), salt)
            
            # Encriptar datos
            if self.algorithm == "AES-256-GCM":
                aesgcm = AESGCM(derived_key)
                nonce = secrets.token_bytes(12)  # 96 bits para GCM
                encrypted_data = aesgcm.encrypt(nonce, data.encode(), None)
                
                result = {
                    "encrypted_data": encrypted_data.hex(),
                    "nonce": nonce.hex(),
                    "salt": salt.hex(),
                    "algorithm": self.algorithm,
                    "key_name": key_name,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                raise ValueError(f"Algoritmo de encriptación no soportado: {self.algorithm}")
            
            # Actualizar métricas
            self.metrics["encryptions_total"] += 1
            self.metrics["last_encryption_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Datos encriptados con clave: {key_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error encriptando datos: {e}")
            self.metrics["encryption_errors"] += 1
            raise
    
    def decrypt_data(self, encrypted_data: Dict[str, Any]) -> str:
        """Desencriptar datos"""
        try:
            # Extraer componentes
            encrypted_hex = encrypted_data["encrypted_data"]
            nonce_hex = encrypted_data["nonce"]
            salt_hex = encrypted_data["salt"]
            key_name = encrypted_data.get("key_name", "default")
            
            # Convertir de hex a bytes
            encrypted_bytes = bytes.fromhex(encrypted_hex)
            nonce = bytes.fromhex(nonce_hex)
            salt = bytes.fromhex(salt_hex)
            
            # Obtener clave de encriptación
            if key_name not in self.encryption_keys:
                raise ValueError(f"Clave de encriptación no encontrada: {key_name}")
            
            encryption_key = self.encryption_keys[key_name]
            
            # Derivar clave de encriptación
            derived_key = self._derive_key(encryption_key.decode(), salt)
            
            # Desencriptar datos
            if self.algorithm == "AES-256-GCM":
                aesgcm = AESGCM(derived_key)
                decrypted_data = aesgcm.decrypt(nonce, encrypted_bytes, None)
                
                # Actualizar métricas
                self.metrics["decryptions_total"] += 1
                self.metrics["last_decryption_time"] = datetime.now(timezone.utc)
                
                logger.debug(f"Datos desencriptados con clave: {key_name}")
                return decrypted_data.decode()
            else:
                raise ValueError(f"Algoritmo de encriptación no soportado: {self.algorithm}")
            
        except Exception as e:
            logger.error(f"Error desencriptando datos: {e}")
            self.metrics["decryption_errors"] += 1
            raise
    
    async def _generate_encryption_key(self, key_name: str):
        """Generar nueva clave de encriptación"""
        try:
            # Generar clave aleatoria
            key = Fernet.generate_key()
            
            # Encriptar clave con la clave maestra
            fernet = Fernet(self.master_key)
            encrypted_key = fernet.encrypt(key)
            
            # Guardar clave encriptada
            key_file = Path(self.encryption_keys_path) / f"{key_name}.key"
            with open(key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # Establecer permisos restrictivos
            os.chmod(key_file, 0o600)
            
            # Almacenar en memoria
            self.encryption_keys[key_name] = key
            
            logger.info(f"Nueva clave de encriptación generada: {key_name}")
            
        except Exception as e:
            logger.error(f"Error generando clave de encriptación {key_name}: {e}")
            raise
    
    def encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encriptar datos sensibles en un diccionario"""
        try:
            encrypted_data = data.copy()
            
            for field in self.sensitive_fields:
                if field in data and data[field] is not None:
                    # Encriptar campo sensible
                    encrypted_field = self.encrypt_data(str(data[field]))
                    encrypted_data[field] = encrypted_field
            
            logger.debug(f"Datos sensibles encriptados: {len(self.sensitive_fields)} campos")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Error encriptando datos sensibles: {e}")
            raise
    
    def decrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Desencriptar datos sensibles en un diccionario"""
        try:
            decrypted_data = data.copy()
            
            for field in self.sensitive_fields:
                if field in data and isinstance(data[field], dict) and "encrypted_data" in data[field]:
                    # Desencriptar campo sensible
                    decrypted_field = self.decrypt_data(data[field])
                    decrypted_data[field] = decrypted_field
            
            logger.debug(f"Datos sensibles desencriptados: {len(self.sensitive_fields)} campos")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Error desencriptando datos sensibles: {e}")
            raise
    
    async def rotate_encryption_key(self, key_name: str):
        """Rotar clave de encriptación"""
        try:
            # Generar nueva clave
            await self._generate_encryption_key(f"{key_name}_new")
            
            # Backup de la clave anterior
            await self._backup_encryption_key(key_name)
            
            # Reemplazar clave anterior
            old_key = self.encryption_keys.get(key_name)
            if old_key:
                del self.encryption_keys[key_name]
            
            # Renombrar nueva clave
            self.encryption_keys[key_name] = self.encryption_keys[f"{key_name}_new"]
            del self.encryption_keys[f"{key_name}_new"]
            
            # Actualizar métricas
            self.metrics["key_rotations_total"] += 1
            
            logger.info(f"Clave de encriptación rotada: {key_name}")
            
        except Exception as e:
            logger.error(f"Error rotando clave de encriptación {key_name}: {e}")
            raise
    
    async def _backup_encryption_key(self, key_name: str):
        """Hacer backup de clave de encriptación"""
        try:
            # Crear directorio de backup con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(self.backup_keys_path) / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copiar clave
            source_file = Path(self.encryption_keys_path) / f"{key_name}.key"
            if source_file.exists():
                backup_file = backup_dir / f"{key_name}.key"
                backup_file.write_bytes(source_file.read_bytes())
                
                logger.info(f"Backup de clave creado: {backup_file}")
            
        except Exception as e:
            logger.error(f"Error creando backup de clave {key_name}: {e}")
            raise
    
    def generate_password_hash(self, password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
        """Generar hash de contraseña"""
        try:
            if salt is None:
                salt = secrets.token_bytes(16)
            
            # Generar hash usando PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.iterations
            )
            
            password_hash = kdf.derive(password.encode())
            
            return {
                "hash": password_hash.hex(),
                "salt": salt.hex(),
                "iterations": str(self.iterations)
            }
            
        except Exception as e:
            logger.error(f"Error generando hash de contraseña: {e}")
            raise
    
    def verify_password(self, password: str, stored_hash: str, salt: str, iterations: int) -> bool:
        """Verificar contraseña"""
        try:
            # Convertir de hex a bytes
            stored_hash_bytes = bytes.fromhex(stored_hash)
            salt_bytes = bytes.fromhex(salt)
            
            # Generar hash de la contraseña proporcionada
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=iterations
            )
            
            password_hash = kdf.derive(password.encode())
            
            # Comparar hashes
            return secrets.compare_digest(password_hash, stored_hash_bytes)
            
        except Exception as e:
            logger.error(f"Error verificando contraseña: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del gestor de encriptación"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del gestor de encriptación"""
        return {
            "is_running": True,
            "algorithm": self.algorithm,
            "key_derivation": self.key_derivation,
            "iterations": self.iterations,
            "salt_length": self.salt_length,
            "sensitive_fields": self.sensitive_fields,
            "encryption_keys_loaded": len(self.encryption_keys),
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del gestor de encriptación"""
        try:
            # Verificar que la clave maestra esté cargada
            if not self.master_key:
                return False
            
            # Verificar que al menos una clave de encriptación esté cargada
            if not self.encryption_keys:
                return False
            
            # Test de encriptación/desencriptación
            test_data = "test_encryption_data"
            encrypted = self.encrypt_data(test_data)
            decrypted = self.decrypt_data(encrypted)
            
            return decrypted == test_data
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear gestor
def create_encryption_manager() -> EncryptionManager:
    """Crear instancia del gestor de encriptación"""
    return EncryptionManager()

if __name__ == "__main__":
    # Test del gestor de encriptación
    async def test_encryption_manager():
        manager = EncryptionManager()
        try:
            await manager.start()
            
            # Test de health check
            health = await manager.health_check()
            print(f"Health check: {health}")
            
            # Test de encriptación
            test_data = "Datos sensibles de prueba"
            encrypted = manager.encrypt_data(test_data)
            print(f"Datos encriptados: {encrypted}")
            
            # Test de desencriptación
            decrypted = manager.decrypt_data(encrypted)
            print(f"Datos desencriptados: {decrypted}")
            
            # Test de encriptación de datos sensibles
            sensitive_data = {
                "api_key": "test_api_key_123",
                "secret_key": "test_secret_key_456",
                "password": "test_password_789",
                "normal_field": "valor_normal"
            }
            
            encrypted_sensitive = manager.encrypt_sensitive_data(sensitive_data)
            print(f"Datos sensibles encriptados: {encrypted_sensitive}")
            
            # Mostrar métricas
            print("\n=== MÉTRICAS DEL GESTOR DE ENCRIPTACIÓN ===")
            metrics = manager.get_metrics()
            for key, value in metrics.items():
                print(f"{key}: {value}")
            
        finally:
            await manager.stop()
    
    # Ejecutar test
    asyncio.run(test_encryption_manager())
