# 📲 Documentación de Comandos Telegram – Bot Trading v10 Enterprise

Este documento describe los comandos disponibles para controlar el bot de trading vía **Telegram**, organizados por categorías.  
Cada comando está pensado para ofrecer **control total**, **retroalimentación en tiempo real** y **registro persistente** en los archivos del repositorio.

---

## 🎓 Entrenamiento

### `/train_hist` – Entrenamiento cronológico sobre histórico
- **Descripción:**  
  - Recorre **de inicio a fin** los datos históricos de todos los símbolos definidos en `user_settings.yaml`.  
  - Ejecución siempre en **orden cronológico**, con todos los símbolos sincronizados por timestamp.  
  - Cada símbolo opera con su propio agente, en paralelo, pero siempre en el mismo punto temporal.  
  - Si un símbolo no ve oportunidad, no opera, pero sigue sincronizado.  

- **Feedback en Telegram:**  
  - **Mensaje vivo (ediciones):**
    ```
    🔧 TRAIN_HIST – Ciclo 23/120
    Timestamp: 2021-09-15 12:00
    Símbolos: BTC, ETH, SOL, ADA, BNB, DOGE
    Equity: 12,430 USDT | PnL ciclo: +2.8%
    Trades ciclo: 92 (WR: 61.2%)
    Top: BTC (+3.4%) | Bottom: ADA (-1.1%)
    ```
  - **Mensaje final por ciclo:**
    ```
    ✅ TRAIN_HIST – Ciclo 23 finalizado
    Rango: 2021-09-01 → 2021-09-30
    Equity final: 12,430 USDT | PnL: +2.8%
    Trades: 92 (W: 56 | L: 36 | WR: 61.2%)
    Sharpe: 1.15 | Sortino: 1.64 | MaxDD: -2.9%
    Estrategias top: OB_15m_break, RSI_4h_div
    Estrategias descartadas: OB_5m_late
    Guardado: top-500 runs | top-500 estrategias | summary actualizado
    ```

- **Artefactos guardados:**  
  - `models/{SYMBOL}/strategies.json` → mejores 500 estrategias  
  - `models/{SYMBOL}/bad_strategies.json` → peores 500 estrategias  
  - `models/{SYMBOL}/runs.jsonl` → mejores 500 runs  
  - `reports/train_hist_summary.json` → resumen histórico top-500  

---

### `/train_live` – Entrenamiento en vivo (paper trading → futuro real)
- **Descripción:**  
  - Conecta a datos en vivo del exchange.  
  - Opera con **balance ficticio** definido en `user_settings.yaml`.  
  - Aprende en tiempo real comparando sus decisiones con estrategias validadas en histórico.  
  - **Balance 0 → reset + penalización.**  
  - **Balance objetivo → reset + recompensa.**  

- **Feedback en Telegram:**  
  - **Mensaje vivo:**
    ```
    📡 TRAIN_LIVE – Paper trading en curso
    Balance: 978.4 USDT | Objetivo: 2,000 USDT
    PnL: -1.4% | Trades abiertos: 3 | WR: 57.8%
    Sharpe: 1.08 | Sortino: 1.62 | MaxDD: -3.1%
    Estrategia activa: RSI_4h_div
    ```
  - **Eventos clave:**
    - Balance 0:
      ```
      ⚠️ TRAIN_LIVE – Balance agotado
      Reset a 1,000 USDT | Penalización aplicada a estrategia OB_5m_late
      ```
    - Balance objetivo alcanzado:
      ```
      🏆 TRAIN_LIVE – Objetivo logrado
      Balance: 2,015 USDT → Reset a 1,000 USDT
      Estrategia RSI_4h_div recibe recompensa
      ```

- **Futuro (cuando esté habilitado trading real):**  
  - Mostrar entradas de cada operación (precio, qty, TF, estrategia).  
  - Mostrar cierres de operaciones con **PnL exacto incluyendo fees**.  
  - Lectura del **balance real** de la cuenta del exchange.  

- **Artefactos guardados:**  
  - `models/{SYMBOL}/train_metrics.jsonl`  
  - `reports/train_live_summary.json`  

---

## 📥 Gestión de Datos Históricos

### `/download_history`
- **Función:**  
  - Descarga datos históricos para todos los símbolos y TFs (1m, 5m, 15m, 1h, 4h, 1d).  
  - Si no existen, descarga completa.  
  - Si ya existen: audita duplicados, gaps y errores → re-descarga solo lo necesario.  
  - Alinea siempre todos los TFs de cada símbolo.  

- **Resultados:**  
  - Guardado en `data/historical/{SYMBOL}/{TF}.csv`  
  - Log en `logs/download_history.log`  
  - Reporte en `reports/download_history_summary.json`  

---

### `/inspect_history`
- **Función:**  
  - Analiza los históricos ya guardados:  
    - Fecha de inicio y fin de cada TF por símbolo  
    - Nº de filas y cobertura (%)  
    - Duplicados y gaps detectados  
  - Genera reporte en `reports/history_inventory.json`  

---

### `/repair_history`
- **Función:**  
  - Repara históricos existentes: elimina duplicados, rellena gaps con descarga exacta, valida y alinea TFs.  
  - Genera reporte en `reports/alignment/{SYMBOL}_alignment.json`  

---

## 💹 Trading en Vivo

### `/start_trading`
- Inicia sesión de trading en vivo (spot o futuros según `symbols.yaml`).  
- Usa balance inicial y riesgo definidos en `user_settings.yaml` y `risk.yaml`.  
- Guarda operaciones en `logs/trading.log` y `models/{SYMBOL}/runs.jsonl`.  

### `/stop_trading`
- Detiene el trading en vivo de forma segura.  
- Si está habilitado, cierra posiciones abiertas automáticamente.  

---

## 🛠️ Control del Sistema

### `/stop_train`
- Detiene el entrenamiento en curso (histórico o live).  
- Cierra ciclo actual y guarda resultados (top-500).  

### `/reload_config`
- Recarga todos los `.yaml` de la carpeta `config/`.  
- Devuelve en Telegram los cambios aplicados.  

### `/reset_agent`
- Resetea balances ficticios, métricas acumuladas y estrategias provisionales.  

---

## 📊 Monitoreo y Métricas

### `/training_status`
- Muestra estado del entrenamiento: ciclo actual, equity, PnL, trades, símbolos activos.  

### `/status`
- Estado global del sistema: CPU, memoria, disco, procesos activos, uptime.  

### `/metrics`
- Métricas avanzadas: Sharpe, Sortino, Calmar, MaxDD, Profit Factor, WinRate, Avg Trade PnL, uso de leverage.  

### `/strategies`
- Resumen de estrategias:  
  - Top-500 (`strategies.json`)  
  - Peores-500 (`bad_strategies.json`)  
  - Provisionales (`strategies_provisional.jsonl`)  

---

## 📂 Archivos Clave Relacionados

- **Históricos:** `data/historical/{SYMBOL}/{TF}.csv`  
- **Modelos y estrategias:** `models/{SYMBOL}/`  
- **Configuraciones:** `config/*.yaml`  
- **Logs:** `logs/`  
- **Reportes:** `reports/`  

---

## 🌐 Dashboard en Vivo
- Acceso a visualización en tiempo real:  
