#!/usr/bin/env python3
"""
Script de Análisis Rápido de Performance
=======================================

Uso: python scripts/analyze_performance.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.performance_analyzer import PerformanceAnalyzer
from datetime import datetime

def main():
    print("ANÁLISIS DE PERFORMANCE - TRADING BOT v10")
    print("=" * 45)
    
    analyzer = PerformanceAnalyzer()
    
    # Análisis de último mes
    analysis = analyzer.analyze_complete_performance('ADAUSDT', 30)
    
    print("\nRESUMEN GENERAL:")
    overview = analysis.get('overview', {})
    print(f"Total trades: {overview.get('total_trades', 0)}")
    print(f"Win rate: {overview.get('win_rate', 0):.1f}%")
    print(f"Profit factor: {overview.get('profit_factor', 0):.2f}")
    print(f"Total P&L: ${overview.get('total_pnl', 0):.2f}")
    
    print("\nPROBLEMAS DETECTADOS:")
    issues = analysis.get('issues_found', [])
    if issues:
        for i, issue in enumerate(issues[:5], 1):
            print(f"{i}. {issue.description}")
            print(f"   Impacto: {issue.impact}")
            print(f"   Recomendación: {issue.recommendation}")
            print()
    else:
        print("No se detectaron problemas críticos")
    
    print("\nRECOMENDACIONES:")
    recommendations = analysis.get('recommendations', [])
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"{i}. {rec['title']} (Prioridad: {rec['priority']})")
        print(f"   {rec['description']}")
        print()

if __name__ == "__main__":
    main()
