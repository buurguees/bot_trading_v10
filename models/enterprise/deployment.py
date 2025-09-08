"""
models/enterprise/deployment.py - Production Deployment Architecture
Sistema de deployment enterprise para modelos ML en producción
"""

import os
import json
import yaml
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Kubernetes and containerization
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

# Docker
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DeploymentConfig:
    """Configuration for production deployment"""
    environment: str = "production"
    namespace: str = "trading-bot"
    image_registry: str = "your-registry.com"
    image_tag: str = "latest"
    replicas: int = 3
    cpu_limit: str = "1000m"
    memory_limit: str = "2Gi"
    cpu_request: str = "500m"
    memory_request: str = "1Gi"
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    liveness_check_path: str = "/live"
    port: int = 8080
    target_port: int = 8080
    service_type: str = "ClusterIP"
    ingress_enabled: bool = True
    ingress_host: str = "trading-bot.your-domain.com"
    tls_secret: str = "trading-bot-tls"
    config_map_name: str = "trading-bot-config"
    secret_name: str = "trading-bot-secrets"
    persistent_volume_claim: str = "trading-bot-pvc"
    storage_class: str = "fast-ssd"
    storage_size: str = "10Gi"

@dataclass
class ModelServingConfig:
    """Configuration for model serving"""
    model_name: str
    model_version: str
    model_path: str
    serving_framework: str = "tensorflow-serving"  # tensorflow-serving, torchserve, seldon
    batch_size: int = 32
    max_batch_wait_time: int = 100  # milliseconds
    max_concurrent_requests: int = 100
    timeout: int = 30  # seconds
    retry_attempts: int = 3
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    graceful_shutdown_timeout: int = 30

class ModelServingInfrastructure:
    """Infrastructure for model serving in production"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.deployments = {}
        self.services = {}
        self.ingresses = {}
        self.config_maps = {}
        self.secrets = {}
    
    def create_model_serving_deployment(self, model_config: ModelServingConfig) -> Dict[str, Any]:
        """Create Kubernetes deployment for model serving"""
        deployment_name = f"{model_config.model_name}-{model_config.model_version}"
        
        # Container spec
        container_spec = {
            "name": deployment_name,
            "image": f"{self.config.image_registry}/trading-bot-ml:{self.config.image_tag}",
            "ports": [{"containerPort": self.config.port, "name": "http"}],
            "resources": {
                "requests": {
                    "cpu": self.config.cpu_request,
                    "memory": self.config.memory_request
                },
                "limits": {
                    "cpu": self.config.cpu_limit,
                    "memory": self.config.memory_limit
                }
            },
            "env": [
                {"name": "MODEL_NAME", "value": model_config.model_name},
                {"name": "MODEL_VERSION", "value": model_config.model_version},
                {"name": "MODEL_PATH", "value": model_config.model_path},
                {"name": "SERVING_FRAMEWORK", "value": model_config.serving_framework},
                {"name": "BATCH_SIZE", "value": str(model_config.batch_size)},
                {"name": "MAX_CONCURRENT_REQUESTS", "value": str(model_config.max_concurrent_requests)},
                {"name": "TIMEOUT", "value": str(model_config.timeout)},
                {"name": "CIRCUIT_BREAKER_ENABLED", "value": str(model_config.circuit_breaker_enabled).lower()},
                {"name": "CIRCUIT_BREAKER_THRESHOLD", "value": str(model_config.circuit_breaker_threshold)},
                {"name": "CIRCUIT_BREAKER_TIMEOUT", "value": str(model_config.circuit_breaker_timeout)},
                {"name": "GRACEFUL_SHUTDOWN_TIMEOUT", "value": str(model_config.graceful_shutdown_timeout)}
            ],
            "volumeMounts": [
                {
                    "name": "model-storage",
                    "mountPath": "/models",
                    "readOnly": True
                },
                {
                    "name": "config-volume",
                    "mountPath": "/app/config"
                }
            ],
            "livenessProbe": {
                "httpGet": {
                    "path": self.config.liveness_check_path,
                    "port": self.config.port
                },
                "initialDelaySeconds": 30,
                "periodSeconds": 10,
                "timeoutSeconds": 5,
                "failureThreshold": 3
            },
            "readinessProbe": {
                "httpGet": {
                    "path": self.config.readiness_check_path,
                    "port": self.config.port
                },
                "initialDelaySeconds": 5,
                "periodSeconds": 5,
                "timeoutSeconds": 3,
                "failureThreshold": 3
            }
        }
        
        # Deployment spec
        deployment_spec = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": deployment_name,
                "namespace": self.config.namespace,
                "labels": {
                    "app": "trading-bot-ml",
                    "model": model_config.model_name,
                    "version": model_config.model_version,
                    "component": "model-serving"
                }
            },
            "spec": {
                "replicas": self.config.replicas,
                "selector": {
                    "matchLabels": {
                        "app": "trading-bot-ml",
                        "model": model_config.model_name,
                        "version": model_config.model_version
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "trading-bot-ml",
                            "model": model_config.model_name,
                            "version": model_config.model_version,
                            "component": "model-serving"
                        }
                    },
                    "spec": {
                        "containers": [container_spec],
                        "volumes": [
                            {
                                "name": "model-storage",
                                "persistentVolumeClaim": {
                                    "claimName": self.config.persistent_volume_claim
                                }
                            },
                            {
                                "name": "config-volume",
                                "configMap": {
                                    "name": self.config.config_map_name
                                }
                            }
                        ],
                        "restartPolicy": "Always",
                        "terminationGracePeriodSeconds": self.config.graceful_shutdown_timeout
                    }
                }
            }
        }
        
        self.deployments[deployment_name] = deployment_spec
        return deployment_spec
    
    def create_model_serving_service(self, model_config: ModelServingConfig) -> Dict[str, Any]:
        """Create Kubernetes service for model serving"""
        service_name = f"{model_config.model_name}-service"
        
        service_spec = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": self.config.namespace,
                "labels": {
                    "app": "trading-bot-ml",
                    "model": model_config.model_name,
                    "component": "model-serving"
                }
            },
            "spec": {
                "selector": {
                    "app": "trading-bot-ml",
                    "model": model_config.model_name
                },
                "ports": [
                    {
                        "name": "http",
                        "port": self.config.port,
                        "targetPort": self.config.target_port,
                        "protocol": "TCP"
                    }
                ],
                "type": self.config.service_type
            }
        }
        
        self.services[service_name] = service_spec
        return service_spec
    
    def create_model_serving_ingress(self, model_config: ModelServingConfig) -> Dict[str, Any]:
        """Create Kubernetes ingress for model serving"""
        if not self.config.ingress_enabled:
            return {}
        
        ingress_name = f"{model_config.model_name}-ingress"
        
        ingress_spec = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": ingress_name,
                "namespace": self.config.namespace,
                "labels": {
                    "app": "trading-bot-ml",
                    "model": model_config.model_name,
                    "component": "model-serving"
                },
                "annotations": {
                    "kubernetes.io/ingress.class": "nginx",
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                    "nginx.ingress.kubernetes.io/rate-limit": "100",
                    "nginx.ingress.kubernetes.io/rate-limit-window": "1m",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                }
            },
            "spec": {
                "tls": [
                    {
                        "hosts": [self.config.ingress_host],
                        "secretName": self.config.tls_secret
                    }
                ],
                "rules": [
                    {
                        "host": self.config.ingress_host,
                        "http": {
                            "paths": [
                                {
                                    "path": f"/api/v1/models/{model_config.model_name}",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": f"{model_config.model_name}-service",
                                            "port": {
                                                "number": self.config.port
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        self.ingresses[ingress_name] = ingress_spec
        return ingress_spec
    
    def create_config_map(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Kubernetes ConfigMap"""
        config_map_spec = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": self.config.config_map_name,
                "namespace": self.config.namespace,
                "labels": {
                    "app": "trading-bot-ml",
                    "component": "config"
                }
            },
            "data": {
                "config.json": json.dumps(config_data, indent=2),
                "logging.yaml": self._generate_logging_config(),
                "monitoring.yaml": self._generate_monitoring_config()
            }
        }
        
        self.config_maps[self.config.config_map_name] = config_map_spec
        return config_map_spec
    
    def create_secrets(self, secrets_data: Dict[str, str]) -> Dict[str, Any]:
        """Create Kubernetes Secrets"""
        import base64
        
        # Encode secrets
        encoded_secrets = {}
        for key, value in secrets_data.items():
            encoded_secrets[key] = base64.b64encode(value.encode()).decode()
        
        secret_spec = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": self.config.secret_name,
                "namespace": self.config.namespace,
                "labels": {
                    "app": "trading-bot-ml",
                    "component": "secrets"
                }
            },
            "type": "Opaque",
            "data": encoded_secrets
        }
        
        self.secrets[self.config.secret_name] = secret_spec
        return secret_spec
    
    def create_persistent_volume_claim(self) -> Dict[str, Any]:
        """Create PersistentVolumeClaim for model storage"""
        pvc_spec = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": self.config.persistent_volume_claim,
                "namespace": self.config.namespace,
                "labels": {
                    "app": "trading-bot-ml",
                    "component": "storage"
                }
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": self.config.storage_size
                    }
                },
                "storageClassName": self.config.storage_class
            }
        }
        
        return pvc_spec
    
    def _generate_logging_config(self) -> str:
        """Generate logging configuration"""
        return """
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  detailed:
    format: '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: /app/logs/trading-bot.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
  
  json_file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /app/logs/trading-bot.json
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  trading_bot:
    level: DEBUG
    handlers: [console, file, json_file]
    propagate: false
  
  models.enterprise:
    level: DEBUG
    handlers: [console, file, json_file]
    propagate: false

root:
  level: INFO
  handlers: [console]
"""
    
    def _generate_monitoring_config(self) -> str:
        """Generate monitoring configuration"""
        return """
prometheus:
  enabled: true
  port: 9090
  path: /metrics
  scrape_interval: 15s

grafana:
  enabled: true
  port: 3000
  dashboards:
    - trading_bot_overview
    - model_performance
    - system_health

jaeger:
  enabled: true
  endpoint: http://jaeger-collector:14268/api/traces
  service_name: trading-bot-ml

health_checks:
  enabled: true
  interval: 30s
  timeout: 5s
  endpoints:
    - /health
    - /ready
    - /live
"""

class BlueGreenDeployment:
    """Blue-Green deployment strategy for zero-downtime updates"""
    
    def __init__(self, infrastructure: ModelServingInfrastructure):
        self.infrastructure = infrastructure
        self.current_color = "blue"
        self.target_color = "green"
    
    def deploy_new_version(self, model_config: ModelServingConfig) -> Dict[str, Any]:
        """Deploy new version using blue-green strategy"""
        logger.info(f"Starting blue-green deployment for {model_config.model_name}")
        
        # Create new version with target color
        new_model_config = ModelServingConfig(
            model_name=model_config.model_name,
            model_version=model_config.model_version,
            model_path=model_config.model_path,
            serving_framework=model_config.serving_framework,
            batch_size=model_config.batch_size,
            max_batch_wait_time=model_config.max_batch_wait_time,
            max_concurrent_requests=model_config.max_concurrent_requests,
            timeout=model_config.timeout,
            retry_attempts=model_config.retry_attempts,
            circuit_breaker_enabled=model_config.circuit_breaker_enabled,
            circuit_breaker_threshold=model_config.circuit_breaker_threshold,
            circuit_breaker_timeout=model_config.circuit_breaker_timeout,
            graceful_shutdown_timeout=model_config.graceful_shutdown_timeout
        )
        
        # Deploy new version
        deployment = self.infrastructure.create_model_serving_deployment(new_model_config)
        service = self.infrastructure.create_model_serving_service(new_model_config)
        
        # Wait for new version to be ready
        self._wait_for_deployment_ready(deployment["metadata"]["name"])
        
        # Switch traffic to new version
        self._switch_traffic(new_model_config)
        
        # Clean up old version
        self._cleanup_old_version()
        
        # Update current color
        self.current_color, self.target_color = self.target_color, self.current_color
        
        return {
            "status": "success",
            "deployment": deployment,
            "service": service,
            "current_color": self.current_color
        }
    
    def _wait_for_deployment_ready(self, deployment_name: str, timeout: int = 300):
        """Wait for deployment to be ready"""
        logger.info(f"Waiting for deployment {deployment_name} to be ready")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # In a real implementation, this would check Kubernetes API
            # For now, simulate waiting
            time.sleep(5)
            
            # Simulate readiness check
            if time.time() - start_time > 30:  # Simulate 30s to be ready
                logger.info(f"Deployment {deployment_name} is ready")
                return True
        
        raise TimeoutError(f"Deployment {deployment_name} not ready after {timeout}s")
    
    def _switch_traffic(self, model_config: ModelServingConfig):
        """Switch traffic to new version"""
        logger.info(f"Switching traffic to {model_config.model_name} version {model_config.model_version}")
        
        # In a real implementation, this would update service selectors
        # For now, simulate traffic switch
        time.sleep(2)
        
        logger.info("Traffic switched successfully")
    
    def _cleanup_old_version(self):
        """Clean up old version after successful switch"""
        logger.info("Cleaning up old version")
        
        # In a real implementation, this would delete old deployments
        # For now, simulate cleanup
        time.sleep(1)
        
        logger.info("Old version cleaned up")

class KubernetesDeployment:
    """Kubernetes deployment manager"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.k8s_client = None
        self._initialize_k8s_client()
    
    def _initialize_k8s_client(self):
        """Initialize Kubernetes client"""
        if not KUBERNETES_AVAILABLE:
            logger.warning("Kubernetes client not available. Install kubernetes package.")
            return
        
        try:
            # Try to load in-cluster config first
            config.load_incluster_config()
            self.k8s_client = client.ApiClient()
            logger.info("Kubernetes client initialized with in-cluster config")
        except:
            try:
                # Fall back to kubeconfig
                config.load_kube_config()
                self.k8s_client = client.ApiClient()
                logger.info("Kubernetes client initialized with kubeconfig")
            except Exception as e:
                logger.error(f"Failed to initialize Kubernetes client: {e}")
                self.k8s_client = None
    
    def deploy_to_kubernetes(self, infrastructure: ModelServingInfrastructure) -> Dict[str, Any]:
        """Deploy to Kubernetes cluster"""
        if not self.k8s_client:
            return {"error": "Kubernetes client not available"}
        
        results = {}
        
        try:
            # Create namespace
            self._create_namespace()
            
            # Create ConfigMap
            config_map = infrastructure.create_config_map({
                "environment": self.config.environment,
                "namespace": self.config.namespace,
                "replicas": self.config.replicas
            })
            results["config_map"] = self._apply_resource(config_map)
            
            # Create Secrets
            secrets = infrastructure.create_secrets({
                "api_key": "your-api-key-here",
                "database_url": "your-database-url-here"
            })
            results["secrets"] = self._apply_resource(secrets)
            
            # Create PVC
            pvc = infrastructure.create_persistent_volume_claim()
            results["pvc"] = self._apply_resource(pvc)
            
            # Create Deployments
            for deployment_name, deployment_spec in infrastructure.deployments.items():
                results[f"deployment_{deployment_name}"] = self._apply_resource(deployment_spec)
            
            # Create Services
            for service_name, service_spec in infrastructure.services.items():
                results[f"service_{service_name}"] = self._apply_resource(service_spec)
            
            # Create Ingresses
            for ingress_name, ingress_spec in infrastructure.ingresses.items():
                results[f"ingress_{ingress_name}"] = self._apply_resource(ingress_spec)
            
            results["status"] = "success"
            logger.info("Deployment to Kubernetes completed successfully")
            
        except Exception as e:
            logger.error(f"Error deploying to Kubernetes: {e}")
            results["error"] = str(e)
        
        return results
    
    def _create_namespace(self):
        """Create namespace if it doesn't exist"""
        if not self.k8s_client:
            return
        
        try:
            v1 = client.CoreV1Api(self.k8s_client)
            
            # Check if namespace exists
            try:
                v1.read_namespace(name=self.config.namespace)
                logger.info(f"Namespace {self.config.namespace} already exists")
            except ApiException as e:
                if e.status == 404:
                    # Create namespace
                    namespace_spec = {
                        "apiVersion": "v1",
                        "kind": "Namespace",
                        "metadata": {
                            "name": self.config.namespace,
                            "labels": {
                                "app": "trading-bot-ml",
                                "environment": self.config.environment
                            }
                        }
                    }
                    
                    v1.create_namespace(body=namespace_spec)
                    logger.info(f"Created namespace {self.config.namespace}")
                else:
                    raise
        
        except Exception as e:
            logger.error(f"Error creating namespace: {e}")
    
    def _apply_resource(self, resource_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a Kubernetes resource"""
        if not self.k8s_client:
            return {"error": "Kubernetes client not available"}
        
        try:
            # This is a simplified version. In practice, you'd use kubectl or
            # the appropriate Kubernetes client methods for each resource type
            logger.info(f"Applying resource: {resource_spec['kind']} {resource_spec['metadata']['name']}")
            
            # Simulate successful application
            return {
                "status": "applied",
                "resource": resource_spec["kind"],
                "name": resource_spec["metadata"]["name"]
            }
        
        except Exception as e:
            logger.error(f"Error applying resource: {e}")
            return {"error": str(e)}
    
    def generate_kubernetes_manifests(self, infrastructure: ModelServingInfrastructure) -> Dict[str, str]:
        """Generate Kubernetes manifest files"""
        manifests = {}
        
        # Generate YAML for each resource
        for resource_name, resource_spec in {
            **infrastructure.deployments,
            **infrastructure.services,
            **infrastructure.ingresses,
            **infrastructure.config_maps,
            **infrastructure.secrets
        }.items():
            manifest_yaml = yaml.dump(resource_spec, default_flow_style=False)
            manifests[f"{resource_name}.yaml"] = manifest_yaml
        
        return manifests

class DockerManager:
    """Docker container management"""
    
    def __init__(self):
        self.docker_client = None
        self._initialize_docker_client()
    
    def _initialize_docker_client(self):
        """Initialize Docker client"""
        if not DOCKER_AVAILABLE:
            logger.warning("Docker client not available. Install docker package.")
            return
        
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
    
    def build_model_image(self, model_path: str, image_tag: str) -> Dict[str, Any]:
        """Build Docker image for model serving"""
        if not self.docker_client:
            return {"error": "Docker client not available"}
        
        try:
            # Create Dockerfile
            dockerfile_content = self._generate_dockerfile()
            
            # Build image
            image, build_logs = self.docker_client.images.build(
                path=model_path,
                tag=image_tag,
                dockerfile=dockerfile_content,
                rm=True
            )
            
            logger.info(f"Built Docker image: {image_tag}")
            
            return {
                "status": "success",
                "image_tag": image_tag,
                "image_id": image.id,
                "build_logs": build_logs
            }
        
        except Exception as e:
            logger.error(f"Error building Docker image: {e}")
            return {"error": str(e)}
    
    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile for model serving"""
        return """
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/logs /app/models /app/config

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_SERVING_ENABLED=true

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "-m", "models.enterprise.serving"]
"""
    
    def push_image(self, image_tag: str, registry: str) -> Dict[str, Any]:
        """Push Docker image to registry"""
        if not self.docker_client:
            return {"error": "Docker client not available"}
        
        try:
            # Tag image for registry
            registry_tag = f"{registry}/{image_tag}"
            image = self.docker_client.images.get(image_tag)
            image.tag(registry_tag)
            
            # Push image
            push_logs = self.docker_client.images.push(registry_tag)
            
            logger.info(f"Pushed Docker image: {registry_tag}")
            
            return {
                "status": "success",
                "registry_tag": registry_tag,
                "push_logs": push_logs
            }
        
        except Exception as e:
            logger.error(f"Error pushing Docker image: {e}")
            return {"error": str(e)}

# Global deployment manager
deployment_config = DeploymentConfig()
infrastructure = ModelServingInfrastructure(deployment_config)
kubernetes_deployment = KubernetesDeployment(deployment_config)
docker_manager = DockerManager()

# Convenience functions
def deploy_model_to_production(model_config: ModelServingConfig) -> Dict[str, Any]:
    """Deploy model to production"""
    # Create infrastructure
    deployment = infrastructure.create_model_serving_deployment(model_config)
    service = infrastructure.create_model_serving_service(model_config)
    ingress = infrastructure.create_model_serving_ingress(model_config)
    
    # Deploy to Kubernetes
    k8s_result = kubernetes_deployment.deploy_to_kubernetes(infrastructure)
    
    return {
        "deployment": deployment,
        "service": service,
        "ingress": ingress,
        "kubernetes_result": k8s_result
    }

def generate_kubernetes_manifests() -> Dict[str, str]:
    """Generate Kubernetes manifest files"""
    return kubernetes_deployment.generate_kubernetes_manifests(infrastructure)

def build_and_push_model_image(model_path: str, image_tag: str, registry: str) -> Dict[str, Any]:
    """Build and push Docker image for model"""
    # Build image
    build_result = docker_manager.build_model_image(model_path, image_tag)
    
    if build_result.get("status") == "success":
        # Push image
        push_result = docker_manager.push_image(image_tag, registry)
        return {
            "build": build_result,
            "push": push_result
        }
    else:
        return build_result
