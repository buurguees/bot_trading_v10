from datetime import datetime, timezone, timedelta
import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)


class TimestampManager:
    """Gestor centralizado de timestamps para APIs (ms y UTC).

    Proporciona conversiones seguras a milisegundos para APIs como Bitget
    y utilidades de normalización/validación.
    """

    @staticmethod
    def to_unix_timestamp_ms(dt: Union[datetime, str, int, float]) -> int:
        """Convierte a timestamp UNIX en milisegundos.

        - datetime naive → UTC
        - str ISO8601 soporta sufijo Z
        - int/float en segundos o ms
        - clamp a [2020-01-01, now + 1d]
        """
        try:
            if isinstance(dt, (int, float)):
                # Si parece segundos, convertir a ms
                return int(dt * 1000) if dt < 1e12 else int(dt)

            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            if isinstance(dt, datetime):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                elif dt.tzinfo != timezone.utc:
                    dt = dt.astimezone(timezone.utc)

                ts_ms = int(dt.timestamp() * 1000)

                min_ts = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
                max_ts = int(datetime.now(timezone.utc).timestamp() * 1000) + 86_400_000

                if ts_ms < min_ts:
                    logger.warning("Timestamp muy antiguo; usando mínimo 2020-01-01")
                    return min_ts
                if ts_ms > max_ts:
                    logger.warning("Timestamp en futuro; usando now+1d")
                    return max_ts
                return ts_ms

        except Exception as e:
            logger.error(f"Error convirtiendo timestamp {dt}: {e}")

        # Fallback: ahora - 1 año
        fallback = datetime.now(timezone.utc) - timedelta(days=365)
        return int(fallback.timestamp() * 1000)

    @staticmethod
    def safe_datetime_conversion(dt: Union[datetime, str, None]) -> Optional[datetime]:
        """Convierte a datetime UTC de forma segura."""
        try:
            if dt is None:
                return None
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            if isinstance(dt, datetime):
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            return None
        except Exception as e:
            logger.error(f"Error en conversión datetime: {e}")
            return None

    @staticmethod
    def normalize_timestamp(ts: Union[int, float]) -> int:
        """Normaliza timestamp a milisegundos."""
        try:
            return int(ts * 1000) if ts < 1e12 else int(ts)
        except Exception:
            return int(datetime.now(timezone.utc).timestamp() * 1000)

    @staticmethod
    def to_datetime(ts: Union[int, float]) -> datetime:
        """Convierte timestamp (s o ms) a datetime UTC."""
        try:
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)


