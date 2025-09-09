# Ruta: core/monitoring/pages/risk_analysis_page.py
"""
monitoring/pages/risk_analysis_page.py
Página de Análisis de Riesgo - Trading Bot v10
"""

from typing import Dict, Any, List
import numpy as np


class RiskAnalysisPagePlaceholders:
    def _simulate_portfolio_returns(self, portfolio_data: Dict[str, Any], periods: int) -> np.ndarray:
        """Simula retornos del portfolio"""
        # Simular retornos correlacionados para múltiples activos
        num_assets = len(portfolio_data)
        
        # Generar matriz de correlación realista
        correlations = np.random.uniform(0.3, 0.8, (num_assets, num_assets))
        np.fill_diagonal(correlations, 1.0)
        correlations = (correlations + correlations.T) / 2  # Hacer simétrica
        
        # Generar retornos usando distribución multivariada
        means = np.random.uniform(0.0005, 0.002, num_assets)  # Retornos esperados
        volatilities = np.random.uniform(0.015, 0.04, num_assets)  # Volatilidades
        
        # Matriz de covarianza
        cov_matrix = np.outer(volatilities, volatilities) * correlations
        
        # Generar retornos
        returns = np.random.multivariate_normal(means, cov_matrix, periods)
        
        # Pesos iguales por simplicidad
        weights = np.ones(num_assets) / num_assets
        
        # Retornos del portfolio
        portfolio_returns = np.dot(returns, weights)
        
        return portfolio_returns
    
    def _generate_sample_portfolio_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Genera datos de portfolio de muestra"""
        portfolio = {}
        
        for symbol in symbols:
            portfolio[symbol] = {
                'current_price': np.random.uniform(30000, 70000) if 'BTC' in symbol else np.random.uniform(1000, 5000),
                'position_size': np.random.uniform(0.1, 0.4),
                'volatility': np.random.uniform(0.15, 0.45),
                'correlation_to_market': np.random.uniform(0.3, 0.9)
            }
        
        return portfolio
    
    def _calculate_correlations(self) -> Dict[str, Any]:
        """Calcula matriz de correlaciones"""
        try:
            if self.data_provider:
                symbols = self.data_provider.get_configured_symbols()
            else:
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
            
            # Generar matriz de correlación simulada
            n_assets = len(symbols)
            correlations = np.random.uniform(0.2, 0.9, (n_assets, n_assets))
            np.fill_diagonal(correlations, 1.0)
            
            # Hacer simétrica
            correlations = (correlations + correlations.T) / 2
            
            return {
                'matrix': correlations.tolist(),
                'symbols': symbols,
                'avg_correlation': np.mean(correlations[np.triu_indices_from(correlations, k=1)]),
                'max_correlation': np.max(correlations[np.triu_indices_from(correlations, k=1)]),
                'min_correlation': np.min(correlations[np.triu_indices_from(correlations, k=1)])
            }
            
        except Exception as e:
            logger.error(f"Error al calcular correlaciones: {e}")
            return {}
    
    def _calculate_exposures(self) -> Dict[str, Any]:
        """Calcula exposiciones del portfolio"""
        try:
            if self.data_provider:
                symbols = self.data_provider.get_configured_symbols()
            else:
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
            
            # Generar exposiciones simuladas
            exposures = {}
            total_exposure = 0
            
            for symbol in symbols:
                exposure = np.random.uniform(0.15, 0.35)
                exposures[symbol] = {
                    'percentage': exposure * 100,
                    'value': exposure * 10000,  # Asumir portfolio de $10k
                    'risk_contribution': exposure * np.random.uniform(0.8, 1.2)
                }
                total_exposure += exposure
            
            # Normalizar para que sume 100%
            for symbol in exposures:
                exposures[symbol]['percentage'] = (exposures[symbol]['percentage'] / total_exposure) * 100
                exposures[symbol]['value'] = (exposures[symbol]['value'] / total_exposure) * 10000
            
            # Análisis por sectores/categorías
            sector_exposures = {
                'Crypto': sum(exp['percentage'] for exp in exposures.values()),
                'Large Cap': exposures.get('BTCUSDT', {}).get('percentage', 0) + exposures.get('ETHUSDT', {}).get('percentage', 0),
                'Alt Coins': sum(exp['percentage'] for symbol, exp in exposures.items() if symbol not in ['BTCUSDT', 'ETHUSDT'])
            }
            
            return {
                'symbols': exposures,
                'sectors': sector_exposures,
                'concentration_risk': max(exp['percentage'] for exp in exposures.values()),
                'diversification_ratio': len([exp for exp in exposures.values() if exp['percentage'] > 5])
            }
            
        except Exception as e:
            logger.error(f"Error al calcular exposiciones: {e}")
            return {}
    
    def _create_risk_alerts(self, risk_metrics: Dict[str, Any]) -> html.Div:
        """Crea alertas de riesgo"""
        alerts = []
        
        try:
            # Verificar VaR del portfolio
            portfolio_var = risk_metrics.get('portfolio_var', {}).get('value', 0)
            if portfolio_var > self.risk_limits['max_portfolio_var']:
                alerts.append(
                    dbc.Alert([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        html.Strong("VaR Alto: "),
                        f"El VaR del portfolio ({portfolio_var*100:.2f}%) excede el límite del {self.risk_limits['max_portfolio_var']*100:.1f}%"
                    ], color="danger", dismissable=True)
                )
            
            # Verificar drawdown actual
            current_dd = risk_metrics.get('max_drawdown', {}).get('current_drawdown', 0)
            if current_dd > self.risk_limits['max_drawdown']:
                alerts.append(
                    dbc.Alert([
                        html.I(className="fas fa-arrow-down me-2"),
                        html.Strong("Drawdown Alto: "),
                        f"Drawdown actual ({current_dd*100:.2f}%) excede el límite del {self.risk_limits['max_drawdown']*100:.1f}%"
                    ], color="warning", dismissable=True)
                )
            
            # Verificar concentración por símbolo
            symbols_risk = risk_metrics.get('symbols', {})
            for symbol, metrics in symbols_risk.items():
                position_size = metrics.get('position_size', 0)
                if position_size > self.risk_limits['max_position_size']:
                    alerts.append(
                        dbc.Alert([
                            html.I(className="fas fa-bullseye me-2"),
                            html.Strong("Concentración Alta: "),
                            f"{symbol} representa {position_size*100:.1f}% del portfolio (límite: {self.risk_limits['max_position_size']*100:.1f}%)"
                        ], color="warning", dismissable=True)
                    )
            
            # Si no hay alertas, mostrar estado OK
            if not alerts:
                alerts.append(
                    dbc.Alert([
                        html.I(className="fas fa-check-circle me-2"),
                        html.Strong("Estado Normal: "),
                        "Todos los límites de riesgo están dentro de los parámetros aceptables"
                    ], color="success", dismissable=True)
                )
            
            return html.Div(alerts)
            
        except Exception as e:
            logger.error(f"Error al crear alertas de riesgo: {e}")
            return html.Div()
    
    def _create_risk_dashboard_cards(self, risk_metrics: Dict[str, Any]) -> dbc.Row:
        """Crea tarjetas del dashboard de riesgo"""
        cards = []
        
        try:
            # VaR del Portfolio
            portfolio_var = risk_metrics.get('portfolio_var', {})
            var_value = portfolio_var.get('value', 0)
            var_color = "danger" if var_value > self.risk_limits['max_portfolio_var'] else "warning"
            
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Portfolio VaR (95%)",
                    value=f"{var_value*100:.2f}%",
                    subtitle=f"${portfolio_var.get('currency_value', 0):,.0f}",
                    icon="fas fa-exclamation-triangle",
                    color=var_color
                )
            ], width=12, md=6, lg=2))
            
            # CVaR del Portfolio
            portfolio_cvar = risk_metrics.get('portfolio_cvar', {})
            cvar_value = portfolio_cvar.get('value', 0)
            
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Portfolio CVaR",
                    value=f"{cvar_value*100:.2f}%",
                    subtitle=f"${portfolio_cvar.get('currency_value', 0):,.0f}",
                    icon="fas fa-chart-line",
                    color="danger"
                )
            ], width=12, md=6, lg=2))
            
            # Volatilidad
            volatility = risk_metrics.get('portfolio_volatility', {}).get('annualized', 0)
            vol_color = "warning" if volatility > 0.3 else "info"
            
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Volatilidad Anual",
                    value=f"{volatility*100:.1f}%",
                    subtitle="Desviación estándar",
                    icon="fas fa-wave-square",
                    color=vol_color
                )
            ], width=12, md=6, lg=2))
            
            # Máximo Drawdown
            max_dd = risk_metrics.get('max_drawdown', {}).get('value', 0)
            dd_color = "danger" if max_dd > self.risk_limits['max_drawdown'] else "warning"
            
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Máximo Drawdown",
                    value=f"{max_dd*100:.2f}%",
                    subtitle="Pérdida máxima",
                    icon="fas fa-arrow-down",
                    color=dd_color
                )
            ], width=12, md=6, lg=2))
            
            # Número de posiciones
            num_positions = len(risk_metrics.get('symbols', {}))
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Posiciones Activas",
                    value=str(num_positions),
                    subtitle="Diversificación",
                    icon="fas fa-chart-pie",
                    color="primary"
                )
            ], width=12, md=6, lg=2))
            
            # Score de riesgo general
            risk_score = self._calculate_overall_risk_score(risk_metrics)
            score_color = "danger" if risk_score > 70 else "warning" if risk_score > 40 else "success"
            
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Score de Riesgo",
                    value=f"{risk_score:.0f}/100",
                    subtitle="Evaluación general",
                    icon="fas fa-thermometer-half",
                    color=score_color
                )
            ], width=12, md=6, lg=2))
            
            return dbc.Row(cards)
            
        except Exception as e:
            logger.error(f"Error al crear dashboard de riesgo: {e}")
            return dbc.Row([])
    
    def _calculate_overall_risk_score(self, risk_metrics: Dict[str, Any]) -> float:
        """Calcula score general de riesgo (0-100)"""
        try:
            score_components = []
            
            # VaR score (0-30 puntos)
            var_value = risk_metrics.get('portfolio_var', {}).get('value', 0)
            var_score = min((var_value / self.risk_limits['max_portfolio_var']) * 30, 30)
            score_components.append(var_score)
            
            # Volatilidad score (0-25 puntos)
            volatility = risk_metrics.get('portfolio_volatility', {}).get('annualized', 0)
            vol_score = min((volatility / 0.5) * 25, 25)  # 50% volatilidad = 25 puntos
            score_components.append(vol_score)
            
            # Drawdown score (0-25 puntos)
            max_dd = risk_metrics.get('max_drawdown', {}).get('value', 0)
            dd_score = min((max_dd / self.risk_limits['max_drawdown']) * 25, 25)
            score_components.append(dd_score)
            
            # Concentración score (0-20 puntos)
            symbols_risk = risk_metrics.get('symbols', {})
            if symbols_risk:
                max_position = max(s.get('position_size', 0) for s in symbols_risk.values())
                conc_score = min((max_position / self.risk_limits['max_position_size']) * 20, 20)
                score_components.append(conc_score)
            
            return sum(score_components)
            
        except Exception as e:
            logger.error(f"Error al calcular score de riesgo: {e}")
            return 50  # Score medio por defecto
    
    def _create_var_analysis_chart(self, risk_metrics: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de análisis de VaR"""
        try:
            # Simular distribución de retornos para VaR
            returns = np.random.normal(0.001, 0.02, 1000)  # 1000 observaciones simuladas
            
            fig = go.Figure()
            
            # Histograma de retornos
            fig.add_trace(go.Histogram(
                x=returns * 100,  # Convertir a porcentajes
                nbinsx=50,
                name='Distribución de Retornos',
                opacity=0.7,
                marker_color='rgba(0, 123, 255, 0.7)'
            ))
            
            # Líneas de VaR
            var_95 = np.percentile(returns, 5) * 100
            var_99 = np.percentile(returns, 1) * 100
            
            fig.add_vline(
                x=var_95,
                line_dash="dash",
                line_color="orange",
                annotation_text=f"VaR 95%: {var_95:.2f}%"
            )
            
            fig.add_vline(
                x=var_99,
                line_dash="dash",
                line_color="red",
                annotation_text=f"VaR 99%: {var_99:.2f}%"
            )
            
            # CVaR (Expected Shortfall)
            cvar_95 = np.mean(returns[returns <= np.percentile(returns, 5)]) * 100
            fig.add_vline(
                x=cvar_95,
                line_dash="dot",
                line_color="darkred",
                annotation_text=f"CVaR 95%: {cvar_95:.2f}%"
            )
            
            fig.update_layout(
                title="Análisis de Value at Risk (VaR)",
                xaxis_title="Retorno Diario (%)",
                yaxis_title="Frecuencia",
                height=self.page_config['chart_height'],
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear análisis de VaR: {e}")
            return self._create_empty_chart("Error en análisis de VaR")
    
    def _create_risk_limits_monitor(self, risk_metrics: Dict[str, Any]) -> html.Div:
        """Crea monitor de límites de riesgo"""
        try:
            limits_data = []
            
            # VaR del portfolio
            current_var = risk_metrics.get('portfolio_var', {}).get('value', 0)
            var_usage = (current_var / self.risk_limits['max_portfolio_var']) * 100
            limits_data.append({
                'limit': 'VaR del Portfolio',
                'current': f"{current_var*100:.2f}%",
                'limit_value': f"{self.risk_limits['max_portfolio_var']*100:.1f}%",
                'usage': var_usage,
                'status': 'danger' if var_usage > 100 else 'warning' if var_usage > 80 else 'success'
            })
            
            # Drawdown máximo
            current_dd = risk_metrics.get('max_drawdown', {}).get('value', 0)
            dd_usage = (current_dd / self.risk_limits['max_drawdown']) * 100
            limits_data.append({
                'limit': 'Máximo Drawdown',
                'current': f"{current_dd*100:.2f}%",
                'limit_value': f"{self.risk_limits['max_drawdown']*100:.1f}%",
                'usage': dd_usage,
                'status': 'danger' if dd_usage > 100 else 'warning' if dd_usage > 80 else 'success'
            })
            
            # Concentración máxima
            symbols_risk = risk_metrics.get('symbols', {})
            if symbols_risk:
                max_position = max(s.get('position_size', 0) for s in symbols_risk.values())
                conc_usage = (max_position / self.risk_limits['max_position_size']) * 100
                limits_data.append({
                    'limit': 'Concentración Máxima',
                    'current': f"{max_position*100:.1f}%",
                    'limit_value': f"{self.risk_limits['max_position_size']*100:.1f}%",
                    'usage': conc_usage,
                    'status': 'danger' if conc_usage > 100 else 'warning' if conc_usage > 80 else 'success'
                })
            
            # Crear componentes visuales
            limit_items = []
            for limit_data in limits_data:
                progress_color = limit_data['status']
                
                limit_item = html.Div([
                    html.Div([
                        html.Strong(limit_data['limit']),
                        html.Span(f" {limit_data['current']} / {limit_data['limit_value']}", 
                                 className="text-muted")
                    ], className="d-flex justify-content-between mb-1"),
                    
                    dbc.Progress(
                        value=min(limit_data['usage'], 100),
                        color=progress_color,
                        className="mb-3",
                        style={'height': '8px'}
                    )
                ])
                
                limit_items.append(limit_item)
            
            return html.Div(limit_items)
            
        except Exception as e:
            logger.error(f"Error al crear monitor de límites: {e}")
            return html.P("Error al cargar monitor de límites", className="text-danger")
    
    def _create_correlation_heatmap(self, correlation_data: Dict[str, Any]) -> go.Figure:
        """Crea heatmap de correlaciones"""
        try:
            matrix = correlation_data.get('matrix', [])
            symbols = correlation_data.get('symbols', [])
            
            if not matrix or not symbols:
                return self._create_empty_chart("No hay datos de correlación")
            
            fig = go.Figure(data=go.Heatmap(
                z=matrix,
                x=symbols,
                y=symbols,
                colorscale='RdBu',
                zmid=0,
                text=np.round(matrix, 2),
                texttemplate='%{text}',
                textfont={'size': 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title="Matriz de Correlaciones",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear heatmap de correlaciones: {e}")
            return self._create_empty_chart("Error en matriz de correlaciones")
    
    def _create_exposure_chart(self, exposure_data: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de exposiciones"""
        try:
            symbols_exposure = exposure_data.get('symbols', {})
            
            if not symbols_exposure:
                return self._create_empty_chart("No hay datos de exposición")
            
            symbols = list(symbols_exposure.keys())
            exposures = [data['percentage'] for data in symbols_exposure.values()]
            
            fig = go.Figure()
            
            # Gráfico de barras
            colors = ['red' if exp > 30 else 'orange' if exp > 20 else 'green' for exp in exposures]
            
            fig.add_trace(go.Bar(
                x=symbols,
                y=exposures,
                marker_color=colors,
                text=[f'{exp:.1f}%' for exp in exposures],
                textposition='outside'
            ))
            
            # Línea de límite
            fig.add_hline(
                y=self.risk_limits['max_position_size'] * 100,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Límite: {self.risk_limits['max_position_size']*100:.0f}%"
            )
            
            fig.update_layout(
                title="Exposición por Símbolo",
                xaxis_title="Símbolo",
                yaxis_title="Exposición (%)",
                height=400,
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de exposiciones: {e}")
            return self._create_empty_chart("Error en análisis de exposiciones")
    
    def _run_stress_test(self, risk_data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Ejecuta stress test según escenario"""
        try:
            scenario_config = self.stress_scenarios.get(scenario, {})
            shock = scenario_config.get('shock', 0)
            
            # Obtener métricas actuales
            current_metrics = risk_data.get('risk_metrics', {})
            portfolio_value = 10000  # Asumir $10k
            
            # Aplicar shock a cada posición
            symbols_risk = current_metrics.get('symbols', {})
            stress_results = {}
            
            total_loss = 0
            for symbol, metrics in symbols_risk.items():
                position_size = metrics.get('position_size', 0)
                position_value = portfolio_value * position_size
                
                # Pérdida por shock
                position_loss = position_value * abs(shock)
                total_loss += position_loss
                
                stress_results[symbol] = {
                    'original_value': position_value,
                    'loss': position_loss,
                    'new_value': position_value + (position_value * shock),
                    'loss_percentage': abs(shock) * 100
                }
            
            # Métricas del stress test
            total_loss_pct = (total_loss / portfolio_value) * 100
            new_portfolio_value = portfolio_value - total_loss
            
            return {
                'scenario': scenario,
                'scenario_config': scenario_config,
                'total_loss': total_loss,
                'total_loss_percentage': total_loss_pct,
                'new_portfolio_value': new_portfolio_value,
                'symbols_impact': stress_results
            }
            
        except Exception as e:
            logger.error(f"Error en stress test: {e}")
            return {}
    
    def _create_stress_test_chart(self, stress_results: Dict[str, Any], scenario: str) -> go.Figure:
        """Crea gráfico de resultados del stress test"""
        try:
            if not stress_results:
                return self._create_empty_chart("Error en stress test")
            
            symbols_impact = stress_results.get('symbols_impact', {})
            
            symbols = list(symbols_impact.keys())
            original_values = [data['original_value'] for data in symbols_impact.values()]
            new_values = [data['new_value'] for data in symbols_impact.values()]
            
            fig = go.Figure()
            
            # Valores originales
            fig.add_trace(go.Bar(
                name='Valor Original',
                x=symbols,
                y=original_values,
                marker_color='blue',
                opacity=0.7
            ))
            
            # Valores después del stress
            fig.add_trace(go.Bar(
                name='Valor Post-Stress',
                x=symbols,
                y=new_values,
                marker_color='red',
                opacity=0.7
            ))
            
            scenario_name = self.stress_scenarios.get(scenario, {}).get('name', scenario)
            
            fig.update_layout(
                title=f"Impacto del Stress Test: {scenario_name}",
                xaxis_title="Símbolo",
                yaxis_title="Valor ($)",
                height=400,
                barmode='group',
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de stress test: {e}")
            return self._create_empty_chart("Error en gráfico de stress test")
    
    def _create_stress_test_summary(self, stress_results: Dict[str, Any], scenario: str) -> html.Div:
        """Crea resumen del stress test"""
        try:
            if not stress_results:
                return html.P("Error en stress test", className="text-danger")
            
            scenario_config = stress_results.get('scenario_config', {})
            total_loss = stress_results.get('total_loss', 0)
            total_loss_pct = stress_results.get('total_loss_percentage', 0)
            
            return html.Div([
                html.H6(scenario_config.get('name', 'Stress Test'), className="text-primary"),
                html.P(scenario_config.get('description', ''), className="text-muted small"),
                html.Hr(),
                html.Div([
                    html.Strong("Pérdida Total: "),
                    html.Span(f"${total_loss:,.0f}", className="text-danger")
                ], className="mb-2"),
                html.Div([
                    html.Strong("Pérdida (%): "),
                    html.Span(f"{total_loss_pct:.2f}%", className="text-danger")
                ], className="mb-2"),
                html.Div([
                    html.Strong("Nuevo Valor: "),
                    html.Span(f"${stress_results.get('new_portfolio_value', 0):,.0f}")
                ], className="mb-3"),
                html.Div([
                    dbc.Badge(
                        "Alto Riesgo" if total_loss_pct > 15 else "Riesgo Moderado" if total_loss_pct > 5 else "Bajo Riesgo",
                        color="danger" if total_loss_pct > 15 else "warning" if total_loss_pct > 5 else "success"
                    )
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error al crear resumen de stress test: {e}")
            return html.P("Error en resumen", className="text-danger")
    
    def _run_monte_carlo_simulation(self, risk_data: Dict[str, Any], num_simulations: int) -> Dict[str, Any]:
        """Ejecuta simulación Monte Carlo"""
        try:
            # Parámetros de simulación
            time_horizon = 252  # 1 año de trading
            portfolio_value = 10000
            
            # Generar paths de precios
            returns_paths = []
            final_values = []
            
            for _ in range(num_simulations):
                # Generar path de retornos aleatorios
                daily_returns = np.random.normal(0.001, 0.02, time_horizon)  # 0.1% promedio, 2% volatilidad
                
                # Calcular valores del portfolio
                cumulative_returns = np.cumprod(1 + daily_returns)
                final_value = portfolio_value * cumulative_returns[-1]
                
                returns_paths.append(cumulative_returns)
                final_values.append(final_value)
            
            # Calcular estadísticas
            final_values = np.array(final_values)
            
            # Percentiles de resultados
            percentiles = {
                'p5': np.percentile(final_values, 5),
                'p25': np.percentile(final_values, 25),
                'p50': np.percentile(final_values, 50),
                'p75': np.percentile(final_values, 75),
                'p95': np.percentile(final_values, 95)
            }
            
            # Probabilidades de pérdida
            prob_loss = np.sum(final_values < portfolio_value) / num_simulations * 100
            prob_loss_10 = np.sum(final_values < portfolio_value * 0.9) / num_simulations * 100
            prob_loss_20 = np.sum(final_values < portfolio_value * 0.8) / num_simulations * 100
            
            return {
                'num_simulations': num_simulations,
                'time_horizon': time_horizon,
                'initial_value': portfolio_value,
                'final_values': final_values.tolist(),
                'returns_paths': [path.tolist() for path in returns_paths[:100]],  # Solo 100 paths para gráfico
                'percentiles': percentiles,
                'mean_final_value': np.mean(final_values),
                'std_final_value': np.std(final_values),
                'prob_loss': prob_loss,
                'prob_loss_10': prob_loss_10,
                'prob_loss_20': prob_loss_20,
                'var_95': portfolio_value - percentiles['p5'],
                'expected_shortfall': portfolio_value - np.mean(final_values[final_values <= percentiles['p5']])
            }
            
        except Exception as e:
            logger.error(f"Error en simulación Monte Carlo: {e}")
            return {}
    
    def _create_monte_carlo_chart(self, mc_results: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de simulación Monte Carlo"""
        try:
            if not mc_results:
                return self._create_empty_chart("Error en simulación Monte Carlo")
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=['Paths de Simulación (100 muestras)', 'Distribución de Valores Finales'],
                vertical_spacing=0.1,
                row_heights=[0.6, 0.4]
            )
            
            # Gráfico 1: Paths de simulación
            returns_paths = mc_results.get('returns_paths', [])
            initial_value = mc_results.get('initial_value', 10000)
            
            for i, path in enumerate(returns_paths[:50]):  # Mostrar solo 50 paths
                values = [initial_value * ret for ret in path]
                fig.add_trace(
                    go.Scatter(
                        y=values,
                        mode='lines',
                        line=dict(width=1, color='rgba(0, 123, 255, 0.3)'),
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=1, col=1
                )
            
            # Línea del valor inicial
            fig.add_hline(
                y=initial_value,
                line_dash="dash",
                line_color="red",
                annotation_text="Valor Inicial",
                row=1
            )
            
            # Gráfico 2: Distribución de valores finales
            final_values = mc_results.get('final_values', [])
            
            fig.add_trace(
                go.Histogram(
                    x=final_values,
                    nbinsx=50,
                    name='Distribución Final',
                    opacity=0.7,
                    marker_color='rgba(0, 123, 255, 0.7)'
                ),
                row=2, col=1
            )
            
            # Líneas de percentiles
            percentiles = mc_results.get('percentiles', {})
            for label, value in percentiles.items():
                fig.add_vline(
                    x=value,
                    line_dash="dot",
                    line_color="green" if label == 'p50' else "orange",
                    annotation_text=f"{label}: ${value:,.0f}",
                    row=2
                )
            
            fig.update_layout(
                title="Simulación Monte Carlo - Análisis de Escenarios",
                height=600,
                showlegend=False,
                margin=dict(l=0, r=0, t=60, b=0)
            )
            
            fig.update_xaxes(title_text="Días de Trading", row=1, col=1)
            fig.update_yaxes(title_text="Valor del Portfolio ($)", row=1, col=1)
            fig.update_xaxes(title_text="Valor Final ($)", row=2, col=1)
            fig.update_yaxes(title_text="Frecuencia", row=2, col=1)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico Monte Carlo: {e}")
            return self._create_empty_chart("Error en gráfico Monte Carlo")
    
    def _create_monte_carlo_statistics(self, mc_results: Dict[str, Any]) -> html.Div:
        """Crea estadísticas de Monte Carlo"""
        try:
            if not mc_results:
                return html.P("Error en estadísticas", className="text-danger")
            
            percentiles = mc_results.get('percentiles', {})
            
            return html.Div([
                html.H6("Estadísticas de Simulación", className="text-primary mb-3"),
                
                # Resultados esperados
                html.Div([
                    html.Strong("Valor Esperado: "),
                    html.Span(f"${mc_results.get('mean_final_value', 0):,.0f}")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Desviación Estándar: "),
                    html.Span(f"${mc_results.get('std_final_value', 0):,.0f}")
                ], className="mb-2"),
                
                html.Hr(),
                
                # Percentiles clave
                html.H6("Percentiles", className="mb-2"),
                html.Div([
                    html.Small(f"P5: ${percentiles.get('p5', 0):,.0f}", className="d-block"),
                    html.Small(f"P25: ${percentiles.get('p25', 0):,.0f}", className="d-block"),
                    html.Small(f"P50: ${percentiles.get('p50', 0):,.0f}", className="d-block"),
                    html.Small(f"P75: ${percentiles.get('p75', 0):,.0f}", className="d-block"),
                    html.Small(f"P95: ${percentiles.get('p95', 0):,.0f}", className="d-block")
                ], className="mb-3"),
                
                html.Hr(),
                
                # Probabilidades de pérdida
                html.H6("Probabilidades de Pérdida", className="mb-2"),
                html.Div([
                    dbc.Badge(f"{mc_results.get('prob_loss', 0):.1f}%", color="warning", className="me-1"),
                    html.Small("Cualquier pérdida", className="d-block mb-1"),
                    
                    dbc.Badge(f"{mc_results.get('prob_loss_10', 0):.1f}%", color="danger", className="me-1"),
                    html.Small("Pérdida > 10%", className="d-block mb-1"),
                    
                    dbc.Badge(f"{mc_results.get('prob_loss_20', 0):.1f}%", color="danger", className="me-1"),
                    html.Small("Pérdida > 20%", className="d-block")
                ], className="mb-3"),
                
                html.Hr(),
                
                # VaR de Monte Carlo
                html.Div([
                    html.Strong("VaR (95%): "),
                    html.Span(f"${mc_results.get('var_95', 0):,.0f}", className="text-danger")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Expected Shortfall: "),
                    html.Span(f"${mc_results.get('expected_shortfall', 0):,.0f}", className="text-danger")
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error al crear estadísticas Monte Carlo: {e}")
            return html.P("Error en estadísticas", className="text-danger")
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Crea un gráfico vacío con mensaje"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        
        return fig
"""
monitoring/pages/risk_analysis_page.py
Página de Análisis de Riesgo - Trading Bot v10

Esta página proporciona análisis integral de riesgo:
- Métricas de riesgo de mercado (VaR, CVaR, etc.)
- Análisis de correlaciones entre activos
- Stress testing y análisis de escenarios
- Gestión de exposición y concentración
- Monitoreo de límites de riesgo
- Alertas automáticas de riesgo
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from monitoring.pages.base_page import BasePage

logger = logging.getLogger(__name__)

class RiskAnalysisPage(BasePage):
    """
    Página de análisis integral de riesgo del Trading Bot v10
    
    Proporciona análisis avanzado de riesgo de mercado, operacional
    y de portfolio con herramientas de gestión y monitoreo.
    """
    
    def __init__(self, data_provider=None):
        """
        Inicializa la página de análisis de riesgo
        
        Args:
            data_provider: Proveedor de datos centralizado
        """
        super().__init__(data_provider=data_provider)
        
        # Configuración específica de la página Risk Analysis
        self.page_config.update({
            'title': 'Análisis de Riesgo',
            'update_interval': 30000,  # 30 segundos
            'auto_refresh': True,
            'enable_stress_testing': True,
            'enable_monte_carlo': True,
            'confidence_levels': [0.90, 0.95, 0.99],
            'default_confidence': 0.95,
            'chart_height': 450,
            'risk_alert_threshold': 0.15  # 15% para alertas
        })
        
        # Tipos de riesgo a analizar
        self.risk_categories = {
            'market': {
                'name': 'Riesgo de Mercado',
                'color': 'danger',
                'icon': 'fas fa-chart-line',
                'metrics': ['var', 'cvar', 'volatility', 'beta']
            },
            'credit': {
                'name': 'Riesgo de Crédito',
                'color': 'warning',
                'icon': 'fas fa-handshake',
                'metrics': ['counterparty_exposure', 'credit_rating']
            },
            'liquidity': {
                'name': 'Riesgo de Liquidez',
                'color': 'info',
                'icon': 'fas fa-tint',
                'metrics': ['bid_ask_spread', 'market_impact', 'trading_volume']
            },
            'operational': {
                'name': 'Riesgo Operacional',
                'color': 'secondary',
                'icon': 'fas fa-cogs',
                'metrics': ['system_uptime', 'execution_slippage', 'api_failures']
            },
            'concentration': {
                'name': 'Riesgo de Concentración',
                'color': 'primary',
                'icon': 'fas fa-bullseye',
                'metrics': ['position_concentration', 'sector_exposure', 'correlation_risk']
            }
        }
        
        # Escenarios de stress testing
        self.stress_scenarios = {
            'market_crash': {
                'name': 'Crash de Mercado',
                'description': 'Caída del 20% en todos los activos',
                'shock': -0.20,
                'duration_days': 1
            },
            'flash_crash': {
                'name': 'Flash Crash',
                'description': 'Caída súbita del 10% en 1 hora',
                'shock': -0.10,
                'duration_days': 0.04  # 1 hora
            },
            'volatility_spike': {
                'name': 'Spike de Volatilidad',
                'description': 'Aumento de volatilidad 5x',
                'shock': 0,
                'volatility_multiplier': 5
            },
            'liquidity_crisis': {
                'name': 'Crisis de Liquidez',
                'description': 'Spreads bid-ask aumentan 10x',
                'shock': 0,
                'liquidity_impact': 10
            },
            'correlation_breakdown': {
                'name': 'Breakdown de Correlaciones',
                'description': 'Correlaciones tienden a 1',
                'correlation_shock': 0.9
            },
            'black_swan': {
                'name': 'Evento Cisne Negro',
                'description': 'Evento extremo improbable',
                'shock': -0.50,
                'probability': 0.001
            }
        }
        
        # Límites de riesgo configurables
        self.risk_limits = {
            'max_portfolio_var': 0.05,  # 5% VaR máximo
            'max_position_size': 0.20,  # 20% máximo por posición
            'max_sector_exposure': 0.40,  # 40% máximo por sector
            'max_correlation': 0.80,  # 80% correlación máxima
            'max_drawdown': 0.15,  # 15% drawdown máximo
            'min_liquidity_ratio': 0.30  # 30% mínimo en activos líquidos
        }
        
        logger.info("RiskAnalysisPage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de análisis de riesgo
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Análisis de Riesgo",
                    subtitle="Gestión integral de riesgo y monitoreo de exposiciones",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Panel de alertas de riesgo
                self._create_risk_alerts_section(),
                
                # Controles de configuración
                self._create_risk_controls_section(),
                
                # Dashboard de riesgo principal
                self._create_risk_dashboard_section(),
                
                # Análisis de VaR y métricas de mercado
                dbc.Row([
                    dbc.Col([
                        self._create_var_analysis_section()
                    ], width=8),
                    dbc.Col([
                        self._create_risk_limits_monitor_section()
                    ], width=4)
                ], className="mb-4"),
                
                # Matriz de correlaciones y exposiciones
                dbc.Row([
                    dbc.Col([
                        self._create_correlation_matrix_section()
                    ], width=6),
                    dbc.Col([
                        self._create_exposure_analysis_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Stress testing y análisis de escenarios
                self._create_stress_testing_section(),
                
                # Monte Carlo y simulaciones
                self._create_monte_carlo_section(),
                
                # Componentes de actualización y stores
                self.create_refresh_interval("risk-refresh-interval"),
                dcc.Store(id='risk-data-store'),
                dcc.Store(id='risk-config-store', data={
                    'confidence_level': self.page_config['default_confidence'],
                    'time_horizon': 1,  # días
                    'enable_alerts': True,
                    'stress_scenario': 'market_crash'
                }),
                
            ], fluid=True, className="risk-analysis-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de RiskAnalysisPage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de análisis de riesgo: {e}")
            ])
    
    def _create_risk_alerts_section(self) -> dbc.Row:
        """Crea la sección de alertas de riesgo"""
        return dbc.Row([
            dbc.Col([
                html.Div(id="risk-alerts-container")
            ], width=12)
        ], className="mb-4")
    
    def _create_risk_controls_section(self) -> dbc.Row:
        """Crea la sección de controles de configuración"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Nivel de confianza
                            dbc.Col([
                                html.Label("Nivel de Confianza:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="confidence-level-selector",
                                    options=[
                                        {'label': '90%', 'value': 0.90},
                                        {'label': '95%', 'value': 0.95},
                                        {'label': '99%', 'value': 0.99}
                                    ],
                                    value=self.page_config['default_confidence'],
                                    placeholder="Nivel de confianza"
                                )
                            ], width=12, md=2),
                            
                            # Horizonte temporal
                            dbc.Col([
                                html.Label("Horizonte (días):", className="form-label mb-1"),
                                dbc.Input(
                                    id="time-horizon-input",
                                    type="number",
                                    value=1,
                                    min=1,
                                    max=30,
                                    step=1
                                )
                            ], width=12, md=2),
                            
                            # Método de cálculo
                            dbc.Col([
                                html.Label("Método VaR:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="var-method-selector",
                                    options=[
                                        {'label': 'Histórico', 'value': 'historical'},
                                        {'label': 'Paramétrico', 'value': 'parametric'},
                                        {'label': 'Monte Carlo', 'value': 'monte_carlo'}
                                    ],
                                    value='historical',
                                    placeholder="Método"
                                )
                            ], width=12, md=2),
                            
                            # Alertas activas
                            dbc.Col([
                                html.Label("Alertas:", className="form-label mb-1"),
                                dbc.Switch(
                                    id="enable-alerts-switch",
                                    label="Activar alertas automáticas",
                                    value=True
                                )
                            ], width=12, md=3),
                            
                            # Botones de acción
                            dbc.Col([
                                html.Label("Acciones:", className="form-label mb-1"),
                                dbc.ButtonGroup([
                                    dbc.Button("Recalcular", id="recalculate-risk-btn", 
                                              color="primary", size="sm"),
                                    dbc.Button("Configurar Límites", id="config-limits-btn", 
                                              color="secondary", size="sm")
                                ])
                            ], width=12, md=3)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_risk_dashboard_section(self) -> dbc.Row:
        """Crea el dashboard principal de riesgo"""
        return dbc.Row([
            dbc.Col([
                html.H5("Dashboard de Riesgo", className="section-title mb-3"),
                self.create_loading_component(
                    "risk-dashboard",
                    html.Div(id="risk-dashboard-cards"),
                    loading_type="default"
                )
            ], width=12)
        ], className="mb-4")
    
    def _create_var_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de VaR"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Value at Risk (VaR)", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "var-analysis",
                    dcc.Graph(
                        id="var-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_risk_limits_monitor_section(self) -> dbc.Card:
        """Crea la sección de monitoreo de límites"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Monitor de Límites de Riesgo", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "risk-limits",
                    html.Div(id="risk-limits-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_correlation_matrix_section(self) -> dbc.Card:
        """Crea la sección de matriz de correlaciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Matriz de Correlaciones", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "correlation-matrix",
                    dcc.Graph(
                        id="correlation-matrix-chart",
                        config=self.get_default_chart_config(),
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_exposure_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de exposiciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Exposiciones", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "exposure-analysis",
                    dcc.Graph(
                        id="exposure-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_stress_testing_section(self) -> dbc.Row:
        """Crea la sección de stress testing"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Stress Testing", className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                dcc.Dropdown(
                                    id="stress-scenario-selector",
                                    options=[
                                        {'label': scenario['name'], 'value': key}
                                        for key, scenario in self.stress_scenarios.items()
                                    ],
                                    value='market_crash',
                                    placeholder="Escenario",
                                    className="stress-scenario-dropdown"
                                )
                            ], width="auto", className="ms-auto")
                        ])
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                self.create_loading_component(
                                    "stress-test-results",
                                    dcc.Graph(
                                        id="stress-test-chart",
                                        config=self.get_default_chart_config(),
                                        style={'height': '400px'}
                                    ),
                                    loading_type="default"
                                )
                            ], width=8),
                            dbc.Col([
                                html.Div(id="stress-test-summary")
                            ], width=4)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_monte_carlo_section(self) -> dbc.Row:
        """Crea la sección de simulaciones Monte Carlo"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Simulación Monte Carlo", className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="monte-carlo-simulations",
                                        type="number",
                                        value=10000,
                                        min=1000,
                                        max=100000,
                                        step=1000
                                    ),
                                    dbc.InputGroupText("simulaciones")
                                ], size="sm")
                            ], width="auto"),
                            dbc.Col([
                                dbc.Button("Ejecutar", id="run-monte-carlo-btn", 
                                          color="primary", size="sm")
                            ], width="auto")
                        ])
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                self.create_loading_component(
                                    "monte-carlo-results",
                                    dcc.Graph(
                                        id="monte-carlo-chart",
                                        config=self.get_default_chart_config(),
                                        style={'height': '400px'}
                                    ),
                                    loading_type="default"
                                )
                            ], width=8),
                            dbc.Col([
                                html.Div(id="monte-carlo-statistics")
                            ], width=4)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de análisis de riesgo
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para actualizar configuración de riesgo
        @app.callback(
            Output('risk-config-store', 'data'),
            [Input('confidence-level-selector', 'value'),
             Input('time-horizon-input', 'value'),
             Input('var-method-selector', 'value'),
             Input('enable-alerts-switch', 'value'),
             Input('stress-scenario-selector', 'value')],
            [State('risk-config-store', 'data')]
        )
        def update_risk_config(confidence, horizon, method, alerts, scenario, current_config):
            """Actualiza configuración de análisis de riesgo"""
            return {
                'confidence_level': confidence or self.page_config['default_confidence'],
                'time_horizon': horizon or 1,
                'var_method': method or 'historical',
                'enable_alerts': alerts if alerts is not None else True,
                'stress_scenario': scenario or 'market_crash',
                'last_update': datetime.now().isoformat()
            }
        
        # Callback principal para cargar datos de riesgo
        @app.callback(
            Output('risk-data-store', 'data'),
            [Input('risk-config-store', 'data'),
             Input('risk-refresh-interval', 'n_intervals'),
             Input('risk-refresh-btn', 'n_clicks'),
             Input('recalculate-risk-btn', 'n_clicks')]
        )
        def update_risk_data(config, n_intervals, refresh_clicks, recalc_clicks):
            """Actualiza datos de análisis de riesgo"""
            try:
                risk_data = self._calculate_risk_metrics(config)
                correlation_data = self._calculate_correlations()
                exposure_data = self._calculate_exposures()
                
                self.update_page_stats()
                
                return {
                    'risk_metrics': risk_data,
                    'correlations': correlation_data,
                    'exposures': exposure_data,
                    'config': config,
                    'last_update': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de riesgo: {e}")
                return {}
        
        # Callback para alertas de riesgo
        @app.callback(
            Output('risk-alerts-container', 'children'),
            [Input('risk-data-store', 'data')]
        )
        def update_risk_alerts(risk_data):
            """Actualiza alertas de riesgo"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return html.Div()
                
                return self._create_risk_alerts(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear alertas de riesgo: {e}")
                return html.Div()
        
        # Callback para dashboard de riesgo
        @app.callback(
            Output('risk-dashboard-cards', 'children'),
            [Input('risk-data-store', 'data')]
        )
        def update_risk_dashboard(risk_data):
            """Actualiza dashboard principal de riesgo"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return self.create_empty_state(
                        title="Calculando métricas de riesgo...",
                        message="Procesando datos para análisis de riesgo",
                        icon="fas fa-calculator"
                    )
                
                return self._create_risk_dashboard_cards(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear dashboard de riesgo: {e}")
                return self.create_error_alert("Error al calcular métricas de riesgo")
        
        # Callback para análisis de VaR
        @app.callback(
            Output('var-analysis-chart', 'figure'),
            [Input('risk-data-store', 'data')]
        )
        def update_var_analysis(risk_data):
            """Actualiza análisis de VaR"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return self._create_empty_chart("Calculando VaR...")
                
                return self._create_var_analysis_chart(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de VaR: {e}")
                return self._create_empty_chart("Error en análisis de VaR")
        
        # Callback para monitor de límites
        @app.callback(
            Output('risk-limits-container', 'children'),
            [Input('risk-data-store', 'data')]
        )
        def update_risk_limits_monitor(risk_data):
            """Actualiza monitor de límites de riesgo"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return html.P("Cargando límites de riesgo...", className="text-muted")
                
                return self._create_risk_limits_monitor(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear monitor de límites: {e}")
                return self.create_error_alert("Error en monitor de límites")
        
        # Callback para matriz de correlaciones
        @app.callback(
            Output('correlation-matrix-chart', 'figure'),
            [Input('risk-data-store', 'data')]
        )
        def update_correlation_matrix(risk_data):
            """Actualiza matriz de correlaciones"""
            try:
                if not risk_data or not risk_data.get('correlations'):
                    return self._create_empty_chart("Calculando correlaciones...")
                
                return self._create_correlation_heatmap(risk_data['correlations'])
                
            except Exception as e:
                logger.error(f"Error al crear matriz de correlaciones: {e}")
                return self._create_empty_chart("Error en matriz de correlaciones")
        
        # Callback para análisis de exposiciones
        @app.callback(
            Output('exposure-analysis-chart', 'figure'),
            [Input('risk-data-store', 'data')]
        )
        def update_exposure_analysis(risk_data):
            """Actualiza análisis de exposiciones"""
            try:
                if not risk_data or not risk_data.get('exposures'):
                    return self._create_empty_chart("Calculando exposiciones...")
                
                return self._create_exposure_chart(risk_data['exposures'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de exposiciones: {e}")
                return self._create_empty_chart("Error en análisis de exposiciones")
        
        # Callback para stress testing
        @app.callback(
            [Output('stress-test-chart', 'figure'),
             Output('stress-test-summary', 'children')],
            [Input('risk-data-store', 'data'),
             Input('stress-scenario-selector', 'value')]
        )
        def update_stress_testing(risk_data, scenario):
            """Actualiza análisis de stress testing"""
            try:
                if not risk_data or not scenario:
                    return (
                        self._create_empty_chart("Seleccione un escenario..."),
                        html.P("Configurando stress test...", className="text-muted")
                    )
                
                stress_results = self._run_stress_test(risk_data, scenario)
                chart = self._create_stress_test_chart(stress_results, scenario)
                summary = self._create_stress_test_summary(stress_results, scenario)
                
                return chart, summary
                
            except Exception as e:
                logger.error(f"Error en stress testing: {e}")
                return (
                    self._create_empty_chart("Error en stress test"),
                    self.create_error_alert("Error en stress testing")
                )
        
        # Callback para Monte Carlo
        @app.callback(
            [Output('monte-carlo-chart', 'figure'),
             Output('monte-carlo-statistics', 'children')],
            [Input('run-monte-carlo-btn', 'n_clicks'),
             Input('risk-data-store', 'data')],
            [State('monte-carlo-simulations', 'value')]
        )
        def update_monte_carlo(n_clicks, risk_data, num_simulations):
            """Actualiza simulación Monte Carlo"""
            try:
                if not n_clicks or not risk_data:
                    return (
                        self._create_empty_chart("Presione 'Ejecutar' para iniciar simulación"),
                        html.P("Listo para ejecutar Monte Carlo", className="text-muted")
                    )
                
                mc_results = self._run_monte_carlo_simulation(risk_data, num_simulations or 10000)
                chart = self._create_monte_carlo_chart(mc_results)
                stats = self._create_monte_carlo_statistics(mc_results)
                
                return chart, stats
                
            except Exception as e:
                logger.error(f"Error en Monte Carlo: {e}")
                return (
                    self._create_empty_chart("Error en simulación"),
                    self.create_error_alert("Error en Monte Carlo")
                )
        
        logger.info("Callbacks de RiskAnalysisPage registrados")
    
    def _calculate_risk_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula métricas de riesgo según configuración"""
        try:
            confidence_level = config.get('confidence_level', 0.95)
            time_horizon = config.get('time_horizon', 1)
            
            # Obtener datos de portfolio si disponible
            if self.data_provider:
                symbols = self.data_provider.get_configured_symbols()
                portfolio_data = {}
                
                for symbol in symbols:
                    metrics = self.data_provider.get_symbol_metrics(symbol)
                    if metrics:
                        portfolio_data[symbol] = metrics
            else:
                # Datos simulados
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
                portfolio_data = self._generate_sample_portfolio_data(symbols)
            
            # Calcular métricas de riesgo
            risk_metrics = {}
            
            # VaR del portfolio
            portfolio_returns = self._simulate_portfolio_returns(portfolio_data, 252)
            var_value = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
            cvar_value = np.mean(portfolio_returns[portfolio_returns <= var_value])
            
            risk_metrics['portfolio_var'] = {
                'value': abs(var_value),
                'confidence': confidence_level,
                'horizon_days': time_horizon,
                'currency_value': abs(var_value) * 10000  # Asumir $10k portfolio
            }
            
            risk_metrics['portfolio_cvar'] = {
                'value': abs(cvar_value),
                'confidence': confidence_level,
                'currency_value': abs(cvar_value) * 10000
            }
            
            # Volatilidad del portfolio
            portfolio_volatility = np.std(portfolio_returns) * np.sqrt(252)
            risk_metrics['portfolio_volatility'] = {
                'annualized': portfolio_volatility,
                'daily': np.std(portfolio_returns)
            }
            
            # Máximo drawdown simulado
            cumulative_returns = np.cumprod(1 + portfolio_returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (running_max - cumulative_returns) / running_max
            max_drawdown = np.max(drawdowns)
            
            risk_metrics['max_drawdown'] = {
                'value': max_drawdown,
                'current_drawdown': drawdowns[-1]
            }
            
            # Métricas por símbolo
            risk_metrics['symbols'] = {}
            for symbol, data in portfolio_data.items():
                symbol_returns = np.random.normal(0.001, 0.02, 252)
                symbol_var = np.percentile(symbol_returns, (1 - confidence_level) * 100)
                symbol_cvar = np.mean(symbol_returns[symbol_returns <= symbol_var])

                risk_metrics['symbols'][symbol] = {
                    'var': abs(symbol_var),
                    'cvar': abs(symbol_cvar),
                    'volatility_annualized': float(np.std(symbol_returns) * np.sqrt(252)),
                    'volatility_daily': float(np.std(symbol_returns)),
                    'exposure_pct': float(np.random.uniform(5, 35)),
                    'current_drawdown': float(np.random.uniform(0, 0.2))
                }

            # Correlaciones simuladas entre símbolos
            corr_symbols = list(risk_metrics['symbols'].keys())
            corr_matrix = np.eye(len(corr_symbols))
            for i in range(len(corr_symbols)):
                for j in range(i + 1, len(corr_symbols)):
                    val = float(np.clip(np.random.normal(0.5, 0.2), -1.0, 1.0))
                    corr_matrix[i, j] = val
                    corr_matrix[j, i] = val

            correlations = {
                'symbols': corr_symbols,
                'matrix': corr_matrix.tolist(),
                'avg': float(np.mean(corr_matrix[np.triu_indices(len(corr_symbols), 1)])),
                'max': float(np.max(corr_matrix[np.triu_indices(len(corr_symbols), 1)])),
                'min': float(np.min(corr_matrix[np.triu_indices(len(corr_symbols), 1)]))
            }

            # Exposición por símbolo y total
            exposures = {
                'symbols': corr_symbols,
                'exposure_pct': [risk_metrics['symbols'][s]['exposure_pct'] for s in corr_symbols],
                'limits': {
                    'per_symbol_max_pct': 20.0,
                    'total_risk_limit_pct': 100.0
                }
            }

            # Límite y estado de riesgo agregados
            risk_limits = {
                'thresholds': {
                    'portfolio_var_pct_limit': 0.05,
                    'max_drawdown_limit_pct': 0.15,
                    'per_symbol_concentration_pct': 0.20,
                    'high_correlation_threshold': 0.80
                },
                'current': {
                    'portfolio_var_pct': float(risk_metrics['portfolio_var']['value']),
                    'max_drawdown_pct': float(risk_metrics['max_drawdown']['value']),
                    'max_symbol_concentration_pct': float(max(exposures['exposure_pct'])),
                    'correlation_avg': correlations['avg']
                }
            }

            return {
                'risk_metrics': risk_metrics,
                'correlations': correlations,
                'exposures': exposures,
                'risk_limits': risk_limits
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")
            return {}

    def _simulate_portfolio_returns(self, portfolio_data: Dict[str, Any], periods: int) -> np.ndarray:
        """Simula retornos del portfolio asumiendo pesos iguales."""
        try:
            symbols = list(portfolio_data.keys())
            if not symbols:
                return np.random.normal(0.0005, 0.01, periods)

            weights = np.ones(len(symbols)) / len(symbols)
            returns_matrix = []
            for _ in symbols:
                returns_matrix.append(np.random.normal(0.0005, 0.01, periods))
            returns_matrix = np.vstack(returns_matrix).T  # shape: (periods, symbols)
            portfolio_returns = returns_matrix @ weights
            return portfolio_returns
        except Exception:
            return np.random.normal(0.0005, 0.01, periods)

    def _create_correlation_heatmap(self, correlations: Dict[str, Any]):
        """Crea heatmap de correlaciones."""
        try:
            import plotly.graph_objects as go
            symbols = correlations.get('symbols', [])
            matrix = correlations.get('matrix', [])
            fig = go.Figure(data=go.Heatmap(
                z=matrix,
                x=symbols,
                y=symbols,
                zmin=-1,
                zmax=1,
                colorscale=[[0, '#f85149'], [0.5, '#21262d'], [1, '#3fb950']]
            ))
            fig.update_layout(margin=dict(l=40, r=10, t=20, b=40))
            return fig
        except Exception as e:
            logger.error(f"Error creando heatmap: {e}")
            return self._create_empty_chart("Error en correlaciones")

    def _create_exposure_chart(self, exposures: Dict[str, Any]):
        """Crea gráfico de barras de exposición por símbolo con límite."""
        try:
            import plotly.graph_objects as go
            symbols = exposures.get('symbols', [])
            values = exposures.get('exposure_pct', [])
            limit = exposures.get('limits', {}).get('per_symbol_max_pct', 20)

            fig = go.Figure()
            fig.add_bar(x=symbols, y=values, name='Exposure %')
            fig.add_hline(y=limit, line_dash='dash', line_color='#d29922', annotation_text='Limit')
            fig.update_layout(margin=dict(l=40, r=10, t=20, b=40))
            return fig
        except Exception as e:
            logger.error(f"Error creando exposición: {e}")
            return self._create_empty_chart("Error en exposición")

    def _run_stress_test(self, risk_data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Ejecuta un stress test simple por escenario."""
        try:
            symbols = risk_data.get('exposures', {}).get('symbols', []) or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
            base_values = np.array([100.0 for _ in symbols])

            scenario_impacts = {
                'market_crash': -0.20,
                'flash_crash': -0.10,
                'vol_spike': -0.05,
                'liquidity_crisis': -0.07,
                'correlation_breakdown': -0.08,
                'black_swan': -0.50
            }
            impact = scenario_impacts.get(scenario, -0.05)
            impacted = base_values * (1 + impact + np.random.normal(0, 0.01, len(symbols)))

            return {
                'symbols': symbols,
                'base': base_values.tolist(),
                'scenario': scenario,
                'impacted': impacted.tolist(),
                'impact_pct': float(impact)
            }
        except Exception as e:
            logger.error(f"Error ejecutando stress test: {e}")
            return {}

    def _create_stress_test_chart(self, stress_results: Dict[str, Any], scenario: str):
        """Crea gráfico del stress test por símbolo."""
        try:
            import plotly.graph_objects as go
            symbols = stress_results.get('symbols', [])
            base = stress_results.get('base', [])
            impacted = stress_results.get('impacted', [])
            fig = go.Figure()
            fig.add_bar(x=symbols, y=base, name='Base')
            fig.add_bar(x=symbols, y=impacted, name='Scenario')
            fig.update_layout(barmode='group', title=f"Stress Test: {scenario}", margin=dict(l=40, r=10, t=30, b=40))
            return fig
        except Exception as e:
            logger.error(f"Error creando gráfico de stress: {e}")
            return self._create_empty_chart("Error en stress chart")

    def _create_stress_test_summary(self, stress_results: Dict[str, Any], scenario: str):
        """Crea resumen textual del stress test."""
        from dash import html
        try:
            base_total = float(np.sum(stress_results.get('base', [])))
            scen_total = float(np.sum(stress_results.get('impacted', [])))
            delta = scen_total - base_total
            delta_pct = (delta / base_total) * 100 if base_total else 0.0
            return html.Div([
                html.Div(f"Escenario: {scenario}"),
                html.Div(f"Impacto total: {delta:+.2f} ({delta_pct:+.2f}%)")
            ])
        except Exception:
            return html.Div("Error generando resumen")

    def _run_monte_carlo_simulation(self, risk_data: Dict[str, Any], num_simulations: int = 10000) -> Dict[str, Any]:
        """Ejecuta simulación Monte Carlo simple del portfolio."""
        try:
            num_simulations = int(max(1000, min(num_simulations, 100000)))
            periods = 252
            mu = 0.0005
            sigma = 0.01
            sims = np.random.normal(mu, sigma, (num_simulations, periods))
            paths = np.cumprod(1 + sims, axis=1)
            final = paths[:, -1]

            percentiles = {
                'p5': float(np.percentile(final, 5)),
                'p25': float(np.percentile(final, 25)),
                'p50': float(np.percentile(final, 50)),
                'p75': float(np.percentile(final, 75)),
                'p95': float(np.percentile(final, 95))
            }

            var_95 = float(np.percentile(final - 1.0, 5))
            es_95 = float(np.mean((final - 1.0)[(final - 1.0) <= var_95]))

            return {
                'paths_sample': paths[:100].tolist(),
                'final_distribution': final.tolist(),
                'percentiles': percentiles,
                'var_95': abs(var_95),
                'es_95': abs(es_95)
            }
        except Exception as e:
            logger.error(f"Error en simulación Monte Carlo: {e}")
            return {}

    def _create_monte_carlo_chart(self, mc_results: Dict[str, Any]):
        """Crea gráfico con paths y distribución final."""
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            paths = mc_results.get('paths_sample', [])
            for p in paths:
                fig.add_scatter(y=p, mode='lines', line=dict(width=1, color='rgba(88,166,255,0.2)'))
            fig.update_layout(title="Monte Carlo - Paths (muestra)", margin=dict(l=40, r=10, t=30, b=40))
            return fig
        except Exception as e:
            logger.error(f"Error creando gráfico MC: {e}")
            return self._create_empty_chart("Error en Monte Carlo chart")

    def _create_monte_carlo_statistics(self, mc_results: Dict[str, Any]):
        """Crea resumen de estadísticas de Monte Carlo."""
        from dash import html
        try:
            p = mc_results.get('percentiles', {})
            var_95 = mc_results.get('var_95', 0.0)
            es_95 = mc_results.get('es_95', 0.0)
            return html.Div([
                html.Div(f"P5: {p.get('p5', 0):.3f}  |  P50: {p.get('p50', 0):.3f}  |  P95: {p.get('p95', 0):.3f}"),
                html.Div(f"VaR 95%: {var_95:.4f}  |  ES 95%: {es_95:.4f}")
            ])
        except Exception:
            return html.Div("Error en estadísticas Monte Carlo")