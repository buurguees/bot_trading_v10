# Ruta: core/monitoring/callbacks/live_trading_callbacks.py
"""
monitoring/callbacks/live_trading_callbacks.py
Callbacks para Página de Trading en Vivo - Trading Bot v10

Este módulo contiene todos los callbacks de Dash para la página de trading en vivo,
manejando posiciones activas, órdenes pendientes, señales del modelo en tiempo real,
controles del bot, métricas live y feed de actividad del sistema.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

import dash
from dash import Input, Output, State, callback, ctx, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Importaciones locales
from monitoring.core.data_provider import DataProvider
from monitoring.core.real_time_manager import RealTimeManager, RealTimeUpdate
from monitoring.core.performance_tracker import PerformanceTracker
from monitoring.config.chart_config import CHART_CONFIG, apply_theme, TRADING_COLORS
from monitoring.config.layout_config import LAYOUT_CONFIG

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN GLOBAL DE CALLBACKS
# ============================================================================

# Instancias globales (serán inyectadas por la aplicación principal)
data_provider: Optional[DataProvider] = None
real_time_manager: Optional[RealTimeManager] = None
performance_tracker: Optional[PerformanceTracker] = None

def initialize_live_trading_callbacks(dp: DataProvider, rtm: RealTimeManager, pt: PerformanceTracker):
    """
    Inicializa las instancias globales para los callbacks de live trading
    
    Args:
        dp (DataProvider): Proveedor de datos
        rtm (RealTimeManager): Gestor de tiempo real
        pt (PerformanceTracker): Tracker de rendimiento
    """
    global data_provider, real_time_manager, performance_tracker
    data_provider = dp
    real_time_manager = rtm
    performance_tracker = pt
    logger.info("⚡ Callbacks de Live Trading inicializados")

# ============================================================================
# CALLBACK PRINCIPAL: ACTUALIZACIÓN DE DATOS EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('live-trading-data-store', 'data'),
        Output('live-positions-store', 'data'),
        Output('live-orders-store', 'data'),
        Output('live-signals-store', 'data'),
        Output('live-last-update', 'children')
    ],
    [
        Input('live-fast-update', 'n_intervals'),
        Input('live-refresh-btn', 'n_clicks'),
        Input('live-emergency-refresh', 'n_clicks')
    ],
    [
        State('bot-status-store', 'data')
    ],
    prevent_initial_call=False
)
def update_live_trading_data(fast_intervals: int, refresh_clicks: int,
                           emergency_clicks: int, bot_status: Dict[str, Any]) -> Tuple:
    """
    Callback principal para actualizar todos los datos de trading en vivo
    """
    try:
        # Determinar tipo de actualización
        triggered_id = ctx.triggered_id if ctx.triggered else None
        is_emergency = triggered_id == 'live-emergency-refresh'
        
        # Obtener datos de trading en vivo
        trading_data = _get_live_trading_data(force_refresh=is_emergency)
        
        # Obtener posiciones activas
        positions_data = _get_active_positions()
        
        # Obtener órdenes pendientes
        orders_data = _get_pending_orders()
        
        # Obtener señales del modelo
        signals_data = _get_model_signals()
        
        # Timestamp de última actualización
        last_update = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Con milisegundos
        
        logger.debug(f"⚡ Datos live actualizados: {len(positions_data.get('positions', []))} posiciones")
        
        return trading_data, positions_data, orders_data, signals_data, f"Live: {last_update}"
        
    except Exception as e:
        logger.error(f"❌ Error actualizando datos live: {e}")
        
        # Datos de fallback
        empty_data = {'error': str(e), 'timestamp': datetime.now().isoformat()}
        error_message = f"Error: {datetime.now().strftime('%H:%M:%S')}"
        
        return empty_data, empty_data, empty_data, empty_data, error_message

# ============================================================================
# CALLBACK: POSICIONES ACTIVAS
# ============================================================================

@callback(
    [
        Output('active-positions-table', 'data'),
        Output('active-positions-table', 'columns'),
        Output('positions-count-badge', 'children'),
        Output('positions-pnl-total', 'children'),
        Output('positions-pnl-total', 'color')
    ],
    [
        Input('live-positions-store', 'data'),
        Input('positions-refresh-interval', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_active_positions(positions_data: Dict[str, Any], 
                          n_intervals: int, theme: str) -> Tuple:
    """
    Actualiza la tabla de posiciones activas
    """
    try:
        if not positions_data or 'error' in positions_data:
            return [], [], "0", "$0.00", "secondary"
        
        positions = positions_data.get('positions', [])
        
        if not positions:
            return [], [], "0", "$0.00", "secondary"
        
        # Configurar columnas de la tabla
        columns = _get_positions_table_columns()
        
        # Formatear datos para la tabla
        table_data = _format_positions_for_table(positions)
        
        # Calcular métricas agregadas
        positions_count = len(positions)
        total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        pnl_color = "success" if total_pnl >= 0 else "danger"
        
        return table_data, columns, str(positions_count), f"${total_pnl:+,.2f}", pnl_color
        
    except Exception as e:
        logger.error(f"❌ Error actualizando posiciones: {e}")
        return [], [], "Error", "Error", "warning"

# ============================================================================
# CALLBACK: ÓRDENES PENDIENTES
# ============================================================================

@callback(
    [
        Output('pending-orders-table', 'data'),
        Output('pending-orders-table', 'columns'),
        Output('orders-count-badge', 'children'),
        Output('orders-management-controls', 'style')
    ],
    [
        Input('live-orders-store', 'data'),
        Input('orders-filter-dropdown', 'value'),
        Input('orders-symbol-filter', 'value')
    ],
    prevent_initial_call=False
)
def update_pending_orders(orders_data: Dict[str, Any], 
                         order_filter: str, symbol_filter: str) -> Tuple:
    """
    Actualiza la tabla de órdenes pendientes
    """
    try:
        if not orders_data or 'error' in orders_data:
            return [], [], "0", {'display': 'none'}
        
        orders = orders_data.get('orders', [])
        
        # Aplicar filtros
        filtered_orders = _filter_orders(orders, order_filter, symbol_filter)
        
        if not filtered_orders:
            empty_columns = [{"name": "No hay órdenes", "id": "empty"}]
            empty_data = [{"empty": "No hay órdenes pendientes"}]
            return empty_data, empty_columns, "0", {'display': 'none'}
        
        # Configurar columnas
        columns = _get_orders_table_columns()
        
        # Formatear datos
        table_data = _format_orders_for_table(filtered_orders)
        
        # Mostrar controles si hay órdenes
        controls_style = {'display': 'block'}
        
        return table_data, columns, str(len(filtered_orders)), controls_style
        
    except Exception as e:
        logger.error(f"❌ Error actualizando órdenes: {e}")
        return [], [], "Error", {'display': 'none'}

# ============================================================================
# CALLBACK: SEÑALES DEL MODELO
# ============================================================================

@callback(
    [
        Output('signals-feed-container', 'children'),
        Output('signals-stats-cards', 'children'),
        Output('model-confidence-gauge', 'figure')
    ],
    [
        Input('live-signals-store', 'data'),
        Input('signals-filter-dropdown', 'value'),
        Input('model-update-interval', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_model_signals(signals_data: Dict[str, Any], signal_filter: str,
                        n_intervals: int, theme: str) -> Tuple:
    """
    Actualiza el feed de señales del modelo y estadísticas
    """
    try:
        if not signals_data or 'error' in signals_data:
            empty_feed = html.P("Cargando señales...", className="text-muted text-center py-3")
            empty_stats = html.Div()
            empty_gauge = _create_empty_gauge(theme)
            return empty_feed, empty_stats, empty_gauge
        
        signals = signals_data.get('signals', [])
        
        # Filtrar señales
        filtered_signals = _filter_signals(signals, signal_filter)
        
        # Crear feed de señales
        signals_feed = _create_signals_feed(filtered_signals, theme)
        
        # Crear estadísticas de señales
        stats_cards = _create_signals_stats_cards(signals)
        
        # Crear gauge de confianza del modelo
        confidence_gauge = _create_model_confidence_gauge(signals_data, theme)
        
        return signals_feed, stats_cards, confidence_gauge
        
    except Exception as e:
        logger.error(f"❌ Error actualizando señales: {e}")
        
        error_feed = dbc.Alert(f"Error: {str(e)}", color="danger", className="mb-0")
        error_stats = html.Div()
        error_gauge = _create_empty_gauge(theme)
        
        return error_feed, error_stats, error_gauge

# ============================================================================
# CALLBACK: CONTROLES DEL BOT
# ============================================================================

@callback(
    [
        Output('bot-status-store', 'data'),
        Output('bot-status-indicator', 'children'),
        Output('bot-status-indicator', 'color'),
        Output('bot-controls-feedback', 'children'),
        Output('bot-controls-feedback', 'is_open'),
        Output('start-bot-btn', 'disabled'),
        Output('pause-bot-btn', 'disabled'),
        Output('stop-bot-btn', 'disabled'),
        Output('emergency-stop-btn', 'disabled')
    ],
    [
        Input('start-bot-btn', 'n_clicks'),
        Input('pause-bot-btn', 'n_clicks'),
        Input('stop-bot-btn', 'n_clicks'),
        Input('emergency-stop-btn', 'n_clicks'),
        Input('bot-status-refresh', 'n_intervals')
    ],
    [
        State('bot-status-store', 'data')
    ],
    prevent_initial_call=False
)
def handle_bot_controls(start_clicks: int, pause_clicks: int, stop_clicks: int,
                       emergency_clicks: int, status_intervals: int,
                       current_status: Dict[str, Any]) -> Tuple:
    """
    Maneja los controles del bot y actualiza su estado
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        # Obtener estado actual del bot
        if not current_status:
            current_status = _get_bot_status()
        
        # Procesar acción de control
        if triggered_id and triggered_id != 'bot-status-refresh':
            action_result = _execute_bot_action(triggered_id, current_status)
            
            # Actualizar estado después de la acción
            new_status = action_result['new_status']
            feedback_alert = action_result['feedback']
            show_feedback = True
        else:
            # Solo actualización de estado
            new_status = _get_bot_status()
            feedback_alert = dbc.Alert()
            show_feedback = False
        
        # Determinar indicador de estado
        status_text, status_color = _get_status_indicator(new_status)
        
        # Determinar qué botones habilitar/deshabilitar
        buttons_state = _get_buttons_state(new_status)
        
        return (new_status, status_text, status_color, feedback_alert, show_feedback,
                buttons_state['start'], buttons_state['pause'], 
                buttons_state['stop'], buttons_state['emergency'])
        
    except Exception as e:
        logger.error(f"❌ Error en controles del bot: {e}")
        
        error_status = {'status': 'error', 'error': str(e)}
        error_alert = dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
        
        return (error_status, "ERROR", "danger", error_alert, True,
                False, False, False, False)

# ============================================================================
# CALLBACK: MÉTRICAS EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('live-pnl-gauge', 'figure'),
        Output('live-win-rate-gauge', 'figure'),
        Output('live-trades-counter', 'children'),
        Output('live-volume-counter', 'children'),
        Output('live-balance-display', 'children'),
        Output('live-drawdown-indicator', 'children'),
        Output('live-drawdown-indicator', 'color')
    ],
    [
        Input('live-trading-data-store', 'data'),
        Input('live-metrics-fast-update', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_live_metrics(trading_data: Dict[str, Any], n_intervals: int,
                       theme: str) -> Tuple:
    """
    Actualiza métricas en tiempo real con gauges y contadores
    """
    try:
        if not trading_data or 'error' in trading_data:
            # Métricas por defecto en caso de error
            empty_gauge = _create_empty_gauge(theme)
            return (empty_gauge, empty_gauge, "0", "$0", "$0.00", "0.0%", "secondary")
        
        # Obtener métricas específicas
        metrics = _get_live_metrics_detailed(trading_data)
        
        # Crear gauges
        pnl_gauge = _create_pnl_gauge(metrics['daily_pnl'], theme)
        win_rate_gauge = _create_win_rate_gauge(metrics['win_rate'], theme)
        
        # Formatear contadores
        trades_count = str(metrics['total_trades_today'])
        volume_display = f"${metrics['daily_volume']:,.0f}"
        balance_display = f"${metrics['total_balance']:,.2f}"
        
        # Indicador de drawdown
        drawdown = metrics['current_drawdown']
        drawdown_text = f"{drawdown:.1f}%"
        drawdown_color = "danger" if drawdown > 10 else "warning" if drawdown > 5 else "success"
        
        return (pnl_gauge, win_rate_gauge, trades_count, volume_display,
                balance_display, drawdown_text, drawdown_color)
        
    except Exception as e:
        logger.error(f"❌ Error actualizando métricas live: {e}")
        
        empty_gauge = _create_empty_gauge(theme)
        return (empty_gauge, empty_gauge, "Error", "Error", "Error", "Error", "danger")

# ============================================================================
# CALLBACK: ACTIVITY FEED
# ============================================================================

@callback(
    [
        Output('activity-feed-container', 'children'),
        Output('activity-auto-scroll', 'data')
    ],
    [
        Input('live-trading-data-store', 'data'),
        Input('activity-refresh-interval', 'n_intervals'),
        Input('clear-activity-btn', 'n_clicks')
    ],
    [
        State('activity-filter-dropdown', 'value'),
        State('activity-auto-scroll', 'data')
    ],
    prevent_initial_call=False
)
def update_activity_feed(trading_data: Dict[str, Any], n_intervals: int,
                        clear_clicks: int, activity_filter: str,
                        auto_scroll: bool) -> Tuple[html.Div, bool]:
    """
    Actualiza el feed de actividad del sistema
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        # Si se presionó clear, limpiar feed
        if triggered_id == 'clear-activity-btn':
            return html.Div([
                html.P("Feed de actividad limpiado", 
                      className="text-muted text-center py-3")
            ]), auto_scroll
        
        # Obtener actividades recientes
        activities = _get_recent_activities(trading_data, activity_filter)
        
        # Crear feed de actividad
        activity_feed = _create_activity_feed(activities)
        
        return activity_feed, auto_scroll
        
    except Exception as e:
        logger.error(f"❌ Error actualizando activity feed: {e}")
        
        error_feed = dbc.Alert(
            f"Error cargando actividad: {str(e)}",
            color="warning",
            className="mb-0"
        )
        
        return error_feed, auto_scroll

# ============================================================================
# CALLBACK: GESTIÓN DE ÓRDENES
# ============================================================================

@callback(
    [
        Output('order-action-feedback', 'children'),
        Output('order-action-feedback', 'is_open')
    ],
    [
        Input('cancel-all-orders-btn', 'n_clicks'),
        Input('cancel-symbol-orders-btn', 'n_clicks'),
        Input({'type': 'cancel-order-btn', 'order_id': ALL}, 'n_clicks')
    ],
    [
        State('orders-symbol-filter', 'value'),
        State('live-orders-store', 'data')
    ],
    prevent_initial_call=True
)
def handle_order_management(cancel_all_clicks: int, cancel_symbol_clicks: int,
                           cancel_individual: List[int], symbol_filter: str,
                           orders_data: Dict[str, Any]) -> Tuple[dbc.Alert, bool]:
    """
    Maneja las acciones de gestión de órdenes
    """
    try:
        if not ctx.triggered:
            return dbc.Alert(), False
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if 'cancel-all-orders-btn' in triggered_id:
            # Cancelar todas las órdenes
            result = _cancel_all_orders()
            message = f"Canceladas {result['count']} órdenes"
            color = "success" if result['success'] else "danger"
            
        elif 'cancel-symbol-orders-btn' in triggered_id:
            # Cancelar órdenes de un símbolo específico
            result = _cancel_symbol_orders(symbol_filter)
            message = f"Canceladas {result['count']} órdenes de {symbol_filter}"
            color = "success" if result['success'] else "danger"
            
        elif 'cancel-order-btn' in triggered_id:
            # Cancelar orden individual
            order_data = eval(triggered_id)
            order_id = order_data['order_id']
            result = _cancel_individual_order(order_id)
            message = f"Orden {order_id} {'cancelada' if result['success'] else 'error al cancelar'}"
            color = "success" if result['success'] else "danger"
            
        else:
            return dbc.Alert(), False
        
        alert = dbc.Alert([
            html.I(className=f"fas fa-{'check' if color == 'success' else 'exclamation-triangle'} me-2"),
            message
        ], color=color, dismissable=True, duration=4000)
        
        return alert, True
        
    except Exception as e:
        logger.error(f"❌ Error en gestión de órdenes: {e}")
        
        error_alert = dbc.Alert(
            f"Error: {str(e)}",
            color="danger",
            dismissable=True
        )
        
        return error_alert, True

# ============================================================================
# CALLBACK: CONFIGURACIÓN DE TRADING EN VIVO
# ============================================================================

@callback(
    [
        Output('live-trading-config-store', 'data'),
        Output('config-update-feedback', 'children')
    ],
    [
        Input('max-positions-slider', 'value'),
        Input('position-size-slider', 'value'),
        Input('stop-loss-slider', 'value'),
        Input('take-profit-slider', 'value'),
        Input('confidence-threshold-slider', 'value'),
        Input('auto-trading-toggle', 'value'),
        Input('risk-management-toggle', 'value')
    ],
    prevent_initial_call=True
)
def update_live_trading_config(max_positions: int, position_size: float,
                              stop_loss: float, take_profit: float,
                              confidence_threshold: float, auto_trading: List[str],
                              risk_management: List[str]) -> Tuple[Dict[str, Any], str]:
    """
    Actualiza configuración de trading en vivo
    """
    try:
        config = {
            'max_positions': max_positions,
            'position_size_percent': position_size,
            'stop_loss_percent': stop_loss,
            'take_profit_percent': take_profit,
            'confidence_threshold': confidence_threshold,
            'auto_trading_enabled': 'auto' in (auto_trading or []),
            'risk_management_enabled': 'risk' in (risk_management or []),
            'updated_at': datetime.now().isoformat()
        }
        
        # Validar configuración
        validation_result = _validate_trading_config(config)
        
        if validation_result['valid']:
            feedback = f"✅ Configuración actualizada correctamente"
            logger.info(f"⚙️ Trading config actualizada: {config}")
        else:
            feedback = f"⚠️ Advertencia: {validation_result['message']}"
        
        return config, feedback
        
    except Exception as e:
        logger.error(f"❌ Error actualizando configuración: {e}")
        return {}, f"❌ Error: {str(e)}"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_live_trading_data(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Obtiene datos generales de trading en vivo
    """
    try:
        # En implementación real, esto vendría del sistema de trading
        import random
        
        return {
            'bot_status': random.choice(['running', 'paused', 'stopped']),
            'total_balance': random.uniform(18000, 22000),
            'daily_pnl': random.uniform(-200, 400),
            'daily_volume': random.uniform(5000, 25000),
            'active_positions_count': random.randint(0, 8),
            'pending_orders_count': random.randint(0, 12),
            'last_trade_time': datetime.now() - timedelta(minutes=random.randint(1, 30)),
            'win_rate_today': random.uniform(55, 75),
            'trades_today': random.randint(5, 25),
            'avg_trade_duration': random.uniform(30, 180),
            'current_drawdown': random.uniform(0, 8),
            'model_accuracy': random.uniform(0.65, 0.85),
            'system_health': random.uniform(0.8, 1.0),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos live: {e}")
        return {'error': str(e)}

def _get_active_positions() -> Dict[str, Any]:
    """
    Obtiene posiciones activas del sistema
    """
    try:
        # Generar posiciones de ejemplo
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        positions = []
        
        for i in range(random.randint(2, 6)):
            symbol = random.choice(symbols)
            side = random.choice(['LONG', 'SHORT'])
            entry_price = random.uniform(100, 50000)
            current_price = entry_price * random.uniform(0.98, 1.02)
            size = random.uniform(0.1, 2.0)
            
            unrealized_pnl = (current_price - entry_price) * size if side == 'LONG' else (entry_price - current_price) * size
            
            position = {
                'position_id': f"POS{i+1:04d}",
                'symbol': symbol,
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl,
                'entry_time': datetime.now() - timedelta(minutes=random.randint(10, 300)),
                'stop_loss': entry_price * (0.95 if side == 'LONG' else 1.05),
                'take_profit': entry_price * (1.05 if side == 'LONG' else 0.95),
                'margin_used': entry_price * size * 0.1,  # 10x leverage
                'roi_percent': (unrealized_pnl / (entry_price * size)) * 100
            }
            
            positions.append(position)
        
        return {'positions': positions, 'count': len(positions)}
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones: {e}")
        return {'error': str(e)}

def _get_pending_orders() -> Dict[str, Any]:
    """
    Obtiene órdenes pendientes del sistema
    """
    try:
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        order_types = ['LIMIT', 'STOP_LOSS', 'TAKE_PROFIT', 'STOP_LIMIT']
        orders = []
        
        for i in range(random.randint(3, 10)):
            symbol = random.choice(symbols)
            side = random.choice(['BUY', 'SELL'])
            order_type = random.choice(order_types)
            
            order = {
                'order_id': f"ORD{i+1:06d}",
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'size': random.uniform(0.1, 5.0),
                'price': random.uniform(100, 50000),
                'status': random.choice(['NEW', 'PARTIALLY_FILLED', 'PENDING']),
                'created_time': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                'filled_size': random.uniform(0, 0.5) if random.random() > 0.7 else 0,
                'remaining_size': None,  # Se calculará
                'time_in_force': random.choice(['GTC', 'IOC', 'FOK']),
                'reduce_only': random.choice([True, False])
            }
            
            # Calcular tamaño restante
            order['remaining_size'] = order['size'] - order['filled_size']
            
            orders.append(order)
        
        return {'orders': orders, 'count': len(orders)}
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo órdenes: {e}")
        return {'error': str(e)}

def _get_model_signals() -> Dict[str, Any]:
    """
    Obtiene señales del modelo de IA
    """
    try:
        import random
        
        signals = []
        signal_types = ['BUY', 'SELL', 'HOLD']
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        for i in range(random.randint(5, 15)):
            signal = {
                'signal_id': f"SIG{i+1:05d}",
                'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                'symbol': random.choice(symbols),
                'signal': random.choice(signal_types),
                'confidence': random.uniform(0.6, 0.95),
                'price': random.uniform(100, 50000),
                'reasoning': random.choice([
                    'Breakout alcista detectado',
                    'RSI en sobreventa',
                    'Confluencia de medias móviles',
                    'Patrón de reversión',
                    'Volumen anómalo',
                    'Soporte/resistencia clave'
                ]),
                'executed': random.choice([True, False]),
                'execution_price': None,
                'pnl': None
            }
            
            # Si fue ejecutada, agregar datos de ejecución
            if signal['executed']:
                signal['execution_price'] = signal['price'] * random.uniform(0.999, 1.001)
                signal['pnl'] = random.uniform(-50, 150)
            
            signals.append(signal)
        
        # Ordenar por timestamp descendente
        signals.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            'signals': signals,
            'count': len(signals),
            'avg_confidence': np.mean([s['confidence'] for s in signals]),
            'signal_distribution': {
                'BUY': len([s for s in signals if s['signal'] == 'BUY']),
                'SELL': len([s for s in signals if s['signal'] == 'SELL']),
                'HOLD': len([s for s in signals if s['signal'] == 'HOLD'])
            },
            'execution_rate': len([s for s in signals if s['executed']]) / len(signals) if signals else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo señales: {e}")
        return {'error': str(e)}

def _get_positions_table_columns() -> List[Dict[str, Any]]:
    """
    Define las columnas de la tabla de posiciones
    """
    return [
        {"name": "ID", "id": "position_id", "type": "text"},
        {"name": "Símbolo", "id": "symbol", "type": "text"},
        {"name": "Lado", "id": "side", "type": "text", "presentation": "markdown"},
        {"name": "Tamaño", "id": "size", "type": "numeric", "format": {"specifier": ".4f"}},
        {"name": "Precio Entrada", "id": "entry_price", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Precio Actual", "id": "current_price", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "PnL No Realizado", "id": "unrealized_pnl", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "ROI (%)", "id": "roi_percent", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Duración", "id": "duration", "type": "text"},
        {"name": "Acciones", "id": "actions", "type": "text", "presentation": "markdown"}
    ]

def _format_positions_for_table(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formatea las posiciones para mostrar en la tabla
    """
    formatted_positions = []
    
    for pos in positions:
        # Calcular duración
        entry_time = pos.get('entry_time', datetime.now())
        duration = datetime.now() - entry_time
        duration_str = f"{duration.total_seconds() / 3600:.1f}h"
        
        # Formatear lado con colores
        side = pos.get('side', 'UNKNOWN')
        side_formatted = f"🟢 **{side}**" if side == 'LONG' else f"🔴 **{side}**"
        
        # Crear botones de acción
        position_id = pos.get('position_id', '')
        actions = f"🔒 [Cerrar](#{position_id}) | ⚙️ [Editar](#{position_id})"
        
        formatted_pos = {
            'position_id': position_id,
            'symbol': pos.get('symbol', ''),
            'side': side_formatted,
            'size': pos.get('size', 0),
            'entry_price': pos.get('entry_price', 0),
            'current_price': pos.get('current_price', 0),
            'unrealized_pnl': pos.get('unrealized_pnl', 0),
            'roi_percent': pos.get('roi_percent', 0),
            'duration': duration_str,
            'actions': actions
        }
        
        formatted_positions.append(formatted_pos)
    
    return formatted_positions

def _get_orders_table_columns() -> List[Dict[str, Any]]:
    """
    Define las columnas de la tabla de órdenes
    """
    return [
        {"name": "ID", "id": "order_id", "type": "text"},
        {"name": "Símbolo", "id": "symbol", "type": "text"},
        {"name": "Lado", "id": "side", "type": "text", "presentation": "markdown"},
        {"name": "Tipo", "id": "type", "type": "text"},
        {"name": "Tamaño", "id": "size", "type": "numeric", "format": {"specifier": ".4f"}},
        {"name": "Precio", "id": "price", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Estado", "id": "status", "type": "text", "presentation": "markdown"},
        {"name": "Ejecutado", "id": "filled_percent", "type": "text"},
        {"name": "Tiempo", "id": "created_time", "type": "text"},
        {"name": "Acciones", "id": "actions", "type": "text", "presentation": "markdown"}
    ]

def _format_orders_for_table(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formatea las órdenes para mostrar en la tabla
    """
    formatted_orders = []
    
    for order in orders:
        # Formatear lado con colores
        side = order.get('side', 'UNKNOWN')
        side_formatted = f"🟢 **{side}**" if side == 'BUY' else f"🔴 **{side}**"
        
        # Formatear estado
        status = order.get('status', 'UNKNOWN')
        status_colors = {
            'NEW': '🔵 **NUEVA**',
            'PARTIALLY_FILLED': '🟡 **PARCIAL**',
            'PENDING': '⏳ **PENDIENTE**',
            'FILLED': '✅ **EJECUTADA**',
            'CANCELLED': '❌ **CANCELADA**'
        }
        status_formatted = status_colors.get(status, f"❓ **{status}**")
        
        # Calcular porcentaje ejecutado
        filled_size = order.get('filled_size', 0)
        total_size = order.get('size', 1)
        filled_percent = f"{(filled_size / total_size * 100):.1f}%" if total_size > 0 else "0%"
        
        # Formatear tiempo
        created_time = order.get('created_time', datetime.now())
        time_ago = datetime.now() - created_time
        if time_ago.total_seconds() < 60:
            time_str = f"{int(time_ago.total_seconds())}s"
        elif time_ago.total_seconds() < 3600:
            time_str = f"{int(time_ago.total_seconds() / 60)}m"
        else:
            time_str = f"{int(time_ago.total_seconds() / 3600)}h"
        
        # Crear botones de acción
        order_id = order.get('order_id', '')
        actions = f"❌ [Cancelar](#{order_id}) | ✏️ [Modificar](#{order_id})"
        
        formatted_order = {
            'order_id': order_id,
            'symbol': order.get('symbol', ''),
            'side': side_formatted,
            'type': order.get('type', ''),
            'size': order.get('size', 0),
            'price': order.get('price', 0),
            'status': status_formatted,
            'filled_percent': filled_percent,
            'created_time': time_str,
            'actions': actions
        }
        
        formatted_orders.append(formatted_order)
    
    return formatted_orders

def _filter_orders(orders: List[Dict[str, Any]], order_filter: str, 
                  symbol_filter: str) -> List[Dict[str, Any]]:
    """
    Filtra órdenes según criterios especificados
    """
    filtered = orders
    
    # Filtrar por tipo
    if order_filter and order_filter != 'all':
        if order_filter == 'buy':
            filtered = [o for o in filtered if o.get('side') == 'BUY']
        elif order_filter == 'sell':
            filtered = [o for o in filtered if o.get('side') == 'SELL']
        elif order_filter == 'limit':
            filtered = [o for o in filtered if o.get('type') == 'LIMIT']
        elif order_filter == 'stop':
            filtered = [o for o in filtered if 'STOP' in o.get('type', '')]
    
    # Filtrar por símbolo
    if symbol_filter and symbol_filter != 'all':
        filtered = [o for o in filtered if o.get('symbol') == symbol_filter]
    
    return filtered

def _filter_signals(signals: List[Dict[str, Any]], signal_filter: str) -> List[Dict[str, Any]]:
    """
    Filtra señales según criterio especificado
    """
    if not signal_filter or signal_filter == 'all':
        return signals
    
    if signal_filter == 'buy':
        return [s for s in signals if s.get('signal') == 'BUY']
    elif signal_filter == 'sell':
        return [s for s in signals if s.get('signal') == 'SELL']
    elif signal_filter == 'high_confidence':
        return [s for s in signals if s.get('confidence', 0) > 0.8]
    elif signal_filter == 'executed':
        return [s for s in signals if s.get('executed', False)]
    
    return signals

def _create_signals_feed(signals: List[Dict[str, Any]], theme: str) -> html.Div:
    """
    Crea el feed de señales del modelo
    """
    if not signals:
        return html.P("No hay señales recientes", className="text-muted text-center py-3")
    
    signal_items = []
    
    for signal in signals[:10]:  # Mostrar últimas 10 señales
        # Determinar color de la señal
        signal_type = signal.get('signal', 'HOLD')
        signal_colors = {
            'BUY': 'success',
            'SELL': 'danger',
            'HOLD': 'warning'
        }
        signal_color = signal_colors.get(signal_type, 'secondary')
        
        # Determinar icono
        signal_icons = {
            'BUY': 'fas fa-arrow-up',
            'SELL': 'fas fa-arrow-down',
            'HOLD': 'fas fa-pause'
        }
        signal_icon = signal_icons.get(signal_type, 'fas fa-question')
        
        # Formatear timestamp
        timestamp = signal.get('timestamp', datetime.now())
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Crear item de señal
        signal_item = dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Badge([
                            html.I(className=f"{signal_icon} me-1"),
                            signal_type
                        ], color=signal_color, className="me-2"),
                        html.Strong(signal.get('symbol', 'N/A')),
                        html.Small(f" - {time_str}", className="text-muted ms-2")
                    ])
                ], width=8),
                dbc.Col([
                    html.Div([
                        html.Small("Confianza: ", className="text-muted"),
                        html.Strong(f"{signal.get('confidence', 0):.1%}")
                    ], className="text-end")
                ], width=4)
            ]),
            html.Hr(className="my-2"),
            html.Small([
                html.I(className="fas fa-lightbulb me-1 text-warning"),
                signal.get('reasoning', 'Sin razón especificada')
            ], className="text-muted"),
            html.Div([
                html.Small(f"Precio: ${signal.get('price', 0):,.2f}", className="text-muted me-3"),
                dbc.Badge(
                    "✅ Ejecutada" if signal.get('executed', False) else "⏳ Pendiente",
                    color="success" if signal.get('executed', False) else "secondary",
                    className="mt-1"
                )
            ], className="mt-2")
        ], className="mb-2")
        
        signal_items.append(signal_item)
    
    return dbc.ListGroup(signal_items, flush=True, className="signals-feed")

def _create_signals_stats_cards(signals: List[Dict[str, Any]]) -> dbc.Row:
    """
    Crea tarjetas de estadísticas de señales
    """
    if not signals:
        return dbc.Row()
    
    # Calcular estadísticas
    total_signals = len(signals)
    executed_signals = len([s for s in signals if s.get('executed', False)])
    avg_confidence = np.mean([s.get('confidence', 0) for s in signals])
    
    # Distribución de señales
    buy_signals = len([s for s in signals if s.get('signal') == 'BUY'])
    sell_signals = len([s for s in signals if s.get('signal') == 'SELL'])
    hold_signals = len([s for s in signals if s.get('signal') == 'HOLD'])
    
    cards = [
        {
            'title': 'Total Señales',
            'value': str(total_signals),
            'icon': 'fas fa-signal',
            'color': 'primary'
        },
        {
            'title': 'Ejecutadas',
            'value': f"{executed_signals}/{total_signals}",
            'icon': 'fas fa-check-circle',
            'color': 'success'
        },
        {
            'title': 'Confianza Promedio',
            'value': f"{avg_confidence:.1%}",
            'icon': 'fas fa-brain',
            'color': 'info'
        },
        {
            'title': 'BUY/SELL/HOLD',
            'value': f"{buy_signals}/{sell_signals}/{hold_signals}",
            'icon': 'fas fa-chart-pie',
            'color': 'warning'
        }
    ]
    
    card_components = []
    for card in cards:
        card_components.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6(card['title'], className="card-subtitle mb-1 text-muted"),
                                html.H5(card['value'], className=f"card-title mb-0 text-{card['color']}")
                            ], width=8),
                            dbc.Col([
                                html.I(className=f"{card['icon']} fa-lg text-{card['color']} opacity-75")
                            ], width=4, className="text-end")
                        ])
                    ])
                ], className="h-100")
            ], width=3, className="mb-2")
        )
    
    return dbc.Row(card_components)

def _create_model_confidence_gauge(signals_data: Dict[str, Any], theme: str) -> go.Figure:
    """
    Crea gauge de confianza del modelo
    """
    try:
        avg_confidence = signals_data.get('avg_confidence', 0.7)
        confidence_percent = avg_confidence * 100
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=confidence_percent,
            delta={'reference': 70, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            },
            title={'text': "Confianza del Modelo (%)"}
        ))
        
        fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        fig = apply_theme(fig, theme)
        
        return fig
        
    except Exception as e:
        logger.error(f"❌ Error creando gauge de confianza: {e}")
        return _create_empty_gauge(theme)

def _create_empty_gauge(theme: str) -> go.Figure:
    """
    Crea un gauge vacío para estados de error
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=0,
        gauge={'axis': {'range': [None, 100]}},
        title={'text': "Sin datos"}
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return apply_theme(fig, theme)

def _get_bot_status() -> Dict[str, Any]:
    """
    Obtiene el estado actual del bot
    """
    try:
        # En implementación real, esto consultaría el estado del bot
        import random
        
        statuses = ['running', 'paused', 'stopped', 'starting', 'error']
        current_status = random.choice(statuses)
        
        return {
            'status': current_status,
            'uptime': random.randint(3600, 86400),  # 1 hora a 1 día
            'last_restart': datetime.now() - timedelta(hours=random.randint(1, 24)),
            'memory_usage': random.uniform(45, 85),  # Porcentaje
            'cpu_usage': random.uniform(10, 60),     # Porcentaje
            'api_latency': random.uniform(50, 200),  # ms
            'errors_count': random.randint(0, 5),
            'warnings_count': random.randint(0, 10),
            'version': '10.0.0',
            'environment': 'production',
            'auto_restart': True,
            'max_memory': 2048,  # MB
            'threads_active': random.randint(5, 15)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado del bot: {e}")
        return {'status': 'error', 'error': str(e)}

def _execute_bot_action(action: str, current_status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta una acción de control del bot
    """
    try:
        if action == 'start-bot-btn':
            new_status = current_status.copy()
            new_status['status'] = 'running'
            new_status['last_restart'] = datetime.now()
            
            feedback = dbc.Alert([
                html.I(className="fas fa-play me-2"),
                "Bot iniciado correctamente"
            ], color="success", dismissable=True, duration=4000)
            
        elif action == 'pause-bot-btn':
            new_status = current_status.copy()
            new_status['status'] = 'paused'
            
            feedback = dbc.Alert([
                html.I(className="fas fa-pause me-2"),
                "Bot pausado - posiciones activas mantenidas"
            ], color="warning", dismissable=True, duration=4000)
            
        elif action == 'stop-bot-btn':
            new_status = current_status.copy()
            new_status['status'] = 'stopped'
            
            feedback = dbc.Alert([
                html.I(className="fas fa-stop me-2"),
                "Bot detenido - cerrando posiciones activas"
            ], color="info", dismissable=True, duration=4000)
            
        elif action == 'emergency-stop-btn':
            new_status = current_status.copy()
            new_status['status'] = 'stopped'
            
            feedback = dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                "🚨 PARADA DE EMERGENCIA ACTIVADA - Todas las operaciones canceladas"
            ], color="danger", dismissable=True, duration=6000)
            
        else:
            raise ValueError(f"Acción no reconocida: {action}")
        
        return {
            'new_status': new_status,
            'feedback': feedback,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando acción {action}: {e}")
        
        error_feedback = dbc.Alert(
            f"Error ejecutando acción: {str(e)}",
            color="danger",
            dismissable=True
        )
        
        return {
            'new_status': current_status,
            'feedback': error_feedback,
            'success': False
        }

def _get_status_indicator(status_data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Obtiene indicador visual del estado del bot
    """
    status = status_data.get('status', 'unknown')
    
    status_configs = {
        'running': ('🟢 ACTIVO', 'success'),
        'paused': ('🟡 PAUSADO', 'warning'),
        'stopped': ('🔴 DETENIDO', 'danger'),
        'starting': ('🔵 INICIANDO', 'info'),
        'error': ('❌ ERROR', 'danger')
    }
    
    return status_configs.get(status, ('❓ DESCONOCIDO', 'secondary'))

def _get_buttons_state(status_data: Dict[str, Any]) -> Dict[str, bool]:
    """
    Determina qué botones deben estar habilitados/deshabilitados
    """
    status = status_data.get('status', 'unknown')
    
    if status == 'running':
        return {
            'start': True,      # Deshabilitado
            'pause': False,     # Habilitado
            'stop': False,      # Habilitado
            'emergency': False  # Habilitado
        }
    elif status == 'paused':
        return {
            'start': False,     # Habilitado
            'pause': True,      # Deshabilitado
            'stop': False,      # Habilitado
            'emergency': False  # Habilitado
        }
    elif status == 'stopped':
        return {
            'start': False,     # Habilitado
            'pause': True,      # Deshabilitado
            'stop': True,       # Deshabilitado
            'emergency': True   # Deshabilitado
        }
    else:  # starting, error, unknown
        return {
            'start': True,      # Deshabilitado
            'pause': True,      # Deshabilitado
            'stop': True,       # Deshabilitado
            'emergency': False  # Habilitado
        }

def _get_live_metrics_detailed(trading_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene métricas detalladas para los gauges y contadores
    """
    return {
        'daily_pnl': trading_data.get('daily_pnl', 0),
        'win_rate': trading_data.get('win_rate_today', 0),
        'total_trades_today': trading_data.get('trades_today', 0),
        'daily_volume': trading_data.get('daily_volume', 0),
        'total_balance': trading_data.get('total_balance', 0),
        'current_drawdown': trading_data.get('current_drawdown', 0),
        'avg_trade_duration': trading_data.get('avg_trade_duration', 0),
        'model_accuracy': trading_data.get('model_accuracy', 0.7),
        'system_health': trading_data.get('system_health', 0.9)
    }

def _create_pnl_gauge(daily_pnl: float, theme: str) -> go.Figure:
    """
    Crea gauge de PnL diario
    """
    try:
        # Normalizar PnL para el gauge (-500 a +500)
        max_pnl = 500
        normalized_pnl = max(-max_pnl, min(max_pnl, daily_pnl))
        gauge_value = 50 + (normalized_pnl / max_pnl) * 50  # 0-100 scale
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=daily_pnl,
            delta={'reference': 0, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
            gauge={
                'axis': {'range': [-max_pnl, max_pnl]},
                'bar': {'color': "green" if daily_pnl >= 0 else "red"},
                'steps': [
                    {'range': [-max_pnl, -100], 'color': "lightcoral"},
                    {'range': [-100, 100], 'color': "lightgray"},
                    {'range': [100, max_pnl], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 2},
                    'thickness': 0.75,
                    'value': 0
                }
            },
            title={'text': "PnL Diario ($)"},
            number={'prefix': "$"}
        ))
        
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return apply_theme(fig, theme)
        
    except Exception as e:
        logger.error(f"❌ Error creando gauge PnL: {e}")
        return _create_empty_gauge(theme)

def _create_win_rate_gauge(win_rate: float, theme: str) -> go.Figure:
    """
    Crea gauge de win rate
    """
    try:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=win_rate,
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "green" if win_rate >= 50 else "orange" if win_rate >= 40 else "red"},
                'steps': [
                    {'range': [0, 40], 'color': "lightcoral"},
                    {'range': [40, 60], 'color': "lightyellow"},
                    {'range': [60, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            },
            title={'text': "Win Rate (%)"},
            number={'suffix': "%"}
        ))
        
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return apply_theme(fig, theme)
        
    except Exception as e:
        logger.error(f"❌ Error creando gauge win rate: {e}")
        return _create_empty_gauge(theme)

def _get_recent_activities(trading_data: Dict[str, Any], activity_filter: str) -> List[Dict[str, Any]]:
    """
    Obtiene actividades recientes del sistema
    """
    try:
        import random
        
        activities = []
        activity_types = ['trade', 'order', 'signal', 'alert', 'system']
        
        for i in range(random.randint(10, 25)):
            activity_type = random.choice(activity_types)
            
            # Generar actividad según tipo
            if activity_type == 'trade':
                activity = {
                    'type': 'trade',
                    'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 120)),
                    'title': f"Trade ejecutado: {random.choice(['BTCUSDT', 'ETHUSDT', 'ADAUSDT'])}",
                    'description': f"{random.choice(['Compra', 'Venta'])} de {random.uniform(0.1, 2.0):.3f} a ${random.uniform(100, 50000):,.2f}",
                    'severity': 'info',
                    'icon': 'fas fa-exchange-alt'
                }
            
            elif activity_type == 'order':
                activity = {
                    'type': 'order',
                    'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                    'title': f"Orden {random.choice(['creada', 'cancelada', 'ejecutada'])}",
                    'description': f"Orden {random.choice(['LIMIT', 'STOP'])} para {random.choice(['BTCUSDT', 'ETHUSDT'])}",
                    'severity': 'success',
                    'icon': 'fas fa-list-alt'
                }
            
            elif activity_type == 'signal':
                activity = {
                    'type': 'signal',
                    'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 30)),
                    'title': f"Señal {random.choice(['BUY', 'SELL', 'HOLD'])} generada",
                    'description': f"Confianza: {random.uniform(0.6, 0.95):.1%} - {random.choice(['BTCUSDT', 'ETHUSDT'])}",
                    'severity': 'primary',
                    'icon': 'fas fa-lightbulb'
                }
            
            elif activity_type == 'alert':
                activity = {
                    'type': 'alert',
                    'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 180)),
                    'title': f"Alerta: {random.choice(['Drawdown alto', 'Latencia API', 'Memoria alta'])}",
                    'description': random.choice(['Revisar configuración', 'Monitorear sistema', 'Optimizar recursos']),
                    'severity': 'warning',
                    'icon': 'fas fa-exclamation-triangle'
                }
            
            else:  # system
                activity = {
                    'type': 'system',
                    'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 300)),
                    'title': f"Sistema: {random.choice(['Reinicio', 'Actualización', 'Backup', 'Mantenimiento'])}",
                    'description': random.choice(['Completado exitosamente', 'En progreso', 'Programado']),
                    'severity': 'secondary',
                    'icon': 'fas fa-cog'
                }
            
            activities.append(activity)
        
        # Ordenar por timestamp descendente
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Aplicar filtro si es necesario
        if activity_filter and activity_filter != 'all':
            activities = [a for a in activities if a['type'] == activity_filter]
        
        return activities
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo actividades: {e}")
        return []

def _create_activity_feed(activities: List[Dict[str, Any]]) -> html.Div:
    """
    Crea el feed de actividad del sistema
    """
    if not activities:
        return html.P("No hay actividad reciente", className="text-muted text-center py-3")
    
    activity_items = []
    
    for activity in activities[:20]:  # Mostrar últimas 20 actividades
        # Determinar color según severidad
        severity_colors = {
            'info': 'info',
            'success': 'success',
            'warning': 'warning',
            'danger': 'danger',
            'primary': 'primary',
            'secondary': 'secondary'
        }
        color = severity_colors.get(activity.get('severity', 'info'), 'info')
        
        # Formatear timestamp
        timestamp = activity.get('timestamp', datetime.now())
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Crear item de actividad
        activity_item = dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{activity.get('icon', 'fas fa-info')} me-2 text-{color}"),
                        html.Strong(activity.get('title', 'Sin título')),
                        html.Small(f" - {time_str}", className="text-muted ms-2")
                    ])
                ], width=12)
            ]),
            html.P(activity.get('description', ''), className="mb-0 mt-1 text-muted small")
        ], className="py-2")
        
        activity_items.append(activity_item)
    
    return dbc.ListGroup(activity_items, flush=True, className="activity-feed")

def _cancel_all_orders() -> Dict[str, Any]:
    """
    Cancela todas las órdenes pendientes
    """
    try:
        # En implementación real, esto cancelaría órdenes reales
        import random
        
        cancelled_count = random.randint(3, 10)
        
        return {
            'success': True,
            'count': cancelled_count,
            'message': f'Se cancelaron {cancelled_count} órdenes'
        }
        
    except Exception as e:
        logger.error(f"❌ Error cancelando todas las órdenes: {e}")
        return {
            'success': False,
            'count': 0,
            'message': f'Error: {str(e)}'
        }

def _cancel_symbol_orders(symbol: str) -> Dict[str, Any]:
    """
    Cancela órdenes de un símbolo específico
    """
    try:
        # En implementación real, esto cancelaría órdenes del símbolo
        import random
        
        cancelled_count = random.randint(1, 5)
        
        return {
            'success': True,
            'count': cancelled_count,
            'message': f'Se cancelaron {cancelled_count} órdenes de {symbol}'
        }
        
    except Exception as e:
        logger.error(f"❌ Error cancelando órdenes de {symbol}: {e}")
        return {
            'success': False,
            'count': 0,
            'message': f'Error: {str(e)}'
        }

def _cancel_individual_order(order_id: str) -> Dict[str, Any]:
    """
    Cancela una orden individual
    """
    try:
        # En implementación real, esto cancelaría la orden específica
        return {
            'success': True,
            'order_id': order_id,
            'message': f'Orden {order_id} cancelada'
        }
        
    except Exception as e:
        logger.error(f"❌ Error cancelando orden {order_id}: {e}")
        return {
            'success': False,
            'order_id': order_id,
            'message': f'Error: {str(e)}'
        }

def _validate_trading_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida la configuración de trading
    """
    try:
        warnings = []
        
        # Validar máximo de posiciones
        max_positions = config.get('max_positions', 0)
        if max_positions > 10:
            warnings.append("Máximo de posiciones muy alto (>10)")
        elif max_positions < 1:
            warnings.append("Máximo de posiciones debe ser al menos 1")
        
        # Validar tamaño de posición
        position_size = config.get('position_size_percent', 0)
        if position_size > 10:
            warnings.append("Tamaño de posición muy alto (>10%)")
        elif position_size < 0.1:
            warnings.append("Tamaño de posición muy bajo (<0.1%)")
        
        # Validar stop loss
        stop_loss = config.get('stop_loss_percent', 0)
        if stop_loss > 20:
            warnings.append("Stop loss muy amplio (>20%)")
        elif stop_loss < 1:
            warnings.append("Stop loss muy estrecho (<1%)")
        
        # Validar take profit
        take_profit = config.get('take_profit_percent', 0)
        if take_profit < stop_loss:
            warnings.append("Take profit menor que stop loss")
        
        # Validar umbral de confianza
        confidence = config.get('confidence_threshold', 0)
        if confidence > 0.95:
            warnings.append("Umbral de confianza muy alto (>95%)")
        elif confidence < 0.6:
            warnings.append("Umbral de confianza muy bajo (<60%)")
        
        if warnings:
            return {
                'valid': False,
                'message': '; '.join(warnings[:2])  # Mostrar solo primeras 2 advertencias
            }
        else:
            return {
                'valid': True,
                'message': 'Configuración válida'
            }
            
    except Exception as e:
        logger.error(f"❌ Error validando configuración: {e}")
        return {
            'valid': False,
            'message': f'Error de validación: {str(e)}'
        }

# ============================================================================
# CALLBACK: ALERTAS DE RIESGO EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('risk-alerts-container', 'children'),
        Output('risk-level-indicator', 'children'),
        Output('risk-level-indicator', 'color')
    ],
    [
        Input('live-trading-data-store', 'data'),
        Input('live-positions-store', 'data'),
        Input('risk-check-interval', 'n_intervals')
    ],
    prevent_initial_call=False
)
def update_risk_alerts(trading_data: Dict[str, Any], positions_data: Dict[str, Any],
                      n_intervals: int) -> Tuple[html.Div, str, str]:
    """
    Actualiza alertas de riesgo en tiempo real
    """
    try:
        # Analizar riesgos actuales
        risk_analysis = _analyze_current_risks(trading_data, positions_data)
        
        # Crear alertas de riesgo
        risk_alerts = _create_risk_alerts(risk_analysis)
        
        # Determinar nivel de riesgo general
        risk_level = risk_analysis.get('overall_risk_level', 'low')
        risk_colors = {
            'low': ('🟢 BAJO', 'success'),
            'medium': ('🟡 MEDIO', 'warning'),
            'high': ('🔴 ALTO', 'danger'),
            'critical': ('🚨 CRÍTICO', 'danger')
        }
        
        risk_text, risk_color = risk_colors.get(risk_level, ('❓ DESCONOCIDO', 'secondary'))
        
        return risk_alerts, risk_text, risk_color
        
    except Exception as e:
        logger.error(f"❌ Error actualizando alertas de riesgo: {e}")
        
        error_alert = dbc.Alert("Error analizando riesgos", color="warning", className="mb-0")
        return error_alert, "❌ ERROR", "danger"

def _analyze_current_risks(trading_data: Dict[str, Any], 
                          positions_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza los riesgos actuales del sistema
    """
    try:
        risks = []
        risk_scores = []
        
        # Analizar drawdown
        current_drawdown = trading_data.get('current_drawdown', 0)
        if current_drawdown > 15:
            risks.append({
                'type': 'critical',
                'title': 'Drawdown Crítico',
                'message': f'Drawdown actual: {current_drawdown:.1f}%',
                'action': 'Considerar parada de emergencia'
            })
            risk_scores.append(0.9)
        elif current_drawdown > 10:
            risks.append({
                'type': 'high',
                'title': 'Drawdown Alto',
                'message': f'Drawdown actual: {current_drawdown:.1f}%',
                'action': 'Monitorear posiciones activas'
            })
            risk_scores.append(0.7)
        
        # Analizar exposición total
        positions = positions_data.get('positions', [])
        total_exposure = sum(abs(pos.get('unrealized_pnl', 0)) for pos in positions)
        
        if total_exposure > 5000:
            risks.append({
                'type': 'high',
                'title': 'Exposición Alta',
                'message': f'Exposición total: ${total_exposure:,.2f}',
                'action': 'Reducir tamaño de posiciones'
            })
            risk_scores.append(0.6)
        
        # Analizar correlación de posiciones
        symbols_in_positions = [pos.get('symbol', '') for pos in positions]
        unique_symbols = set(symbols_in_positions)
        
        if len(positions) > 0 and len(unique_symbols) / len(positions) < 0.7:
            risks.append({
                'type': 'medium',
                'title': 'Alta Correlación',
                'message': 'Múltiples posiciones en símbolos similares',
                'action': 'Diversificar posiciones'
            })
            risk_scores.append(0.4)
        
        # Analizar PnL diario
        daily_pnl = trading_data.get('daily_pnl', 0)
        if daily_pnl < -500:
            risks.append({
                'type': 'high',
                'title': 'Pérdidas Diarias Altas',
                'message': f'PnL diario: ${daily_pnl:,.2f}',
                'action': 'Revisar estrategia'
            })
            risk_scores.append(0.8)
        
        # Determinar nivel de riesgo general
        if not risk_scores:
            overall_risk = 'low'
        else:
            avg_risk_score = np.mean(risk_scores)
            if avg_risk_score >= 0.8:
                overall_risk = 'critical'
            elif avg_risk_score >= 0.6:
                overall_risk = 'high'
            elif avg_risk_score >= 0.3:
                overall_risk = 'medium'
            else:
                overall_risk = 'low'
        
        return {
            'risks': risks,
            'overall_risk_level': overall_risk,
            'risk_score': np.mean(risk_scores) if risk_scores else 0,
            'total_exposure': total_exposure,
            'positions_count': len(positions),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error analizando riesgos: {e}")
        return {'risks': [], 'overall_risk_level': 'low'}

def _create_risk_alerts(risk_analysis: Dict[str, Any]) -> html.Div:
    """
    Crea alertas visuales de riesgo
    """
    risks = risk_analysis.get('risks', [])
    
    if not risks:
        return html.Div([
            html.I(className="fas fa-shield-alt text-success me-2"),
            html.Span("No hay alertas de riesgo activas", className="text-success")
        ], className="text-center py-3")
    
    alert_components = []
    
    for risk in risks:
        risk_type = risk.get('type', 'info')
        alert_colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'success'
        }
        alert_color = alert_colors.get(risk_type, 'info')
        
        alert_component = dbc.Alert([
            html.Strong(risk.get('title', 'Alerta de riesgo')),
            html.P(risk.get('message', ''), className="mb-1 mt-1"),
            html.Small([
                html.I(className="fas fa-lightbulb me-1"),
                f"Acción recomendada: {risk.get('action', 'Revisar sistema')}"
            ], className="text-muted")
        ], color=alert_color, className="mb-2")
        
        alert_components.append(alert_component)
    
    return html.Div(alert_components)

# ============================================================================
# CALLBACK: MINI GRÁFICO DE RENDIMIENTO INTRADAY
# ============================================================================

@callback(
    Output('intraday-performance-chart', 'figure'),
    [
        Input('live-trading-data-store', 'data'),
        Input('intraday-chart-refresh', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_intraday_chart(trading_data: Dict[str, Any], n_intervals: int,
                         theme: str) -> go.Figure:
    """
    Actualiza mini gráfico de rendimiento intraday
    """
    try:
        # Generar datos de rendimiento intraday
        hours = list(range(24))
        current_hour = datetime.now().hour
        
        # Simular PnL acumulado durante el día
        np.random.seed(42 + n_intervals)  # Variación pero consistente
        hourly_returns = np.random.normal(0, 0.02, current_hour + 1)
        cumulative_pnl = np.cumsum(hourly_returns) * 1000  # Escalar a dólares
        
        # Crear timestamps para las horas
        today = datetime.now().replace(minute=0, second=0, microsecond=0)
        timestamps = [today.replace(hour=h) for h in range(current_hour + 1)]
        
        fig = go.Figure()
        
        # Línea de PnL
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=cumulative_pnl,
            mode='lines+markers',
            name='PnL Intraday',
            line=dict(color=TRADING_COLORS['primary'], width=2),
            marker=dict(size=4),
            fill='tonexty',
            fillcolor='rgba(187, 134, 252, 0.1)'
        ))
        
        # Línea de break-even
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="gray",
            opacity=0.5
        )
        
        # Configurar layout
        fig.update_layout(
            title="Rendimiento Intraday",
            xaxis_title="Hora",
            yaxis_title="PnL Acumulado ($)",
            height=200,
            margin=dict(l=40, r=20, t=40, b=40),
            showlegend=False
        )
        
        # Aplicar tema
        fig = apply_theme(fig, theme)
        
        return fig
        
    except Exception as e:
        logger.error(f"❌ Error creando gráfico intraday: {e}")
        
        # Gráfico vacío en caso de error
        fig = go.Figure()
        fig.add_annotation(
            text="Error cargando datos",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False
        )
        fig.update_layout(height=200)
        
        return apply_theme(fig, theme)

# ============================================================================
# FUNCIONES DE UTILIDAD PARA REGISTRAR CALLBACKS
# ============================================================================

def register_all_live_trading_callbacks(app, dp: DataProvider, rtm: RealTimeManager, pt: PerformanceTracker):
    """
    Registra todos los callbacks de live trading en la aplicación Dash
    
    Args:
        app: Aplicación Dash
        dp (DataProvider): Proveedor de datos
        rtm (RealTimeManager): Gestor de tiempo real
        pt (PerformanceTracker): Tracker de rendimiento
    """
    # Inicializar instancias globales
    initialize_live_trading_callbacks(dp, rtm, pt)
    
    # Los callbacks ya están registrados usando el decorador @callback
    logger.info("⚡ Todos los callbacks de Live Trading registrados correctamente")

def get_live_trading_callback_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas de los callbacks de live trading para debugging
    
    Returns:
        Dict[str, Any]: Estadísticas de callbacks
    """
    return {
        'data_provider_connected': data_provider is not None,
        'real_time_manager_connected': real_time_manager is not None,
        'performance_tracker_connected': performance_tracker is not None,
        'callbacks_registered': True,
        'last_check': datetime.now().isoformat()
    }

# ============================================================================
# CONFIGURACIÓN DE LOGGING ESPECÍFICA
# ============================================================================

# Configurar logging específico para callbacks de live trading
logging.getLogger(__name__).setLevel(logging.INFO)

logger.info("⚡ Módulo de callbacks de Live Trading cargado correctamente")

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

import dash
from dash import Input, Output, State, callback, ctx, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Importaciones locales
from monitoring.core.data_provider import DataProvider
from monitoring.core.real_time_manager import RealTimeManager, RealTimeUpdate
from monitoring.core.performance_tracker import PerformanceTracker
from monitoring.config.chart_config import CHART_CONFIG, apply_theme, TRADING_COLORS
from monitoring.config.layout_config import LAYOUT_CONFIG

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN GLOBAL DE CALLBACKS
# ============================================================================

# Instancias globales (serán inyectadas por la aplicación principal)
data_provider: Optional[DataProvider] = None
real_time_manager: Optional[RealTimeManager] = None
performance_tracker: Optional[PerformanceTracker] = None

def initialize_live_trading_callbacks(dp: DataProvider, rtm: RealTimeManager, pt: PerformanceTracker):
    """
    Inicializa las instancias globales para los callbacks de live trading
    
    Args:
        dp (DataProvider): Proveedor de datos
        rtm (RealTimeManager): Gestor de tiempo real
        pt (PerformanceTracker): Tracker de rendimiento
    """
    global data_provider, real_time_manager, performance_tracker
    data_provider = dp
    real_time_manager = rtm
    performance_tracker = pt
    logger.info("⚡ Callbacks de Live Trading inicializados")

# ============================================================================
# CALLBACK PRINCIPAL: ACTUALIZACIÓN DE DATOS EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('live-trading-data-store', 'data'),
        Output('live-positions-store', 'data'),
        Output('live-orders-store', 'data'),
        Output('live-signals-store', 'data'),
        Output('live-last-update', 'children')
    ],
    [
        Input('live-fast-update', 'n_intervals'),
        Input('live-refresh-btn', 'n_clicks'),
        Input('live-emergency-refresh', 'n_clicks')
    ],
    [
        State('bot-status-store', 'data')
    ],
    prevent_initial_call=False
)
def update_live_trading_data(fast_intervals: int, refresh_clicks: int,
                           emergency_clicks: int, bot_status: Dict[str, Any]) -> Tuple:
    """
    Callback principal para actualizar todos los datos de trading en vivo
    """
    try:
        # Determinar tipo de actualización
        triggered_id = ctx.triggered_id if ctx.triggered else None
        is_emergency = triggered_id == 'live-emergency-refresh'
        
        # Obtener datos de trading en vivo
        trading_data = _get_live_trading_data(force_refresh=is_emergency)
        
        # Obtener posiciones activas
        positions_data = _get_active_positions()
        
        # Obtener órdenes pendientes
        orders_data = _get_pending_orders()
        
        # Obtener señales del modelo
        signals_data = _get_model_signals()
        
        # Timestamp de última actualización
        last_update = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Con milisegundos
        
        logger.debug(f"⚡ Datos live actualizados: {len(positions_data.get('positions', []))} posiciones")
        
        return trading_data, positions_data, orders_data, signals_data, f"Live: {last_update}"
        
    except Exception as e:
        logger.error(f"❌ Error actualizando datos live: {e}")
        
        # Datos de fallback
        empty_data = {'error': str(e), 'timestamp': datetime.now().isoformat()}
        error_message = f"Error: {datetime.now().strftime('%H:%M:%S')}"
        
        return empty_data, empty_data, empty_data, empty_data, error_message

# ============================================================================
# CALLBACK: POSICIONES ACTIVAS
# ============================================================================

@callback(
    [
        Output('active-positions-table', 'data'),
        Output('active-positions-table', 'columns'),
        Output('positions-count-badge', 'children'),
        Output('positions-pnl-total', 'children'),
        Output('positions-pnl-total', 'color')
    ],
    [
        Input('live-positions-store', 'data'),
        Input('positions-refresh-interval', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_active_positions(positions_data: Dict[str, Any], 
                          n_intervals: int, theme: str) -> Tuple:
    """
    Actualiza la tabla de posiciones activas
    """
    try:
        if not positions_data or 'error' in positions_data:
            return [], [], "0", "$0.00", "secondary"
        
        positions = positions_data.get('positions', [])
        
        if not positions:
            return [], [], "0", "$0.00", "secondary"
        
        # Configurar columnas de la tabla
        columns = _get_positions_table_columns()
        
        # Formatear datos para la tabla
        table_data = _format_positions_for_table(positions)
        
        # Calcular métricas agregadas
        positions_count = len(positions)
        total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        pnl_color = "success" if total_pnl >= 0 else "danger"
        
        return table_data, columns, str(positions_count), f"${total_pnl:+,.2f}", pnl_color
        
    except Exception as e:
        logger.error(f"❌ Error actualizando posiciones: {e}")
        return [], [], "Error", "Error", "warning"

# ============================================================================
# CALLBACK: ÓRDENES PENDIENTES
# ============================================================================

@callback(
    [
        Output('pending-orders-table', 'data'),
        Output('pending-orders-table', 'columns'),
        Output('orders-count-badge', 'children'),
        Output('orders-management-controls', 'style')
    ],
    [
        Input('live-orders-store', 'data'),
        Input('orders-filter-dropdown', 'value'),
        Input('orders-symbol-filter', 'value')
    ],
    prevent_initial_call=False
)
def update_pending_orders(orders_data: Dict[str, Any], 
                         order_filter: str, symbol_filter: str) -> Tuple:
    """
    Actualiza la tabla de órdenes pendientes
    """
    try:
        if not orders_data or 'error' in orders_data:
            return [], [], "0", {'display': 'none'}
        
        orders = orders_data.get('orders', [])
        
        # Aplicar filtros
        filtered_orders = _filter_orders(orders, order_filter, symbol_filter)
        
        if not filtered_orders:
            empty_columns = [{"name": "No hay órdenes", "id": "empty"}]
            empty_data = [{"empty": "No hay órdenes pendientes"}]
            return empty_data, empty_columns, "0", {'display': 'none'}
        
        # Configurar columnas
        columns = _get_orders_table_columns()
        
        # Formatear datos
        table_data = _format_orders_for_table(filtered_orders)
        
        # Mostrar controles si hay órdenes
        controls_style = {'display': 'block'}
        
        return table_data, columns, str(len(filtered_orders)), controls_style
        
    except Exception as e:
        logger.error(f"❌ Error actualizando órdenes: {e}")
        return [], [], "Error", {'display': 'none'}

# ============================================================================
# CALLBACK: SEÑALES DEL MODELO
# ============================================================================

@callback(
    [
        Output('signals-feed-container', 'children'),
        Output('signals-stats-cards', 'children'),
        Output('model-confidence-gauge', 'figure')
    ],
    [
        Input('live-signals-store', 'data'),
        Input('signals-filter-dropdown', 'value'),
        Input('model-update-interval', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_model_signals(signals_data: Dict[str, Any], signal_filter: str,
                        n_intervals: int, theme: str) -> Tuple:
    """
    Actualiza el feed de señales del modelo y estadísticas
    """
    try:
        if not signals_data or 'error' in signals_data:
            empty_feed = html.P("Cargando señales...", className="text-muted text-center py-3")
            empty_stats = html.Div()
            empty_gauge = _create_empty_gauge(theme)
            return empty_feed, empty_stats, empty_gauge
        
        signals = signals_data.get('signals', [])
        
        # Filtrar señales
        filtered_signals = _filter_signals(signals, signal_filter)
        
        # Crear feed de señales
        signals_feed = _create_signals_feed(filtered_signals, theme)
        
        # Crear estadísticas de señales
        stats_cards = _create_signals_stats_cards(signals)
        
        # Crear gauge de confianza del modelo
        confidence_gauge = _create_model_confidence_gauge(signals_data, theme)
        
        return signals_feed, stats_cards, confidence_gauge
        
    except Exception as e:
        logger.error(f"❌ Error actualizando señales: {e}")
        
        error_feed = dbc.Alert(f"Error: {str(e)}", color="danger", className="mb-0")
        error_stats = html.Div()
        error_gauge = _create_empty_gauge(theme)
        
        return error_feed, error_stats, error_gauge

# ============================================================================
# CALLBACK: CONTROLES DEL BOT
# ============================================================================

@callback(
    [
        Output('bot-status-store', 'data'),
        Output('bot-status-indicator', 'children'),
        Output('bot-status-indicator', 'color'),
        Output('bot-controls-feedback', 'children'),
        Output('bot-controls-feedback', 'is_open'),
        Output('start-bot-btn', 'disabled'),
        Output('pause-bot-btn', 'disabled'),
        Output('stop-bot-btn', 'disabled'),
        Output('emergency-stop-btn', 'disabled')
    ],
    [
        Input('start-bot-btn', 'n_clicks'),
        Input('pause-bot-btn', 'n_clicks'),
        Input('stop-bot-btn', 'n_clicks'),
        Input('emergency-stop-btn', 'n_clicks'),
        Input('bot-status-refresh', 'n_intervals')
    ],
    [
        State('bot-status-store', 'data')
    ],
    prevent_initial_call=False
)
def handle_bot_controls(start_clicks: int, pause_clicks: int, stop_clicks: int,
                       emergency_clicks: int, status_intervals: int,
                       current_status: Dict[str, Any]) -> Tuple:
    """
    Maneja los controles del bot y actualiza su estado
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        # Obtener estado actual del bot
        if not current_status:
            current_status = _get_bot_status()
        
        # Procesar acción de control
        if triggered_id and triggered_id != 'bot-status-refresh':
            action_result = _execute_bot_action(triggered_id, current_status)
            
            # Actualizar estado después de la acción
            new_status = action_result['new_status']
            feedback_alert = action_result['feedback']
            show_feedback = True
        else:
            # Solo actualización de estado
            new_status = _get_bot_status()
            feedback_alert = dbc.Alert()
            show_feedback = False
        
        # Determinar indicador de estado
        status_text, status_color = _get_status_indicator(new_status)
        
        # Determinar qué botones habilitar/deshabilitar
        buttons_state = _get_buttons_state(new_status)
        
        return (new_status, status_text, status_color, feedback_alert, show_feedback,
                buttons_state['start'], buttons_state['pause'], 
                buttons_state['stop'], buttons_state['emergency'])
        
    except Exception as e:
        logger.error(f"❌ Error en controles del bot: {e}")
        
        error_status = {'status': 'error', 'error': str(e)}
        error_alert = dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
        
        return (error_status, "ERROR", "danger", error_alert, True,
                False, False, False, False)

# ============================================================================
# CALLBACK: MÉTRICAS EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('live-pnl-gauge', 'figure'),
        Output('live-win-rate-gauge', 'figure'),
        Output('live-trades-counter', 'children'),
        Output('live-volume-counter', 'children'),
        Output('live-balance-display', 'children'),
        Output('live-drawdown-indicator', 'children'),
        Output('live-drawdown-indicator', 'color')
    ],
    [
        Input('live-trading-data-store', 'data'),
        Input('live-metrics-fast-update', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_live_metrics(trading_data: Dict[str, Any], n_intervals: int,
                       theme: str) -> Tuple:
    """
    Actualiza métricas en tiempo real con gauges y contadores
    """
    try:
        if not trading_data or 'error' in trading_data:
            # Métricas por defecto en caso de error
            empty_gauge = _create_empty_gauge(theme)
            return (empty_gauge, empty_gauge, "0", "$0", "$0.00", "0.0%", "secondary")
        
        # Obtener métricas específicas
        metrics = _get_live_metrics_detailed(trading_data)
        
        # Crear gauges
        pnl_gauge = _create_pnl_gauge(metrics['daily_pnl'], theme)
        win_rate_gauge = _create_win_rate_gauge(metrics['win_rate'], theme)
        
        # Formatear contadores
        trades_count = str(metrics['total_trades_today'])
        volume_display = f"${metrics['daily_volume']:,.0f}"
        balance_display = f"${metrics['total_balance']:,.2f}"
        
        # Indicador de drawdown
        drawdown = metrics['current_drawdown']
        drawdown_text = f"{drawdown:.1f}%"
        drawdown_color = "danger" if drawdown > 10 else "warning" if drawdown > 5 else "success"
        
        return (pnl_gauge, win_rate_gauge, trades_count, volume_display,
                balance_display, drawdown_text, drawdown_color)
        
    except Exception as e:
        logger.error(f"❌ Error actualizando métricas live: {e}")
        
        empty_gauge = _create_empty_gauge(theme)
        return (empty_gauge, empty_gauge, "Error", "Error", "Error", "Error", "danger")

# ============================================================================
# CALLBACK: ACTIVITY FEED
# ============================================================================

@callback(
    [
        Output('activity-feed-container', 'children'),
        Output('activity-auto-scroll', 'data')
    ],
    [
        Input('live-trading-data-store', 'data'),
        Input('activity-refresh-interval', 'n_intervals'),
        Input('clear-activity-btn', 'n_clicks')
    ],
    [
        State('activity-filter-dropdown', 'value'),
        State('activity-auto-scroll', 'data')
    ],
    prevent_initial_call=False
)
def update_activity_feed(trading_data: Dict[str, Any], n_intervals: int,
                        clear_clicks: int, activity_filter: str,
                        auto_scroll: bool) -> Tuple[html.Div, bool]:
    """
    Actualiza el feed de actividad del sistema
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        # Si se presionó clear, limpiar feed
        if triggered_id == 'clear-activity-btn':
            return html.Div([
                html.P("Feed de actividad limpiado", 
                      className="text-muted text-center py-3")
            ]), auto_scroll
        
        # Obtener actividades recientes
        activities = _get_recent_activities(trading_data, activity_filter)
        
        # Crear feed de actividad
        activity_feed = _create_activity_feed(activities)
        
        return activity_feed, auto_scroll
        
    except Exception as e:
        logger.error(f"❌ Error actualizando activity feed: {e}")
        
        error_feed = dbc.Alert(
            f"Error cargando actividad: {str(e)}",
            color="warning",
            className="mb-0"
        )
        
        return error_feed, auto_scroll

# ============================================================================
# CALLBACK: GESTIÓN DE ÓRDENES
# ============================================================================

@callback(
    [
        Output('order-action-feedback', 'children'),
        Output('order-action-feedback', 'is_open')
    ],
    [
        Input('cancel-all-orders-btn', 'n_clicks'),
        Input('cancel-symbol-orders-btn', 'n_clicks'),
        Input({'type': 'cancel-order-btn', 'order_id': ALL}, 'n_clicks')
    ],
    [
        State('orders-symbol-filter', 'value'),
        State('live-orders-store', 'data')
    ],
    prevent_initial_call=True
)
def handle_order_management(cancel_all_clicks: int, cancel_symbol_clicks: int,
                           cancel_individual: List[int], symbol_filter: str,
                           orders_data: Dict[str, Any]) -> Tuple[dbc.Alert, bool]:
    """
    Maneja las acciones de gestión de órdenes
    """
    try:
        if not ctx.triggered:
            return dbc.Alert(), False
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if 'cancel-all-orders-btn' in triggered_id:
            # Cancelar todas las órdenes
            result = _cancel_all_orders()
            message = f"Canceladas {result['count']} órdenes"
            color = "success" if result['success'] else "danger"
            
        elif 'cancel-symbol-orders-btn' in triggered_id:
            # Cancelar órdenes de un símbolo específico
            result = _cancel_symbol_orders(symbol_filter)
            message = f"Canceladas {result['count']} órdenes de {symbol_filter}"
            color = "success" if result['success'] else "danger"
            
        elif 'cancel-order-btn' in triggered_id:
            # Cancelar orden individual
            order_data = eval(triggered_id)
            order_id = order_data['order_id']
            result = _cancel_individual_order(order_id)
            message = f"Orden {order_id} {'cancelada' if result['success'] else 'error al cancelar'}"
            color = "success" if result['success'] else "danger"
            
        else:
            return dbc.Alert(), False
        
        alert = dbc.Alert([
            html.I(className=f"fas fa-{'check' if color == 'success' else 'exclamation-triangle'} me-2"),
            message
        ], color=color, dismissable=True, duration=4000)
        
        return alert, True
        
    except Exception as e:
        logger.error(f"❌ Error en gestión de órdenes: {e}")
        
        error_alert = dbc.Alert(
            f"Error: {str(e)}",
            color="danger",
            dismissable=True
        )
        
        return error_alert, True

# ============================================================================
# CALLBACK: CONFIGURACIÓN DE TRADING EN VIVO
# ============================================================================

@callback(
    [
        Output('live-trading-config-store', 'data'),
        Output('config-update-feedback', 'children')
    ],
    [
        Input('max-positions-slider', 'value'),
        Input('position-size-slider', 'value'),
        Input('stop-loss-slider', 'value'),
        Input('take-profit-slider', 'value'),
        Input('confidence-threshold-slider', 'value'),
        Input('auto-trading-toggle', 'value'),
        Input('risk-management-toggle', 'value')
    ],
    prevent_initial_call=True
)
def update_live_trading_config(max_positions: int, position_size: float,
                              stop_loss: float, take_profit: float,
                              confidence_threshold: float, auto_trading: List[str],
                              risk_management: List[str]) -> Tuple[Dict[str, Any], str]:
    """
    Actualiza configuración de trading en vivo
    """
    try:
        config = {
            'max_positions': max_positions,
            'position_size_percent': position_size,
            'stop_loss_percent': stop_loss,
            'take_profit_percent': take_profit,
            'confidence_threshold': confidence_threshold,
            'auto_trading_enabled': 'auto' in (auto_trading or []),
            'risk_management_enabled': 'risk' in (risk_management or []),
            'updated_at': datetime.now().isoformat()
        }
        
        # Validar configuración
        validation_result = _validate_trading_config(config)
        
        if validation_result['valid']:
            feedback = f"✅ Configuración actualizada correctamente"
            logger.info(f"⚙️ Trading config actualizada: {config}")
        else:
            feedback = f"⚠️ Advertencia: {validation_result['message']}"
        
        return config, feedback
        
    except Exception as e:
        logger.error(f"❌ Error actualizando configuración: {e}")
        return {}, f"❌ Error: {str(e)}"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_live_trading_data(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Obtiene datos generales de trading en vivo
    """
    try:
        # En implementación real, esto vendría del sistema de trading
        import random
        
        return {
            'bot_status': random.choice(['running', 'paused', 'stopped']),
            'total_balance': random.uniform(18000, 22000),
            'daily_pnl': random.uniform(-200, 400),
            'daily_volume': random.uniform(5000, 25000),
            'active_positions_count': random.randint(0, 8),
            'pending_orders_count': random.randint(0, 12),
            'last_trade_time': datetime.now() - timedelta(minutes=random.randint(1, 30)),
            'win_rate_today': random.uniform(55, 75),
            'trades_today': random.randint(5, 25),
            'avg_trade_duration': random.uniform(30, 180),
            'current_drawdown': random.uniform(0, 8),
            'model_accuracy': random.uniform(0.65, 0.85),
            'system_health': random.uniform(0.8, 1.0),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos live: {e}")
        return {'error': str(e)}

def _get_active_positions() -> Dict[str, Any]:
    """
    Obtiene posiciones activas del sistema
    """
    try:
        # Generar posiciones de ejemplo
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        positions = []
        
        for i in range(random.randint(2, 6)):
            symbol = random.choice(symbols)
            side = random.choice(['LONG', 'SHORT'])
            entry_price = random.uniform(100, 50000)
            current_price = entry_price * random.uniform(0.98, 1.02)
            size = random.uniform(0.1, 2.0)
            
            unrealized_pnl = (current_price - entry_price) * size if side == 'LONG' else (entry_price - current_price) * size
            
            position = {
                'position_id': f"POS{i+1:04d}",
                'symbol': symbol,
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl,
                'entry_time': datetime.now() - timedelta(minutes=random.randint(10, 300)),
                'stop_loss': entry_price * (0.95 if side == 'LONG' else 1.05),
                'take_profit': entry_price * (1.05 if side == 'LONG' else 0.95),
                'margin_used': entry_price * size * 0.1,  # 10x leverage
                'roi_percent': (unrealized_pnl / (entry_price * size)) * 100
            }
            
            positions.append(position)
        
        return {'positions': positions, 'count': len(positions)}
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones: {e}")
        return {'error': str(e)}

def _get_pending_orders() -> Dict[str, Any]:
    """
    Obtiene órdenes pendientes del sistema
    """
    try:
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        order_types = ['LIMIT', 'STOP_LOSS', 'TAKE_PROFIT', 'STOP_LIMIT']
        orders = []
        
        for i in range(random.randint(3, 10)):
            symbol = random.choice(symbols)
            side = random.choice(['BUY', 'SELL'])
            order_type = random.choice(order_types)
            
            order = {
                'order_id': f"ORD{i+1:06d}",
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'size': random.uniform(0.1, 5.0),
                'price': random.uniform(100, 50000),
                'status': random.choice(['NEW', 'PARTIALLY_FILLED', 'PENDING']),
                'created_time': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                'filled_size': random.uniform(0, 0.5) if random.random() > 0.7 else 0,
                'remaining_size': None,  # Se calculará
                'time_in_force': random.choice(['GTC', 'IOC', 'FOK']),
                'reduce_only': random.choice([True, False])
            }
            
            # Calcular tamaño restante
            order['remaining_size'] = order['size'] - order['filled_size']
            
            orders.append(order)
        
        return {'orders': orders, 'count': len(orders)}
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo órdenes: {e}")
        return {'error': str(e)}

def _get_model_signals() -> Dict[str, Any]:
    """
    Obtiene señales del modelo de IA
    """
    try:
        import random
        
        signals = []
        signal_types = ['BUY', 'SELL', 'HOLD']
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        for i in range(random.randint(5, 15)):
            signal = {
                'signal_id': f"SIG{i+1:05d}",
                'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                'symbol': random.choice(symbols),
                'signal': random.choice(signal_types),
                'confidence': random.uniform(0.6, 0.95),
                'price': random.uniform(100, 50000),
                'reasoning': random.choice([
                    'Breakout alcista detectado',
                    'RSI en sobreventa',
                    'Confluencia de medias móviles',
                    'Patrón de reversión',
                    'Volumen anómalo',
                    'Soporte/resistencia clave'
                ]),
                'executed': random.choice([True, False]),
                'execution_price': None,
                'pnl': None
            }
            
            # Si fue ejecutada, agregar datos de ejecución
            if signal['executed']:
                signal['execution_price'] = signal['price'] * random.uniform(0.999, 1.001)
                signal['pnl'] = random.uniform(-50, 150)
            
            signals.append(signal)
        
        # Ordenar por timestamp descendente
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'signals': signals,
            'total_signals': len(signals),
            'executed_signals': len([s for s in signals if s['executed']]),
            'avg_confidence': sum(s['confidence'] for s in signals) / len(signals) if signals else 0,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo señales: {e}")
        return {'error': str(e)}