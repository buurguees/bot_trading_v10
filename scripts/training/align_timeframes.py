#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/training/align_timeframes.py
=====================================
Script manual para generar alineamiento de timeframes multi-símbolo.
Guarda en data/aligned_timeframes.json para reutilización.

Uso: python scripts/training/align_timeframes.py --days-back 365
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.unified_config import get_config_manager
from core.data.database import DatabaseManager  # Asume maneja queries a datos históricos
from core.data.temporal_alignment import TemporalAlignment  # Asume módulo genérico para alineamiento

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeframeAligner:
    def __init__(self, days_back: int = 365):
        self.config = get_config_manager()
        self.symbols = self.config.get_symbols()
        self.timeframes = self.config.get_timeframes()
        self.start_date = datetime.now() - timedelta(days=days_back)
        self.end_date = datetime.now()
        self.db_manager = DatabaseManager()  # Inicializa DB para datos históricos
        self.alignment_path = Path("data/aligned_timeframes.json")

    async def generate_alignment(self) -> Dict:
        """Genera alineamiento sincronizado por timestamps."""
        alignment = {}
        try:
            # Usar asyncio.gather para paralelizar por símbolo
            tasks = [self._align_symbol(symbol) for symbol in self.symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(self.symbols, results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Error alineando {symbol}: {result}")
                    continue
                alignment[symbol] = result
            
            # Guardar en JSON
            with open(self.alignment_path, 'w') as f:
                json.dump(alignment, f, indent=2, default=str)
            logger.info(f"✅ Alineamiento guardado en {self.alignment_path}")
            
            return alignment
        except Exception as e:
            logger.error(f"❌ Error general: {e}")
            return {}

    async def _align_symbol(self, symbol: str) -> Dict:
        """Alinea TFs para un símbolo (usando temporal_alignment.py)."""
        data = {}  # Cargar datos históricos desde DB
        for tf in self.timeframes:
            data[tf] = await self.db_manager.get_historical_data(symbol, tf, self.start_date, self.end_date)
        
        # Usar módulo genérico para alineamiento
        aligner = TemporalAlignment()
        aligned_data = aligner.align_multi_timeframe(data)  # Asume método que sincroniza por timestamps
        
        return {
            "symbol": symbol,
            "aligned_timestamps": aligned_data['timestamps'],  # Lista de timestamps sincronizados
            "aligned_data": aligned_data['data']  # Dict por TF con datos alineados
        }

async def main(days_back: int):
    aligner = TimeframeAligner(days_back)
    await aligner.generate_alignment()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar alineamiento de TFs manualmente.")
    parser.add_argument('--days-back', type=int, default=365, help="Días hacia atrás para datos.")
    args = parser.parse_args()
    asyncio.run(main(args.days_back))