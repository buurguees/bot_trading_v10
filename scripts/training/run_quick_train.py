#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ejecutor rápido de entrenamiento paralelo (7 días)
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Asegurar importación desde la raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.training.train_hist_parallel import TrainHistParallel


async def main():
    trainer = TrainHistParallel(progress_file="data/tmp/quick_train_progress.json")
    # Forzar modo SIMULACIÓN para prueba rápida sin datos locales
    trainer.force_simulate = True
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)
    results = await trainer.execute_training(start_date=start_date, end_date=end_date)
    gp = results.get("global_performance", {})
    print("OK", gp)
    if "cycle_metrics" in results:
        print("CYCLE", results["cycle_metrics"])


if __name__ == "__main__":
    asyncio.run(main())


