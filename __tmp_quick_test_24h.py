import asyncio
from datetime import datetime, timedelta, timezone
from core.data.collector import BitgetDataCollector


async def main():
    collector = BitgetDataCollector()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    class P:
        downloaded_periods = 0
        total_records = 0
        errors = 0
    df = await collector.fetch_historical_data_chunk('BTCUSDT', '1h', start, end, P())
    print('24H ROWS:', 0 if df is None else len(df))
    if df is not None and not df.empty:
        print('FIRST:', df.index.min(), 'LAST:', df.index.max())

if __name__ == '__main__':
    asyncio.run(main())


