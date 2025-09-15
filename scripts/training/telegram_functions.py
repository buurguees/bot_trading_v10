# Funciones para integración con Telegram
async def execute_train_hist_for_telegram(progress_file: str, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
    """
    Función principal para ejecutar entrenamiento histórico desde Telegram
    
    Args:
        progress_file: Archivo de progreso para Telegram
        start_date: Fecha de inicio (opcional)
        end_date: Fecha de fin (opcional)
        
    Returns:
        Resultados del entrenamiento formateados para Telegram
    """
    try:
        logger.info("🚀 Iniciando entrenamiento histórico desde Telegram...")
        
        # Crear instancia del entrenador
        trainer = TrainHistParallel(progress_file=progress_file)
        
        # Configurar fechas por defecto si no se proporcionan
        if start_date is None or end_date is None:
            training_mode = trainer._load_training_mode_from_user_settings()
            if end_date is None:
                end_date = datetime.now() - timedelta(days=1)  # Hasta ayer
            if start_date is None:
                start_date = end_date - timedelta(days=trainer._get_training_days(training_mode))
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        # Formatear resultados para Telegram
        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = results.get("telegram_summary", "Entrenamiento completado exitosamente")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento para Telegram: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Error en entrenamiento: {str(e)[:100]}...",
            "telegram_ready": True
        }

async def execute_train_hist_continuous_for_telegram(progress_file: str, cycle_days: int = 7) -> Dict[str, Any]:
    """
    Función para entrenamiento continuo desde Telegram
    
    Args:
        progress_file: Archivo de progreso para Telegram
        cycle_days: Días por ciclo de entrenamiento
        
    Returns:
        Resultados del entrenamiento continuo
    """
    try:
        logger.info(f"🔄 Iniciando entrenamiento continuo desde Telegram (ciclos de {cycle_days} días)...")
        
        # Crear instancia del entrenador
        trainer = TrainHistParallel(progress_file=progress_file)
        
        # Configurar fechas para el ciclo
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=cycle_days)
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        # Formatear resultados para Telegram
        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = f"Entrenamiento continuo completado (últimos {cycle_days} días)"
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento continuo para Telegram: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Error en entrenamiento continuo: {str(e)[:100]}...",
            "telegram_ready": True
        }

# Función principal para ejecución desde línea de comandos
async def main():
    """Función principal para ejecución desde línea de comandos"""
    parser = argparse.ArgumentParser(description='Entrenamiento Histórico Paralelo - Bot Trading v10')
    parser.add_argument('--progress-file', type=str, help='Archivo de progreso para Telegram')
    parser.add_argument('--start-date', type=str, help='Fecha de inicio (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Fecha de fin (YYYY-MM-DD)')
    parser.add_argument('--mode', type=str, default='ultra_fast', help='Modo de entrenamiento')
    
    args = parser.parse_args()
    
    try:
        # Crear instancia del entrenador
        trainer = TrainHistParallel(progress_file=args.progress_file)
        
        # Configurar fechas
        start_date = None
        end_date = None
        
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        print("✅ Entrenamiento completado exitosamente")
        print(f"📊 Resultados: {json.dumps(results, indent=2, default=str)}")
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
