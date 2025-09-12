import asyncio
from datetime import datetime, timedelta, timezone
from config.unified_config import get_config_manager
from core.utils.timestamp_utils import TimestampManager as TS
from core.data.collector import BitgetDataCollector


async def main():
    cm = get_config_manager()
    print('CFG OK:', bool(cm))
    now = datetime.now(timezone.utc)
    print('TS now ms:', TS.to_unix_timestamp_ms(now))
    collector = BitgetDataCollector()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=2)

    class P:
        downloaded_periods = 0
        total_records = 0
        errors = 0

    try:
        df = await collector.fetch_historical_data_chunk('BTCUSDT', '1h', start, end, P())
        print('CHUNK ROWS:', 0 if df is None else len(df))
    except Exception as e:
        print('ERR CHUNK:', e)


if __name__ == '__main__':
    asyncio.run(main())


