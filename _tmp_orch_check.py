from config.unified_config import get_config_manager
from scripts.training.parallel_training_orchestrator import ParallelTrainingOrchestrator

def main():
    cm = get_config_manager()
    symbols = cm.get_symbols()
    timeframes = cm.get_timeframes() or ["1m", "5m"]
    if not isinstance(timeframes, list) or len(timeframes) < 2:
        timeframes = ["1m", "5m"]
    print("CFG OK")
    print("symbols", symbols[:5])
    print("timeframes", timeframes)
    orch = ParallelTrainingOrchestrator(symbols=symbols[:2], timeframes=timeframes[:2])
    print("ORCH OK", orch.session_id)

if __name__ == "__main__":
    main()


