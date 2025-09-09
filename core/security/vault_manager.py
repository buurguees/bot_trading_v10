# vault_manager.py - Gestor Vault para secrets enterprise
# Ubicación: C:\TradingBot_v10\security\vault_manager.py

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VaultManager:
    """Gestor Vault para secrets enterprise"""
    
    def __init__(self):
        """Inicializar el gestor Vault"""
        config_manager = EnterpriseConfigManager()
        self.config = config_manager.load_config()
        self.security_config = self.config.get_security_config()
        self.vault_config = self.security_config.get("vault", {})
        
        # Configuración de Vault
        self.enabled = self.vault_config.get("enabled", False)
        self.vault_url = self.vault_config.get("url", "http://localhost:8200")
        self.token_path = self.vault_config.get("token_path", "security/vault/token")
        self.secrets_config = self.vault_config.get("secrets", {})
        
        # Token de Vault
        self.vault_token: Optional[str] = None
        
        # Configurar sesión HTTP
        self.session = requests.Session()
        self._setup_http_session()
        
        # Métricas
        self.metrics = {
            "secrets_retrieved_total": 0,
            "secrets_stored_total": 0,
            "secrets_updated_total": 0,
            "secrets_deleted_total": 0,
            "vault_requests_total": 0,
            "vault_requests_failed": 0,
            "last_request_time": None,
            "errors_total": 0
        }
        
        logger.info("VaultManager inicializado")
    
    def _setup_http_session(self):
        """Configurar sesión HTTP con retry"""
        try:
            # Configurar retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # Configurar headers por defecto
            self.session.headers.update({
                'Content-Type': 'application/json',
                'User-Agent': 'TradingBot-Enterprise/1.0'
            })
            
        except Exception as e:
            logger.error(f"Error configurando sesión HTTP: {e}")
    
    async def start(self):
        """Iniciar el gestor Vault"""
        try:
            if not self.enabled:
                logger.info("VaultManager deshabilitado en configuración")
                return
            
            logger.info("Iniciando VaultManager...")
            
            # Cargar token de Vault
            await self._load_vault_token()
            
            # Verificar conexión con Vault
            if await self.health_check():
                logger.info("VaultManager iniciado exitosamente")
            else:
                logger.warning("VaultManager iniciado pero no se pudo conectar a Vault")
            
        except Exception as e:
            logger.error(f"Error iniciando VaultManager: {e}")
            raise
    
    async def stop(self):
        """Detener el gestor Vault"""
        try:
            logger.info("Deteniendo VaultManager...")
            
            # Limpiar token
            self.vault_token = None
            
            # Cerrar sesión HTTP
            self.session.close()
            
            logger.info("VaultManager detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo VaultManager: {e}")
    
    async def _load_vault_token(self):
        """Cargar token de Vault"""
        try:
            token_file = Path(self.token_path)
            
            if token_file.exists():
                with open(token_file, 'r') as f:
                    self.vault_token = f.read().strip()
                
                # Actualizar headers con token
                self.session.headers.update({
                    'X-Vault-Token': self.vault_token
                })
                
                logger.info("Token de Vault cargado")
            else:
                logger.warning(f"Archivo de token no encontrado: {self.token_path}")
                
        except Exception as e:
            logger.error(f"Error cargando token de Vault: {e}")
            raise
    
    async def _make_vault_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Realizar petición a Vault"""
        try:
            url = f"{self.vault_url}/v1/{path}"
            
            # Realizar petición
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                timeout=30
            )
            
            # Actualizar métricas
            self.metrics["vault_requests_total"] += 1
            self.metrics["last_request_time"] = datetime.now(timezone.utc)
            
            # Verificar respuesta
            response.raise_for_status()
            
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Vault: {e}")
            self.metrics["vault_requests_failed"] += 1
            self.metrics["errors_total"] += 1
            raise
        except Exception as e:
            logger.error(f"Error procesando respuesta de Vault: {e}")
            self.metrics["errors_total"] += 1
            raise
    
    async def get_secret(self, secret_path: str, secret_key: Optional[str] = None) -> Union[Dict[str, Any], str, None]:
        """Obtener secret de Vault"""
        try:
            if not self.enabled or not self.vault_token:
                logger.warning("Vault no está habilitado o no hay token")
                return None
            
            # Realizar petición
            response = await self._make_vault_request("GET", f"secret/data/{secret_path}")
            
            # Extraer datos
            if "data" in response and "data" in response["data"]:
                secret_data = response["data"]["data"]
                
                # Actualizar métricas
                self.metrics["secrets_retrieved_total"] += 1
                
                # Retornar clave específica o todos los datos
                if secret_key:
                    return secret_data.get(secret_key)
                else:
                    return secret_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo secret {secret_path}: {e}")
            return None
    
    async def store_secret(self, secret_path: str, secret_data: Dict[str, Any]) -> bool:
        """Almacenar secret en Vault"""
        try:
            if not self.enabled or not self.vault_token:
                logger.warning("Vault no está habilitado o no hay token")
                return False
            
            # Preparar datos
            data = {
                "data": secret_data
            }
            
            # Realizar petición
            await self._make_vault_request("POST", f"secret/data/{secret_path}", data)
            
            # Actualizar métricas
            self.metrics["secrets_stored_total"] += 1
            
            logger.info(f"Secret almacenado: {secret_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error almacenando secret {secret_path}: {e}")
            return False
    
    async def update_secret(self, secret_path: str, secret_data: Dict[str, Any]) -> bool:
        """Actualizar secret en Vault"""
        try:
            if not self.enabled or not self.vault_token:
                logger.warning("Vault no está habilitado o no hay token")
                return False
            
            # Obtener datos existentes
            existing_data = await self.get_secret(secret_path)
            if existing_data:
                # Fusionar datos
                updated_data = {**existing_data, **secret_data}
            else:
                updated_data = secret_data
            
            # Almacenar datos actualizados
            return await self.store_secret(secret_path, updated_data)
            
        except Exception as e:
            logger.error(f"Error actualizando secret {secret_path}: {e}")
            return False
    
    async def delete_secret(self, secret_path: str) -> bool:
        """Eliminar secret de Vault"""
        try:
            if not self.enabled or not self.vault_token:
                logger.warning("Vault no está habilitado o no hay token")
                return False
            
            # Realizar petición
            await self._make_vault_request("DELETE", f"secret/data/{secret_path}")
            
            # Actualizar métricas
            self.metrics["secrets_deleted_total"] += 1
            
            logger.info(f"Secret eliminado: {secret_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando secret {secret_path}: {e}")
            return False
    
    async def get_api_credentials(self) -> Optional[Dict[str, str]]:
        """Obtener credenciales de API"""
        try:
            api_creds_config = self.secrets_config.get("api_credentials", {})
            secret_path = api_creds_config.get("path", "secret/trading-bot/api")
            fields = api_creds_config.get("fields", ["api_key", "secret_key", "passphrase"])
            
            credentials = {}
            for field in fields:
                value = await self.get_secret(secret_path, field)
                if value:
                    credentials[field] = value
            
            return credentials if credentials else None
            
        except Exception as e:
            logger.error(f"Error obteniendo credenciales de API: {e}")
            return None
    
    async def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """Obtener credenciales de base de datos"""
        try:
            db_creds_config = self.secrets_config.get("database_credentials", {})
            secret_path = db_creds_config.get("path", "secret/trading-bot/database")
            fields = db_creds_config.get("fields", ["username", "password"])
            
            credentials = {}
            for field in fields:
                value = await self.get_secret(secret_path, field)
                if value:
                    credentials[field] = value
            
            return credentials if credentials else None
            
        except Exception as e:
            logger.error(f"Error obteniendo credenciales de base de datos: {e}")
            return None
    
    async def get_monitoring_credentials(self) -> Optional[Dict[str, str]]:
        """Obtener credenciales de monitoreo"""
        try:
            monitoring_creds_config = self.secrets_config.get("monitoring_credentials", {})
            secret_path = monitoring_creds_config.get("path", "secret/trading-bot/monitoring")
            fields = monitoring_creds_config.get("fields", ["grafana_password", "prometheus_password"])
            
            credentials = {}
            for field in fields:
                value = await self.get_secret(secret_path, field)
                if value:
                    credentials[field] = value
            
            return credentials if credentials else None
            
        except Exception as e:
            logger.error(f"Error obteniendo credenciales de monitoreo: {e}")
            return None
    
    async def store_api_credentials(self, credentials: Dict[str, str]) -> bool:
        """Almacenar credenciales de API"""
        try:
            api_creds_config = self.secrets_config.get("api_credentials", {})
            secret_path = api_creds_config.get("path", "secret/trading-bot/api")
            
            return await self.store_secret(secret_path, credentials)
            
        except Exception as e:
            logger.error(f"Error almacenando credenciales de API: {e}")
            return False
    
    async def store_database_credentials(self, credentials: Dict[str, str]) -> bool:
        """Almacenar credenciales de base de datos"""
        try:
            db_creds_config = self.secrets_config.get("database_credentials", {})
            secret_path = db_creds_config.get("path", "secret/trading-bot/database")
            
            return await self.store_secret(secret_path, credentials)
            
        except Exception as e:
            logger.error(f"Error almacenando credenciales de base de datos: {e}")
            return False
    
    async def store_monitoring_credentials(self, credentials: Dict[str, str]) -> bool:
        """Almacenar credenciales de monitoreo"""
        try:
            monitoring_creds_config = self.secrets_config.get("monitoring_credentials", {})
            secret_path = monitoring_creds_config.get("path", "secret/trading-bot/monitoring")
            
            return await self.store_secret(secret_path, credentials)
            
        except Exception as e:
            logger.error(f"Error almacenando credenciales de monitoreo: {e}")
            return False
    
    async def list_secrets(self, path: str = "secret/trading-bot") -> List[str]:
        """Listar secrets en un path"""
        try:
            if not self.enabled or not self.vault_token:
                return []
            
            # Realizar petición
            response = await self._make_vault_request("LIST", f"secret/metadata/{path}")
            
            # Extraer lista de secrets
            if "data" in response and "keys" in response["data"]:
                return response["data"]["keys"]
            
            return []
            
        except Exception as e:
            logger.error(f"Error listando secrets en {path}: {e}")
            return []
    
    async def rotate_secret(self, secret_path: str, new_data: Dict[str, Any]) -> bool:
        """Rotar secret en Vault"""
        try:
            if not self.enabled or not self.vault_token:
                logger.warning("Vault no está habilitado o no hay token")
                return False
            
            # Obtener datos existentes
            existing_data = await self.get_secret(secret_path)
            if not existing_data:
                logger.warning(f"Secret no encontrado para rotación: {secret_path}")
                return False
            
            # Crear backup de datos existentes
            backup_data = {
                **existing_data,
                "_backup_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Almacenar backup
            backup_path = f"{secret_path}_backup"
            await self.store_secret(backup_path, backup_data)
            
            # Actualizar con nuevos datos
            success = await self.update_secret(secret_path, new_data)
            
            if success:
                logger.info(f"Secret rotado exitosamente: {secret_path}")
            else:
                logger.error(f"Error rotando secret: {secret_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rotando secret {secret_path}: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del gestor Vault"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del gestor Vault"""
        return {
            "enabled": self.enabled,
            "vault_url": self.vault_url,
            "token_loaded": self.vault_token is not None,
            "secrets_config": self.secrets_config,
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del gestor Vault"""
        try:
            if not self.enabled:
                return True  # Vault deshabilitado es considerado saludable
            
            if not self.vault_token:
                return False
            
            # Verificar estado de Vault
            response = await self._make_vault_request("GET", "sys/health")
            
            # Verificar que Vault esté inicializado y no esté sellado
            if response.get("initialized") and not response.get("sealed"):
                return True
            else:
                logger.warning(f"Vault no está disponible: {response}")
                return False
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear gestor
def create_vault_manager() -> VaultManager:
    """Crear instancia del gestor Vault"""
    return VaultManager()

if __name__ == "__main__":
    # Test del gestor Vault
    async def test_vault_manager():
        manager = VaultManager()
        try:
            await manager.start()
            
            # Test de health check
            health = await manager.health_check()
            print(f"Health check: {health}")
            
            if health:
                # Test de almacenamiento de secret
                test_data = {
                    "api_key": "test_api_key_123",
                    "secret_key": "test_secret_key_456"
                }
                
                success = await manager.store_secret("secret/trading-bot/test", test_data)
                print(f"Secret almacenado: {success}")
                
                # Test de obtención de secret
                retrieved_data = await manager.get_secret("secret/trading-bot/test")
                print(f"Secret obtenido: {retrieved_data}")
                
                # Test de listado de secrets
                secrets = await manager.list_secrets("secret/trading-bot")
                print(f"Secrets listados: {secrets}")
            
            # Mostrar métricas
            print("\n=== MÉTRICAS DEL GESTOR VAULT ===")
            metrics = manager.get_metrics()
            for key, value in metrics.items():
                print(f"{key}: {value}")
            
        finally:
            await manager.stop()
    
    # Ejecutar test
    import asyncio
    asyncio.run(test_vault_manager())
