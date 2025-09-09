# Ruta: core/monitoring/enterprise/dashboard_generator.py
# dashboard_generator.py - Generador de dashboards enterprise
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\dashboard_generator.py

"""
Generador de dashboards enterprise para Grafana.

Características:
- Generación automática de dashboards
- Dashboards predefinidos para trading
- Dashboards personalizables
- Integración con Prometheus
- Exportación a Grafana
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import requests
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class DashboardPanel:
    """Panel de dashboard"""
    id: int
    title: str
    type: str
    targets: List[Dict[str, Any]]
    gridPos: Dict[str, int]
    options: Optional[Dict[str, Any]] = None
    fieldConfig: Optional[Dict[str, Any]] = None

@dataclass
class Dashboard:
    """Dashboard de Grafana"""
    title: str
    description: str
    panels: List[DashboardPanel]
    refresh: str = "30s"
    time_range: str = "1h"
    tags: List[str] = None
    folder: str = "Trading Bot"

class DashboardGenerator:
    """Generador de dashboards enterprise"""
    
    def __init__(self, grafana_url: str = "http://localhost:3000", api_key: Optional[str] = None):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        
        # Configurar directorios
        self.dashboards_dir = Path("monitoring/grafana/dashboards")
        self.dashboards_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Configurar headers para API
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def setup_logging(self):
        """Configura logging del generador"""
        dashboard_logger = logging.getLogger(f"{__name__}.DashboardGenerator")
        dashboard_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.dashboards_dir / "dashboard_generator.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        dashboard_logger.addHandler(file_handler)
        self.dashboard_logger = dashboard_logger
    
    def create_trading_overview_dashboard(self) -> Dashboard:
        """Crea dashboard de overview de trading"""
        panels = [
            # Panel de estado del sistema
            DashboardPanel(
                id=1,
                title="Estado del Sistema",
                type="stat",
                targets=[
                    {
                        "expr": "up{job='trading_bot_main'}",
                        "legendFormat": "Bot Principal",
                        "refId": "A"
                    },
                    {
                        "expr": "up{job='trading_bot_data_collection'}",
                        "legendFormat": "Data Collection",
                        "refId": "B"
                    },
                    {
                        "expr": "up{job='trading_bot_ml_training'}",
                        "legendFormat": "ML Training",
                        "refId": "C"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 0},
                options={
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto"
                }
            ),
            
            # Panel de balance de cuenta
            DashboardPanel(
                id=2,
                title="Balance de Cuenta",
                type="stat",
                targets=[
                    {
                        "expr": "trading_account_balance_usd",
                        "legendFormat": "USD",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 0},
                options={
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto"
                }
            ),
            
            # Panel de trades por segundo
            DashboardPanel(
                id=3,
                title="Trades por Segundo",
                type="graph",
                targets=[
                    {
                        "expr": "rate(trading_trades_executed_total[1m])",
                        "legendFormat": "{{symbol}} - {{side}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de PnL
            DashboardPanel(
                id=4,
                title="PnL por Símbolo",
                type="graph",
                targets=[
                    {
                        "expr": "trading_trades_pnl_total",
                        "legendFormat": "{{symbol}} - {{side}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de posiciones abiertas
            DashboardPanel(
                id=5,
                title="Posiciones Abiertas",
                type="table",
                targets=[
                    {
                        "expr": "trading_open_positions_count",
                        "legendFormat": "{{symbol}} - {{side}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 16},
                options={
                    "showHeader": True,
                    "sortBy": [{"desc": True, "displayName": "Value"}]
                }
            ),
            
            # Panel de tiempo de ejecución
            DashboardPanel(
                id=6,
                title="Tiempo de Ejecución de Órdenes",
                type="graph",
                targets=[
                    {
                        "expr": "histogram_quantile(0.95, trading_order_execution_time_seconds)",
                        "legendFormat": "P95 - {{symbol}}",
                        "refId": "A"
                    },
                    {
                        "expr": "histogram_quantile(0.50, trading_order_execution_time_seconds)",
                        "legendFormat": "P50 - {{symbol}}",
                        "refId": "B"
                    }
                ],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 24},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            )
        ]
        
        return Dashboard(
            title="Trading Bot - Overview",
            description="Dashboard principal del sistema de trading",
            panels=panels,
            refresh="30s",
            time_range="1h",
            tags=["trading", "overview"],
            folder="Trading Bot"
        )
    
    def create_ml_training_dashboard(self) -> Dashboard:
        """Crea dashboard de entrenamiento ML"""
        panels = [
            # Panel de estado de entrenamiento
            DashboardPanel(
                id=1,
                title="Estado de Entrenamiento",
                type="stat",
                targets=[
                    {
                        "expr": "up{job='trading_bot_ml_training'}",
                        "legendFormat": "ML Training",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 0},
                options={
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto"
                }
            ),
            
            # Panel de epochs completados
            DashboardPanel(
                id=2,
                title="Epochs Completados",
                type="stat",
                targets=[
                    {
                        "expr": "ml_training_epochs_total",
                        "legendFormat": "{{model_name}} - {{symbol}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 0},
                options={
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto"
                }
            ),
            
            # Panel de loss de entrenamiento
            DashboardPanel(
                id=3,
                title="Training Loss",
                type="graph",
                targets=[
                    {
                        "expr": "ml_training_loss",
                        "legendFormat": "{{model_name}} - {{symbol}} - {{phase}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de accuracy
            DashboardPanel(
                id=4,
                title="Training Accuracy",
                type="graph",
                targets=[
                    {
                        "expr": "ml_training_accuracy",
                        "legendFormat": "{{model_name}} - {{symbol}} - {{phase}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de tiempo de inferencia
            DashboardPanel(
                id=5,
                title="Tiempo de Inferencia",
                type="graph",
                targets=[
                    {
                        "expr": "histogram_quantile(0.95, ml_model_inference_time_seconds)",
                        "legendFormat": "P95 - {{model_name}}",
                        "refId": "A"
                    },
                    {
                        "expr": "histogram_quantile(0.50, ml_model_inference_time_seconds)",
                        "legendFormat": "P50 - {{model_name}}",
                        "refId": "B"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de confianza del modelo
            DashboardPanel(
                id=6,
                title="Confianza del Modelo",
                type="graph",
                targets=[
                    {
                        "expr": "ml_model_confidence",
                        "legendFormat": "{{model_name}} - {{symbol}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de predicciones
            DashboardPanel(
                id=7,
                title="Predicciones del Modelo",
                type="graph",
                targets=[
                    {
                        "expr": "rate(ml_model_predictions_total[1m])",
                        "legendFormat": "{{model_name}} - {{symbol}} - {{prediction_type}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 24},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            )
        ]
        
        return Dashboard(
            title="ML Training - Monitoreo",
            description="Dashboard de monitoreo de entrenamiento ML",
            panels=panels,
            refresh="15s",
            time_range="6h",
            tags=["ml", "training"],
            folder="Trading Bot"
        )
    
    def create_data_collection_dashboard(self) -> Dashboard:
        """Crea dashboard de data collection"""
        panels = [
            # Panel de estado de data collection
            DashboardPanel(
                id=1,
                title="Estado de Data Collection",
                type="stat",
                targets=[
                    {
                        "expr": "up{job='trading_bot_data_collection'}",
                        "legendFormat": "Data Collection",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 0},
                options={
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto"
                }
            ),
            
            # Panel de ticks por segundo
            DashboardPanel(
                id=2,
                title="Ticks por Segundo",
                type="graph",
                targets=[
                    {
                        "expr": "rate(data_collection_ticks_received_total[1m])",
                        "legendFormat": "{{symbol}} - {{source}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 0},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de latencia de procesamiento
            DashboardPanel(
                id=3,
                title="Latencia de Procesamiento",
                type="graph",
                targets=[
                    {
                        "expr": "histogram_quantile(0.95, data_collection_processing_latency_seconds)",
                        "legendFormat": "P95 - {{symbol}}",
                        "refId": "A"
                    },
                    {
                        "expr": "histogram_quantile(0.50, data_collection_processing_latency_seconds)",
                        "legendFormat": "P50 - {{symbol}}",
                        "refId": "B"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de conexiones WebSocket
            DashboardPanel(
                id=4,
                title="Conexiones WebSocket",
                type="graph",
                targets=[
                    {
                        "expr": "data_collection_websocket_connections_active",
                        "legendFormat": "{{exchange}} - {{symbol}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de mensajes Kafka
            DashboardPanel(
                id=5,
                title="Mensajes Kafka",
                type="graph",
                targets=[
                    {
                        "expr": "rate(data_collection_kafka_messages_sent_total[1m])",
                        "legendFormat": "{{topic}} - {{status}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de operaciones Redis
            DashboardPanel(
                id=6,
                title="Operaciones Redis",
                type="graph",
                targets=[
                    {
                        "expr": "rate(data_collection_redis_operations_total[1m])",
                        "legendFormat": "{{operation_type}} - {{status}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de inserts TimescaleDB
            DashboardPanel(
                id=7,
                title="Inserts TimescaleDB",
                type="graph",
                targets=[
                    {
                        "expr": "rate(data_collection_timescaledb_inserts_total[1m])",
                        "legendFormat": "{{table}} - {{status}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 24},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            )
        ]
        
        return Dashboard(
            title="Data Collection - Monitoreo",
            description="Dashboard de monitoreo de recolección de datos",
            panels=panels,
            refresh="10s",
            time_range="1h",
            tags=["data", "collection"],
            folder="Trading Bot"
        )
    
    def create_system_performance_dashboard(self) -> Dashboard:
        """Crea dashboard de rendimiento del sistema"""
        panels = [
            # Panel de CPU
            DashboardPanel(
                id=1,
                title="Uso de CPU",
                type="graph",
                targets=[
                    {
                        "expr": "system_cpu_usage_percent",
                        "legendFormat": "CPU {{core}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 0},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de memoria
            DashboardPanel(
                id=2,
                title="Uso de Memoria",
                type="graph",
                targets=[
                    {
                        "expr": "system_memory_usage_bytes",
                        "legendFormat": "{{type}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 0},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de GPU
            DashboardPanel(
                id=3,
                title="Uso de GPU",
                type="graph",
                targets=[
                    {
                        "expr": "performance_gpu_utilization_percent",
                        "legendFormat": "GPU {{gpu_id}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de memoria GPU
            DashboardPanel(
                id=4,
                title="Memoria GPU",
                type="graph",
                targets=[
                    {
                        "expr": "performance_gpu_memory_usage_bytes",
                        "legendFormat": "GPU {{gpu_id}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 8},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de disco
            DashboardPanel(
                id=5,
                title="Uso de Disco",
                type="graph",
                targets=[
                    {
                        "expr": "system_disk_usage_bytes",
                        "legendFormat": "{{mount_point}} - {{type}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de red
            DashboardPanel(
                id=6,
                title="Tráfico de Red",
                type="graph",
                targets=[
                    {
                        "expr": "rate(system_network_io_bytes_total[1m])",
                        "legendFormat": "{{direction}} - {{interface}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 16},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            ),
            
            # Panel de load average
            DashboardPanel(
                id=7,
                title="Load Average",
                type="graph",
                targets=[
                    {
                        "expr": "system_load_average",
                        "legendFormat": "{{period}}",
                        "refId": "A"
                    }
                ],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 24},
                options={
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi", "sort": "none"}
                }
            )
        ]
        
        return Dashboard(
            title="Sistema - Rendimiento",
            description="Dashboard de rendimiento del sistema",
            panels=panels,
            refresh="30s",
            time_range="1h",
            tags=["system", "performance"],
            folder="Trading Bot"
        )
    
    def dashboard_to_grafana_json(self, dashboard: Dashboard) -> Dict[str, Any]:
        """Convierte dashboard a formato JSON de Grafana"""
        grafana_dashboard = {
            "dashboard": {
                "id": None,
                "title": dashboard.title,
                "description": dashboard.description,
                "tags": dashboard.tags or [],
                "timezone": "browser",
                "refresh": dashboard.refresh,
                "time": {
                    "from": f"now-{dashboard.time_range}",
                    "to": "now"
                },
                "panels": [],
                "templating": {
                    "list": []
                },
                "annotations": {
                    "list": []
                },
                "schemaVersion": 30,
                "version": 0,
                "links": []
            }
        }
        
        # Convertir panels
        for panel in dashboard.panels:
            grafana_panel = {
                "id": panel.id,
                "title": panel.title,
                "type": panel.type,
                "gridPos": panel.gridPos,
                "targets": panel.targets,
                "options": panel.options or {},
                "fieldConfig": panel.fieldConfig or {
                    "defaults": {},
                    "overrides": []
                }
            }
            
            grafana_dashboard["dashboard"]["panels"].append(grafana_panel)
        
        return grafana_dashboard
    
    def save_dashboard(self, dashboard: Dashboard, filename: Optional[str] = None):
        """Guarda dashboard en archivo JSON"""
        if filename is None:
            filename = f"{dashboard.title.lower().replace(' ', '_')}.json"
        
        dashboard_file = self.dashboards_dir / filename
        
        try:
            grafana_json = self.dashboard_to_grafana_json(dashboard)
            
            with open(dashboard_file, 'w') as f:
                json.dump(grafana_json, f, indent=2, ensure_ascii=False)
            
            self.dashboard_logger.info(f"📊 Dashboard guardado: {dashboard_file}")
            
        except Exception as e:
            self.dashboard_logger.error(f"Error guardando dashboard: {e}")
    
    def upload_dashboard_to_grafana(self, dashboard: Dashboard) -> bool:
        """Sube dashboard a Grafana"""
        try:
            grafana_json = self.dashboard_to_grafana_json(dashboard)
            
            # Crear o actualizar dashboard
            url = f"{self.grafana_url}/api/dashboards/db"
            
            response = requests.post(
                url,
                headers=self.headers,
                json=grafana_json
            )
            
            if response.status_code == 200:
                self.dashboard_logger.info(f"✅ Dashboard subido a Grafana: {dashboard.title}")
                return True
            else:
                self.dashboard_logger.error(f"Error subiendo dashboard: {response.text}")
                return False
                
        except Exception as e:
            self.dashboard_logger.error(f"Error subiendo dashboard a Grafana: {e}")
            return False
    
    def generate_all_dashboards(self):
        """Genera todos los dashboards predefinidos"""
        dashboards = [
            ("trading_overview", self.create_trading_overview_dashboard()),
            ("ml_training", self.create_ml_training_dashboard()),
            ("data_collection", self.create_data_collection_dashboard()),
            ("system_performance", self.create_system_performance_dashboard())
        ]
        
        for name, dashboard in dashboards:
            try:
                # Guardar en archivo
                self.save_dashboard(dashboard, f"{name}.json")
                
                # Subir a Grafana si está configurado
                if self.api_key:
                    self.upload_dashboard_to_grafana(dashboard)
                
            except Exception as e:
                self.dashboard_logger.error(f"Error generando dashboard {name}: {e}")
    
    def create_custom_dashboard(
        self,
        title: str,
        description: str,
        panels: List[DashboardPanel],
        refresh: str = "30s",
        time_range: str = "1h",
        tags: List[str] = None
    ) -> Dashboard:
        """Crea dashboard personalizado"""
        return Dashboard(
            title=title,
            description=description,
            panels=panels,
            refresh=refresh,
            time_range=time_range,
            tags=tags or []
        )

# Funciones de utilidad
def create_dashboard_generator(
    grafana_url: str = "http://localhost:3000",
    api_key: Optional[str] = None
) -> DashboardGenerator:
    """Factory function para crear DashboardGenerator"""
    return DashboardGenerator(grafana_url, api_key)

def generate_all_dashboards(
    grafana_url: str = "http://localhost:3000",
    api_key: Optional[str] = None
):
    """Genera todos los dashboards"""
    generator = create_dashboard_generator(grafana_url, api_key)
    generator.generate_all_dashboards()
