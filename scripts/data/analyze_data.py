#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para análisis automático de datos históricos al iniciar el bot.
Analiza issues (gaps, duplicados) desde 01/09/2024 hasta ahora.
Llama core/data/history_analyzer.py.
Retorna JSON para bot.py.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Importar módulos locales
from config.unified_config import get_config_manager

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/analyze_data.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class AnalyzeDataEnterprise:
    """Análisis enterprise de datos históricos"""

    def __init__(self, progress_id: str = None, auto_repair: bool = False):
        self.progress_id = progress_id
        self.auto_repair = auto_repair
        self.config = get_config_manager()
        self.analyzer = None
        self._init_progress_file()

    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)

    def _update_progress(self, progress: int, current_symbol: str, status: str = "Analizando"):
        if self.progress_id:
            try:
                progress_path = Path("data/tmp") / f"{self.progress_id}.json"
                # Crear directorio si no existe
                progress_path.parent.mkdir(parents=True, exist_ok=True)
                
                bar_length = 10
                filled = int(progress / 100 * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                data = {"progress": progress, "bar": bar, "current_symbol": current_symbol, "status": status}
                
                # Escribir de forma segura
                with open(progress_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                    f.flush()  # Asegurar que se escriba
                    
            except Exception as e:
                # Si hay error, solo logear, no fallar
                print(f"⚠️ Error actualizando progreso: {e}")

    def _update_progress_safe(self, progress: int, current_symbol: str, status: str = "Analizando"):
        """Versión segura del método _update_progress"""
        self._update_progress(progress, current_symbol, status)

    async def initialize(self) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from core.data.history_analyzer import HistoryAnalyzer
                self.analyzer = HistoryAnalyzer()
                self._update_progress_safe(10, "Inicializando analyzer", "Configurando core/")
                logger.info("✅ Analyzer inicializado")
                return True
            except Exception as e:
                logger.error(f"❌ Error inicializando analyzer (intento {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        return False

    async def execute(self, symbols: List[str] = None, timeframes: List[str] = None, start_date: datetime = None) -> Dict:
        """Ejecuta análisis de datos históricos desde start_date"""
        try:
            if not await self.initialize():
                return {"status": "error", "message": "No se pudo inicializar el analyzer"}

            # Cargar configuración si no se proporcionan parámetros
            symbols = symbols or self.config.get_symbols() or ['BTCUSDT']
            timeframes = timeframes or self.config.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
            start_date = start_date or datetime(2024, 9, 1, tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)

            issues_by_symbol = {}
            total_issues = 0
            total_symbols = len(symbols)
            step = 0

            # Procesar cada símbolo y generar reportes
            for symbol in symbols:
                self._update_progress_safe(int((step / total_symbols) * 90) + 10, symbol)
                try:
                    issues = await self.analyzer.detect_data_issues([symbol])
                    sym_issues = issues.get("symbol_issues", {}).get(symbol, {})
                    total_issues += len(sym_issues.get("issues", []))
                    issues_by_symbol[symbol] = sym_issues
                    # Generar reporte por símbolo (ahora con lógica optimizada)
                    self._generate_symbol_report(symbol, sym_issues)
                    step += 1
                except Exception as e:
                    logger.error(f"❌ {symbol}: {e}")
                    issues_by_symbol[symbol] = {"total_issues": 0, "status": "error"}
                    # Manejar errores en el estado global
                    if not hasattr(self, '_symbol_states'):
                        self._symbol_states = {}
                    self._symbol_states[symbol] = {
                        'gaps': 0,
                        'duplicates': 0,
                        'invalid': 0,
                        'is_clean': False,
                        'status': f"Error: {str(e)}"
                    }
                    step += 1

            # Generar reportes por símbolo (solo los que tienen problemas)
            symbol_reports = []
            for symbol in symbols:
                if symbol in issues_by_symbol:
                    issues = issues_by_symbol[symbol]
                    report = self._generate_symbol_report(symbol, issues)
                    if report:  # Solo agregar si tiene contenido (hay problemas)
                        symbol_reports.append(report)

            # Determinar qué tipo de mensaje mostrar
            if symbol_reports:
                # Hay símbolos con problemas - mostrar detalle + resumen global
                global_summary = self._generate_global_summary()
                final_report = global_summary + "\n\n" + "\n".join(symbol_reports)
            else:
                # Todos limpios - solo resumen global
                final_report = self._generate_global_summary()

            self._update_progress_safe(100, "Completado", "completed")
            return {
                "status": "success",
                "report": [final_report],  # Mantener formato de lista para compatibilidad
                "total_issues": total_issues,
                "issues_by_symbol": issues_by_symbol
            }

        except Exception as e:
            logger.error(f"❌ Error análisis: {e}")
            self._update_progress_safe(0, "Error", "error")
            return {"status": "error", "message": str(e)}

    def _generate_symbol_report(self, symbol: str, issues: Dict) -> str:
        """
        Genera reporte por símbolo con formato optimizado.
        Si todos los datos están limpios, muestra resumen global.
        Si hay problemas, muestra detalle por símbolo.
        """
        issues_list = issues.get("issues", [])
        
        # Contar diferentes tipos de issues
        gaps = 0
        duplicates = 0
        invalid = 0
        errors = 0
        
        for issue in issues_list:
            description = issue.get("description", "").lower()
            if "gap" in description:
                gaps += 1
            elif "duplicate" in description:
                duplicates += 1
            elif "invalid" in description:
                invalid += 1
            elif "error" in description:
                errors += 1
        
        total_issues = len(issues_list)
        
        # Determinar si hay problemas reales (excluyendo errores de análisis limitado)
        real_issues = gaps + duplicates + invalid
        
        # Si hay errores de análisis pero no problemas reales, considerar como limpio
        if errors > 0 and real_issues == 0:
            status = "Datos disponibles (análisis limitado)"
            is_clean = True
        elif total_issues == 0:
            status = "Datos disponibles"
            is_clean = True
        else:
            status = "Issues encontrados"
            is_clean = False
        
        # Guardar estado para usar en el resumen global
        if not hasattr(self, '_symbol_states'):
            self._symbol_states = {}
        
        self._symbol_states[symbol] = {
            'gaps': gaps,
            'duplicates': duplicates,
            'invalid': invalid,
            'is_clean': is_clean,
            'status': status
        }
        
        # Si hay problemas reales, mostrar detalle por símbolo
        if real_issues > 0:
            report = f"""
<b>🔍 {symbol}:</b>
• Gaps: {gaps}
• Duplicados: {duplicates}
• Inválidos: {invalid}
• Estado: ⚠️ {status}
            """
            return report.strip()
        
        # Si está limpio, contribuir al resumen global (se procesará al final)
        return ""  # No mostrar detalle individual si está limpio

    def _generate_global_summary(self) -> str:
        """
        Genera resumen global cuando todos los símbolos están limpios
        o hay pocos problemas.
        """
        if not hasattr(self, '_symbol_states'):
            return ""
        
        total_symbols = len(self._symbol_states)
        clean_symbols = sum(1 for state in self._symbol_states.values() if state['is_clean'])
        total_gaps = sum(state['gaps'] for state in self._symbol_states.values())
        total_duplicates = sum(state['duplicates'] for state in self._symbol_states.values())
        total_invalid = sum(state['invalid'] for state in self._symbol_states.values())
        
        # Si todos están limpios o solo hay problemas mínimos
        if clean_symbols == total_symbols:
            return f"""
<b>📊 Análisis de datos completado:</b>
• Gaps: {total_gaps}
• Duplicados: {total_duplicates} 
• Inválidos: {total_invalid}
• Estado: ✅ Datos disponibles
            """.strip()
        
        # Si hay algunos problemas, mostrar resumen con detalle de símbolos problemáticos
        problematic_symbols = [
            symbol for symbol, state in self._symbol_states.items() 
            if not state['is_clean']
        ]
        
        summary = f"""
<b>📊 Análisis de datos completado:</b>
• Símbolos analizados: {total_symbols}
• Símbolos limpios: {clean_symbols}
• Símbolos con problemas: {len(problematic_symbols)}
• Total gaps: {total_gaps}
• Total duplicados: {total_duplicates}
• Total inválidos: {total_invalid}

<b>🔍 Símbolos con problemas:</b>
        """
        
        for symbol in problematic_symbols:
            state = self._symbol_states[symbol]
            summary += f"\n• {symbol}: G:{state['gaps']} D:{state['duplicates']} I:{state['invalid']}"
        
        return summary.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = AnalyzeDataEnterprise(progress_id=args.progress_id, auto_repair=False)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())