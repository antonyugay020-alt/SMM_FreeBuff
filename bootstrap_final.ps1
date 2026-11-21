# Final bootstrap: all fixes in one file
# Run:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_final.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ""
Write-Host "=== FINAL BOOTSTRAP ===" -ForegroundColor Green

function Write-File {
    param([string]$Path, [string]$Content)
    $fullPath = Join-Path $root $Path
    $dir = Split-Path -Parent $fullPath
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8NoBom)
    Write-Host "  Created: $Path"
}

# ============================================================
# 1. supervisor.py - kill_switch closes positions via exchange
# ============================================================
$supervisorPy = @'
"""
Trader supervisor with kill_switch that closes all positions.
"""

import asyncio
import json
import os
import threading
import time
from pathlib import Path

from loguru import logger

from src.core.control import get_control, set_control

STATUS_PATH = Path("data/status.json")


class TraderSupervisor:
    def __init__(self):
        self.thread = None
        self.trader = None
        self.restarts = 0
        self.started_at = 0.0
        self.running = False
        self._stop = threading.Event()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._watchdog, daemon=True)
        self.thread.start()
        logger.info("Supervisor started")

    def stop(self):
        self.running = False
        self._stop.set()
        if self.trader:
            try:
                self.trader.shutdown()
            except Exception:
                pass

    def _close_all_positions(self):
        """Close all open positions via market orders."""
        try:
            if not (self.trader and hasattr(self.trader, 'adapter') and self.trader.adapter):
                return
            positions = self.trader.adapter.fetch_positions()
            logger.info(f"Found {len(positions)} positions to close")
            for p in positions:
                symbol = p.get("symbol")
                side = p.get("side")
                contracts = float(p.get("contracts") or 0)
                if contracts > 0:
                    close_side = "sell" if side.lower() == "long" else "buy"
                    logger.warning(f"Closing {side} {contracts} {symbol}")
                    try:
                        self.trader.adapter.exchange.create_market_order(
                            symbol=symbol, side=close_side, amount=contracts
                        )
                        logger.info(f"Closed {symbol}")
                        time.sleep(0.3)
                    except Exception as e:
                        logger.error(f"Failed to close {symbol}: {e}")
        except Exception as e:
            logger.error(f"Failed to close positions: {e}")

    def _watchdog(self):
        while self.running and not self._stop.is_set():
            control = get_control()

            if control.get("kill_switch"):
                logger.error("KILL SWITCH: closing all positions and stopping")
                self.running = False
                self._close_all_positions()
                if self.trader:
                    self.trader.shutdown()
                    time.sleep(2)
                self._write_status(running=False, note="kill_switch")
                break

            if control.get("restart_trader"):
                set_control(restart_trader=False)
                if self.trader:
                    self.trader.shutdown()
                    time.sleep(3)

            from src.autonomous import AutonomousTrader
            self.trader = AutonomousTrader()
            self.started_at = time.time()

            threading.Thread(target=self._status_loop, daemon=True).start()

            try:
                self.trader.init_system()
                asyncio.run(self.trader.run_forever())
            except Exception as e:
                logger.error(f"Trader crashed: {e}")

            self.restarts += 1
            logger.warning(f"Trader stopped. Restart #{self.restarts} in 5s")
            self._write_status(running=False, note="restarting")
            time.sleep(5)

    def _status_loop(self):
        while self.trader and self.trader.running and not self._stop.is_set():
            self._write_status(running=True)
            time.sleep(3)

    def _write_status(self, running: bool, note: str = ""):
        try:
            cycles = self.trader.cycle_count if self.trader else 0
            data = {
                "running": running,
                "note": note,
                "pid": os.getpid(),
                "restarts": self.restarts,
                "cycles": cycles,
                "uptime_sec": round(time.time() - self.started_at, 1) if self.started_at else 0,
                "updated": time.time(),
            }
            STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATUS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
'@

Write-File "src/core/supervisor.py" $supervisorPy

# ============================================================
# 2. autonomous.py - full file with flag checks + emergency close
# ============================================================
$autonomousPy = @'
"""
Autonomous trading main loop (final).
Checks control flags before every expensive operation.
"""

import asyncio
import signal
import time
from typing import Dict, List

from loguru import logger

from src.ai.decision_engine import AIDecisionEngine
from src.ai.llm_client import LLMClient
from src.ai.proactive_scanner import ProactiveScanner
from src.ai.regime_detector import RegimeDetector, RegimeInfo
from src.core.control import get_control
from src.data.market_data_collector import MarketDataCollector
from src.data.news_collector import NewsCollector
from src.data.universe_builder import UniverseBuilder
from src.execution.bybit_demo_adapter import BybitDemoAdapter
from src.execution.order_manager import OrderManager
from src.learning.engine import LearningEngine
from src.monitoring.telegram import TelegramNotifier
from src.risk.risk_engine import RiskEngine
from src.storage.database import TradeDatabase
from src.strategies.mean_reversion import MeanReversion
from src.strategies.momentum_breakout import MomentumBreakout
from src.strategies.signal import Signal
from src.strategies.signal_aggregator import SignalAggregator
from src.strategies.trend_follow import TrendFollow


class AutonomousTrader:
    def __init__(self):
        self.running = True
        self.cycle_count = 0
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_daily_summary = time.time()
        self.news_every = 5
        self.scan_every = 5
        self.adapter: BybitDemoAdapter = None
        self.collector: MarketDataCollector = None
        self.order_manager: OrderManager = None

    def _emergency_close_all(self) -> None:
        """Close all open positions via market orders."""
        logger.warning("EMERGENCY: closing all positions")
        try:
            if not self.adapter:
                return
            positions = self.adapter.fetch_positions()
            logger.info(f"Found {len(positions)} positions to close")
            for p in positions:
                symbol = p.get("symbol")
                side = p.get("side")
                contracts = float(p.get("contracts") or 0)
                if contracts > 0:
                    close_side = "sell" if side.lower() == "long" else "buy"
                    logger.warning(f"Closing {side} {contracts} {symbol}")
                    try:
                        self.adapter.exchange.create_market_order(
                            symbol=symbol, side=close_side, amount=contracts
                        )
                        logger.info(f"Closed {symbol}")
                        time.sleep(0.3)
                    except Exception as e:
                        logger.error(f"Failed to close {symbol}: {e}")
        except Exception as e:
            logger.error(f"Emergency close failed: {e}")

    def _check_control_flags(self) -> bool:
        """Check control flags. Returns True if should continue, False if should stop."""
        control = get_control()
        if control.get("kill_switch"):
            logger.error("KILL SWITCH: closing all positions and stopping")
            self._emergency_close_all()
            self.shutdown()
            return False
        if control.get("stop_trading"):
            logger.info("Stop trading flag set, skipping cycle")
            return False
        if control.get("paused"):
            logger.info("Paused, skipping cycle")
            return False
        if control.get("restart_trader"):
            logger.warning("Restart requested")
            self.shutdown()
            return False
        return True

    def init_system(self):
        logger.info("Initializing autonomous trading system...")

        self.db = TradeDatabase()
        self.notifier = TelegramNotifier()
        self.llm = LLMClient(model="qwen3:8b", temperature=0.2)

        self.adapter = BybitDemoAdapter()
        self.adapter.connect()
        balance = self.adapter.fetch_balance()
        equity = float(balance.get("USDT", {}).get("total", 10000) or 10000)
        logger.info(f"Connected. Equity: {equity:.2f} USDT")

        builder = UniverseBuilder(
            adapter=self.adapter, max_symbols=20,
            min_volume_usdt=5_000_000, oi_fetch_top_n=20,
        )
        universe = builder.build()
        symbols = [i.symbol for i in universe]
        logger.info(f"Universe: {len(symbols)} symbols")

        self.collector = MarketDataCollector(symbols=symbols)
        self.collector.preload_history(self.adapter, timeframe="1m", limit=200)

        strategies = [
            MomentumBreakout(lookback=15, volume_multiplier=1.8),
            MeanReversion(lookback=20, std_multiplier=2.0),
            TrendFollow(fast_period=9, slow_period=21),
        ]
        self.aggregator = SignalAggregator(strategies)

        self.regime_detector = RegimeDetector()
        self.news = NewsCollector(self.llm, refresh_sec=300)
        self.scanner = ProactiveScanner(self.llm, min_confidence=0.65, max_ideas=2)

        self.ai_engine = AIDecisionEngine(model="qwen3:8b", temperature=0.2)
        self.risk_engine = RiskEngine(
            equity=equity, max_risk_per_trade_pct=0.5,
            max_total_open_risk_pct=2.5, max_positions=50, default_leverage=5,
        )
        self.order_manager = OrderManager(self.adapter)
        self.learning = LearningEngine(self.db)
        logger.info(f"Strategy weights: {self.learning.get_strategy_weights()}")

        try:
            self.news.refresh(force=True)
        except Exception as e:
            logger.warning(f"Initial news refresh failed: {e}")

    def _publish_portfolio(self) -> None:
        """Write portfolio snapshot for GUI."""
        import json as _json
        from pathlib import Path as _Path
        try:
            balance = self.adapter.fetch_balance()
            usdt = balance.get("USDT", {}) or {}
            positions = self.order_manager.get_positions()
            pos_list = []
            for p in positions:
                pos_list.append({
                    "symbol": p.get("symbol"),
                    "side": p.get("side"),
                    "contracts": float(p.get("contracts") or 0),
                    "entry_price": float(p.get("entryPrice") or 0),
                    "mark_price": float(p.get("markPrice") or 0),
                    "unrealized_pnl": float(p.get("unrealizedPnl") or 0),
                    "leverage": p.get("leverage"),
                    "stop_loss": p.get("stopLoss"),
                    "take_profit": p.get("takeProfit"),
                })
            data = {
                "total": float(usdt.get("total") or 0),
                "free": float(usdt.get("free") or 0),
                "used": float(usdt.get("used") or 0),
                "unrealized_pnl": sum(p["unrealized_pnl"] for p in pos_list),
                "positions": pos_list,
                "updated": time.time(),
            }
            out = _Path("data/portfolio.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(_json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"publish_portfolio error: {e}")

    async def run_cycle(self):
        if not self._check_control_flags():
            return

        self.cycle_count += 1

        # Regimes
        regimes: Dict[str, RegimeInfo] = {}
        for symbol in list(self.collector.states.keys())[:10]:
            state = self.collector.states[symbol]
            reg = self.regime_detector.detect(symbol, state)
            if reg:
                regimes[symbol] = reg
        global_regime = self.regime_detector.detect_global(regimes)

        # News
        if self.cycle_count % self.news_every == 1:
            try:
                self.news.refresh()
            except Exception as e:
                logger.warning(f"News refresh failed: {e}")
        news_context = self.news.get_context()

        # Extra context for judge
        reg_lines = [f"{s}: {r.regime} (eff={r.efficiency}, atr%={r.atr_pct})" for s, r in regimes.items()]
        extra = (
            f"Global regime: {global_regime}\n"
            "Per-symbol regimes:\n" + "\n".join(reg_lines) +
            "\nNews:\n" + news_context
        )
        self.ai_engine.extra_context = extra

        # Strategy signals
        signals: List[Signal] = self.aggregator.collect_signals(self.collector)
        logger.info(
            f"Cycle {self.cycle_count}: {len(signals)} strategy signals | "
            f"global={global_regime.get('regime')}"
        )

        approved_signals: List[Signal] = []
        ai_decisions = []
        if signals:
            ai_decisions = self.ai_engine.analyze_signals(signals, self.collector)
            approved_signals = [
                d["signal"] for d in ai_decisions
                if d["decision"] in ("approve", "reduce")
            ]

        # Proactive AI scan
        proactive_ideas: List[Signal] = []
        if self.cycle_count % self.scan_every == 0:
            proactive_ideas = self.scanner.scan(
                self.collector, regimes, news_context, global_regime
            )
            approved_signals.extend(proactive_ideas)

        # Risk + execution
        trades = []
        proposals = []
        if approved_signals:
            proposals = self.risk_engine.evaluate_batch(approved_signals)
            for p in [p for p in proposals if p.approved]:
                record = self.order_manager.execute_proposal(p)
                if record:
                    trades.append(record)
                    self.db.save_trade({
                        "symbol": record.symbol,
                        "side": record.side,
                        "strategy_id": record.strategy_id,
                        "entry_price": record.entry_price,
                        "amount": record.amount,
                        "leverage": record.leverage,
                        "stop_loss": record.stop_loss,
                        "take_profit": record.take_profit,
                        "opened_at": record.opened_at,
                        "status": "open",
                    })
                    if self.notifier.enabled:
                        self.notifier.trade_opened(
                            record.symbol, record.side, record.amount,
                            record.entry_price, record.leverage,
                            record.stop_loss, record.take_profit,
                        )

        # Signal journal
        executed_symbols = {t.symbol for t in trades}
        approved_ids = {id(p.signal) for p in proposals if p.approved}
        for d in ai_decisions:
            sig = d["signal"]
            self.db.save_signal({
                "strategy_id": sig.strategy_id,
                "symbol": sig.symbol,
                "side": sig.side.value,
                "strength": sig.strength,
                "confidence": sig.confidence,
                "ai_decision": d["decision"],
                "ai_score": d["ai_score"],
                "risk_approved": id(sig) in approved_ids,
                "executed": id(sig) in approved_ids and sig.symbol in executed_symbols,
            })
        for sig in proactive_ideas:
            self.db.save_signal({
                "strategy_id": sig.strategy_id,
                "symbol": sig.symbol,
                "side": sig.side.value,
                "strength": sig.strength,
                "confidence": sig.confidence,
                "ai_decision": "proactive",
                "ai_score": sig.confidence * 100,
                "risk_approved": id(sig) in approved_ids,
                "executed": sig.symbol in executed_symbols,
            })

        # Closed positions bookkeeping
        await self._check_closed_positions()

        # Publish portfolio for GUI
        try:
            self._publish_portfolio()
        except Exception as e:
            logger.debug(f"Portfolio publish failed: {e}")

    async def _check_closed_positions(self):
        positions = self.order_manager.get_positions()
        active_symbols = {p.get("symbol") for p in positions}
        for symbol, record in list(self.order_manager.active_trades.items()):
            if symbol not in active_symbols:
                try:
                    closed = self.order_manager.close_trade(symbol)
                    if closed:
                        self.daily_pnl += closed.pnl or 0
                        self.daily_trades += 1
                        self.learning.update_after_trade(closed.strategy_id, closed.pnl or 0)
                        self.db.save_trade({
                            "symbol": closed.symbol,
                            "side": closed.side,
                            "strategy_id": closed.strategy_id,
                            "entry_price": closed.entry_price,
                            "amount": closed.amount,
                            "leverage": closed.leverage,
                            "stop_loss": closed.stop_loss,
                            "take_profit": closed.take_profit,
                            "opened_at": closed.opened_at,
                            "closed_at": closed.closed_at,
                            "pnl": closed.pnl,
                            "status": "closed",
                        })
                        if self.notifier.enabled:
                            duration = (closed.closed_at or time.time()) - closed.opened_at
                            self.notifier.trade_closed(closed.symbol, closed.pnl or 0, duration)
                except Exception as e:
                    logger.error(f"Error handling closed position {symbol}: {e}")

    async def run_forever(self):
        logger.info("Starting autonomous loop (60s interval)")
        ws_task = asyncio.create_task(self.collector.run())
        await asyncio.sleep(10)
        try:
            while self.running:
                try:
                    await self.run_cycle()
                except Exception as e:
                    logger.error(f"Cycle error: {e}")

                if time.time() - self.last_daily_summary > 86400:
                    try:
                        balance = self.adapter.fetch_balance()
                        equity = float(balance.get("USDT", {}).get("total", 0) or 0)
                        if self.notifier.enabled:
                            self.notifier.daily_summary(self.daily_trades, self.daily_pnl, equity)
                    except Exception as e:
                        logger.warning(f"Daily summary failed: {e}")
                    self.daily_pnl = 0.0
                    self.daily_trades = 0
                    self.last_daily_summary = time.time()

                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        finally:
            ws_task.cancel()
            try:
                await ws_task
            except asyncio.CancelledError:
                pass

    def shutdown(self):
        logger.warning("Shutdown signal received")
        self.running = False


def main():
    logger.add("logs/trader.log", rotation="10 MB", retention="7 days")
    trader = AutonomousTrader()

    def handler(sig, frame):
        trader.shutdown()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    trader.init_system()
    logger.info("System initialized. Starting autonomous trading...")

    try:
        asyncio.run(trader.run_forever())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    finally:
        if trader.db:
            trader.db.close()
        logger.info("Autonomous trader stopped.")


if __name__ == "__main__":
    main()
'@

Write-File "src/autonomous.py" $autonomousPy

# ============================================================
# 3. native_gui.py - tkinter version (stable)
# ============================================================
$nativeGuiPy = @'
"""
Native desktop GUI for Bybit AI Trader (tkinter).
"""

import json
import sys
import threading
import time
import sqlite3
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.supervisor import TraderSupervisor
from src.core.control import get_control, set_control, reset_control

STATUS_PATH = PROJECT_ROOT / "data/status.json"
PORTFOLIO_PATH = PROJECT_ROOT / "data/portfolio.json"
DB_PATH = PROJECT_ROOT / "data/trader.db"
LOG_PATH = PROJECT_ROOT / "logs/trader.log"


class NativeGUI:
    def __init__(self):
        self.supervisor = TraderSupervisor()
        self.current_view = "status"
        self._stop = threading.Event()
        self._cache: Dict = {}
        self._dirty = False

        self.root = tk.Tk()
        self.root.title("Bybit AI Trader")
        self.root.geometry("1400x860")
        self.root.minsize(1100, 700)

        self.bg = "#1e1e1e"
        self.fg = "#e0e0e0"
        self.accent = "#00c896"
        self.green = "#00c864"
        self.red = "#dc3c3c"
        self.grey = "#a0a0a0"

        self.root.configure(bg=self.bg)

        main_frame = tk.Frame(self.root, bg=self.bg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sidebar = tk.Frame(main_frame, bg=self.bg, width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(sidebar, text="Bybit AI Trader", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(pady=10)
        tk.Frame(sidebar, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(sidebar, text="STOPPED", fg=self.red, bg=self.bg, font=("Arial", 12, "bold"))
        self.status_label.pack(pady=10)

        views = [("Status", "status"), ("Trades", "trades"), ("AI Signals", "ai"),
                 ("Strategies", "strategies"), ("System", "system"), ("Logs", "logs")]
        for label, view in views:
            btn = tk.Button(sidebar, text=f"  {label}", bg="#2a2a2a", fg=self.fg,
                          activebackground="#3a3a3a", activeforeground=self.fg,
                          font=("Arial", 11), width=20, height=2,
                          command=lambda v=view: self.switch_view(v))
            btn.pack(pady=2)

        tk.Frame(sidebar, height=1, bg=self.grey).pack(fill=tk.X, pady=10)
        tk.Label(sidebar, text="Controls", fg=self.grey, bg=self.bg, font=("Arial", 10)).pack(pady=5)

        tk.Button(sidebar, text="  Resume", bg="#2a2a2a", fg=self.fg,
                 activebackground="#3a3a3a", width=20, height=1,
                 command=self.on_resume).pack(pady=2)
        tk.Button(sidebar, text="  Pause", bg="#2a2a2a", fg=self.fg,
                 activebackground="#3a3a3a", width=20, height=1,
                 command=self.on_pause).pack(pady=2)
        tk.Button(sidebar, text="  Stop trading", bg="#2a2a2a", fg=self.fg,
                 activebackground="#3a3a3a", width=20, height=1,
                 command=self.on_stop).pack(pady=2)
        tk.Button(sidebar, text="  Kill switch", bg="#2a2a2a", fg=self.fg,
                 activebackground="#3a3a3a", width=20, height=1,
                 command=self.on_kill).pack(pady=2)
        tk.Button(sidebar, text="  Restart trader", bg="#2a2a2a", fg=self.fg,
                 activebackground="#3a3a3a", width=20, height=1,
                 command=self.on_restart).pack(pady=2)
        tk.Button(sidebar, text="  Exit application", bg="#2a2a2a", fg=self.fg,
                 activebackground="#3a3a3a", width=20, height=1,
                 command=self.request_exit).pack(pady=10)

        self.content_frame = tk.Frame(main_frame, bg=self.bg)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.views = {}
        self.views["status"] = self._build_status_view()
        self.views["trades"] = self._build_trades_view()
        self.views["ai"] = self._build_ai_view()
        self.views["strategies"] = self._build_strategies_view()
        self.views["system"] = self._build_system_view()
        self.views["logs"] = self._build_logs_view()

        self.switch_view("status")

    def _build_status_view(self):
        frame = tk.Frame(self.content_frame, bg=self.bg)
        tk.Label(frame, text="Portfolio", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        tk.Frame(frame, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        metrics_frame = tk.Frame(frame, bg=self.bg)
        metrics_frame.pack(fill=tk.X, pady=10)

        self.metrics = {}
        for i, (title, key) in enumerate([("Total Balance", "m_total"), ("Available", "m_free"),
                                           ("In Margin", "m_used"), ("Unrealized PnL", "m_upnl"),
                                           ("Realized PnL", "m_rpnl"), ("Open Positions", "m_pos")]):
            card = tk.Frame(metrics_frame, bg="#2a2a2a", relief=tk.RAISED, bd=1)
            card.grid(row=0, column=i, padx=5, pady=5, sticky=tk.NSEW)
            tk.Label(card, text=title, fg=self.grey, bg="#2a2a2a", font=("Arial", 9)).pack(pady=5)
            self.metrics[key] = tk.Label(card, text="0.00", fg=self.fg, bg="#2a2a2a", font=("Arial", 12, "bold"))
            self.metrics[key].pack(pady=5)

        tk.Label(frame, text="Open Positions (live)", fg=self.accent, bg=self.bg, font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        pos_frame = tk.Frame(frame, bg=self.bg)
        pos_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.pos_tree = ttk.Treeview(pos_frame, columns=("Symbol", "Side", "Size", "Entry", "Mark", "uPnL", "Lev", "Stop Loss", "Take Profit"),
                                     show="headings", height=10)
        for col in ("Symbol", "Side", "Size", "Entry", "Mark", "uPnL", "Lev", "Stop Loss", "Take Profit"):
            self.pos_tree.heading(col, text=col)
            self.pos_tree.column(col, width=100, anchor=tk.CENTER)
        self.pos_tree.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Recent Closed Trades", fg=self.accent, bg=self.bg, font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        closed_frame = tk.Frame(frame, bg=self.bg)
        closed_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.closed_tree = ttk.Treeview(closed_frame, columns=("Closed At", "Symbol", "Side", "Strategy", "Entry", "PnL"),
                                        show="headings", height=6)
        for col in ("Closed At", "Symbol", "Side", "Strategy", "Entry", "PnL"):
            self.closed_tree.heading(col, text=col)
            self.closed_tree.column(col, width=120, anchor=tk.CENTER)
        self.closed_tree.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Activity", fg=self.accent, bg=self.bg, font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        self.activity_text = scrolledtext.ScrolledText(frame, bg="#2a2a2a", fg=self.fg, font=("Consolas", 9), height=6, wrap=tk.WORD)
        self.activity_text.pack(fill=tk.BOTH, expand=True, pady=5)

        return frame

    def _build_trades_view(self):
        frame = tk.Frame(self.content_frame, bg=self.bg)
        tk.Label(frame, text="All Trades", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        tk.Frame(frame, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        self.trades_tree = ttk.Treeview(frame, columns=("Symbol", "Side", "Strategy", "Entry", "Size", "Lev", "PnL", "Status"),
                                        show="headings", height=20)
        for col in ("Symbol", "Side", "Strategy", "Entry", "Size", "Lev", "PnL", "Status"):
            self.trades_tree.heading(col, text=col)
            self.trades_tree.column(col, width=120, anchor=tk.CENTER)
        self.trades_tree.pack(fill=tk.BOTH, expand=True, pady=10)

        return frame

    def _build_ai_view(self):
        frame = tk.Frame(self.content_frame, bg=self.bg)
        tk.Label(frame, text="AI Signals", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        tk.Frame(frame, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        self.ai_tree = ttk.Treeview(frame, columns=("Time", "Symbol", "Strategy", "Side", "Conf", "AI Score", "Decision", "Executed"),
                                    show="headings", height=20)
        for col in ("Time", "Symbol", "Strategy", "Side", "Conf", "AI Score", "Decision", "Executed"):
            self.ai_tree.heading(col, text=col)
            self.ai_tree.column(col, width=100, anchor=tk.CENTER)
        self.ai_tree.pack(fill=tk.BOTH, expand=True, pady=10)

        return frame

    def _build_strategies_view(self):
        frame = tk.Frame(self.content_frame, bg=self.bg)
        tk.Label(frame, text="Strategies Performance", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        tk.Frame(frame, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        self.strategies_tree = ttk.Treeview(frame, columns=("Strategy", "Trades", "Wins", "Losses", "Winrate %", "Total PnL", "Weight"),
                                            show="headings", height=15)
        for col in ("Strategy", "Trades", "Wins", "Losses", "Winrate %", "Total PnL", "Weight"):
            self.strategies_tree.heading(col, text=col)
            self.strategies_tree.column(col, width=100, anchor=tk.CENTER)
        self.strategies_tree.pack(fill=tk.BOTH, expand=True, pady=10)

        return frame

    def _build_system_view(self):
        frame = tk.Frame(self.content_frame, bg=self.bg)
        tk.Label(frame, text="System", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        tk.Frame(frame, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        self.system_text = scrolledtext.ScrolledText(frame, bg="#2a2a2a", fg=self.fg, font=("Consolas", 10), wrap=tk.WORD)
        self.system_text.pack(fill=tk.BOTH, expand=True, pady=10)

        return frame

    def _build_logs_view(self):
        frame = tk.Frame(self.content_frame, bg=self.bg)
        tk.Label(frame, text="Logs (last 100 lines)", fg=self.accent, bg=self.bg, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        tk.Frame(frame, height=1, bg=self.grey).pack(fill=tk.X, pady=5)

        self.logs_text = scrolledtext.ScrolledText(frame, bg="#2a2a2a", fg=self.fg, font=("Consolas", 9), wrap=tk.WORD)
        self.logs_text.pack(fill=tk.BOTH, expand=True, pady=10)

        return frame

    def switch_view(self, view):
        self.current_view = view
        for v, frame in self.views.items():
            if v == view:
                frame.pack(fill=tk.BOTH, expand=True)
            else:
                frame.pack_forget()
        self._refresh_current()

    def _refresh_current(self):
        try:
            if self.current_view == "status":
                self._refresh_status()
            elif self.current_view == "trades":
                self._refresh_trades()
            elif self.current_view == "ai":
                self._refresh_ai()
            elif self.current_view == "strategies":
                self._refresh_strategies()
            elif self.current_view == "system":
                self._refresh_system()
            elif self.current_view == "logs":
                self._refresh_logs()
        except Exception as e:
            logger.exception(f"refresh error for {self.current_view}")

    def _refresh_status(self):
        st = self._cache.get("status", {}) or {}
        pf = self._cache.get("portfolio", {}) or {}
        realized = self._cache.get("realized", 0.0)

        if st.get("running"):
            self.status_label.config(text="RUNNING", fg=self.green)
        else:
            self.status_label.config(text="STOPPED", fg=self.red)

        def setm(key, value, color=None):
            if key in self.metrics:
                self.metrics[key].config(text=value)
                if color:
                    self.metrics[key].config(fg=color)

        setm("m_total", f"{pf.get('total', 0):,.2f}", self.fg)
        setm("m_free", f"{pf.get('free', 0):,.2f}", self.fg)
        setm("m_used", f"{pf.get('used', 0):,.2f}", self.fg)
        upnl = pf.get("unrealized_pnl", 0)
        setm("m_upnl", f"{upnl:+,.2f}", self.green if upnl >= 0 else self.red)
        setm("m_rpnl", f"{realized:+,.2f}", self.green if realized >= 0 else self.red)
        positions = pf.get("positions", [])
        setm("m_pos", str(len(positions)), self.fg)

        for item in self.pos_tree.get_children():
            self.pos_tree.delete(item)
        for pos in positions:
            side = str(pos.get("side", ""))
            u = pos.get("unrealized_pnl", 0)
            sl = pos.get("stop_loss")
            tp = pos.get("take_profit")
            self.pos_tree.insert("", tk.END, values=(
                pos.get("symbol", ""), side.upper(),
                f"{pos.get('contracts', 0):g}",
                f"{pos.get('entry_price', 0):,.4f}",
                f"{pos.get('mark_price', 0):,.4f}",
                f"{u:+,.4f}",
                f"{pos.get('leverage') or '-'}x",
                f"{sl:,.4f}" if sl else "-",
                f"{tp:,.4f}" if tp else "-"
            ))

        for item in self.closed_tree.get_children():
            self.closed_tree.delete(item)
        closed = [t for t in self._load_trades() if t.get("status") == "closed"][:8]
        for t in closed:
            ca = t.get("closed_at")
            pnl = t.get("pnl") or 0
            self.closed_tree.insert("", tk.END, values=(
                datetime.fromtimestamp(ca).strftime("%m-%d %H:%M:%S") if ca else "-",
                t.get("symbol", ""), t.get("side", "").upper(),
                t.get("strategy_id", ""),
                f"{t.get('entry_price', 0):,.4f}",
                f"{pnl:+,.4f}"
            ))

        self.activity_text.delete(1.0, tk.END)
        self.activity_text.insert(tk.END, "".join(self._cache.get("logs", [])))

    def _refresh_trades(self):
        for item in self.trades_tree.get_children():
            self.trades_tree.delete(item)
        for t in self._load_trades()[:200]:
            pnl = t.get("pnl")
            stt = str(t.get("status", ""))
            self.trades_tree.insert("", tk.END, values=(
                t.get("symbol", ""), t.get("side", "").upper(),
                t.get("strategy_id", ""),
                f"{t.get('entry_price', 0):,.4f}",
                f"{t.get('amount', 0):g}",
                f"{t.get('leverage', 0)}x",
                f"{pnl:+,.4f}" if pnl is not None else "-",
                stt
            ))

    def _refresh_ai(self):
        for item in self.ai_tree.get_children():
            self.ai_tree.delete(item)
        for s in self._load_signals()[:200]:
            ts = s.get("timestamp", 0)
            dec = str(s.get("ai_decision", ""))
            self.ai_tree.insert("", tk.END, values=(
                datetime.fromtimestamp(ts).strftime("%m-%d %H:%M:%S") if ts else "-",
                s.get("symbol", ""), s.get("strategy_id", ""),
                s.get("side", ""),
                f"{float(s.get('confidence') or 0):.2f}",
                f"{float(s.get('ai_score') or 0):.0f}",
                dec or "-",
                "YES" if s.get("executed") else "NO"
            ))

    def _refresh_strategies(self):
        for item in self.strategies_tree.get_children():
            self.strategies_tree.delete(item)
        for st in self._load_strategy_stats():
            pnl = st.get("total_pnl", 0) or 0
            self.strategies_tree.insert("", tk.END, values=(
                st.get("strategy_id", ""),
                st.get("total_trades", 0),
                st.get("wins", 0),
                st.get("losses", 0),
                f"{st.get('winrate', 0):.1f}",
                f"{pnl:+,.2f}",
                f"{st.get('weight', 1.0):.2f}"
            ))

    def _refresh_system(self):
        st = self._cache.get("status", {}) or {}
        control = get_control()
        lines = ["Control flags:"]
        for k, v in control.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("Trader process:")
        lines.append(f"  PID: {st.get('pid')}")
        lines.append(f"  Cycles: {st.get('cycles')}")
        lines.append(f"  Restarts: {st.get('restarts')}")
        lines.append(f"  Uptime: {st.get('uptime_sec', 0) / 60:.1f} min")
        lines.append(f"  Running: {st.get('running')}")
        lines.append("")
        lines.append("Paths:")
        lines.append(f"  DB: {DB_PATH}" + (f" ({DB_PATH.stat().st_size / 1024:.0f} KB)" if DB_PATH.exists() else " (missing)"))
        lines.append(f"  Portfolio: {PORTFOLIO_PATH}" + ("" if PORTFOLIO_PATH.exists() else " (missing)"))
        lines.append(f"  Log: {LOG_PATH}")

        self.system_text.delete(1.0, tk.END)
        self.system_text.insert(tk.END, "\n".join(lines))

    def _refresh_logs(self):
        self.logs_text.delete(1.0, tk.END)
        self.logs_text.insert(tk.END, "".join(self._cache.get("logs_full", [])))

    def on_resume(self):
        reset_control()
        logger.info("Resume requested")

    def on_pause(self):
        set_control(paused=True)
        logger.info("Pause requested")

    def on_stop(self):
        set_control(stop_trading=True)
        logger.info("Stop trading requested")

    def on_kill(self):
        set_control(kill_switch=True)
        logger.info("Kill switch requested")

    def on_restart(self):
        set_control(restart_trader=True)
        logger.info("Restart requested")

    def request_exit(self):
        self._stop.set()
        self.root.quit()

    def _load_portfolio(self):
        try:
            return json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _load_status(self):
        try:
            return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _load_trades(self):
        if not DB_PATH.exists():
            return []
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM trades ORDER BY opened_at DESC LIMIT 300")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def _load_signals(self):
        if not DB_PATH.exists():
            return []
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 300")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def _load_strategy_stats(self):
        if not DB_PATH.exists():
            return []
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM strategy_stats ORDER BY total_pnl DESC")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def _realized_pnl(self):
        if not DB_PATH.exists():
            return 0.0
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE status='closed'")
            val = cur.fetchone()[0]
            conn.close()
            return float(val or 0)
        except Exception:
            return 0.0

    def _load_logs(self, n):
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                return f.readlines()[-n:]
        except Exception:
            return ["Log file not found"]

    def _bg_loop(self):
        while not self._stop.is_set():
            try:
                self._cache = {
                    "status": self._load_status(),
                    "portfolio": self._load_portfolio(),
                    "realized": self._realized_pnl(),
                    "logs": self._load_logs(8),
                    "logs_full": self._load_logs(100),
                }
                self._dirty = True
            except Exception as e:
                logger.debug(f"bg cache error: {e}")
            time.sleep(2)

    def run(self):
        logger.info("Starting native GUI (tkinter)")
        self.supervisor.start()

        threading.Thread(target=self._bg_loop, daemon=True).start()

        def update_loop():
            if self._dirty:
                self._dirty = False
                try:
                    self._refresh_current()
                except Exception as e:
                    logger.debug(f"ui refresh error: {e}")
            self.root.after(100, update_loop)

        update_loop()
        self.root.mainloop()

        logger.info("Shutting down...")
        self.supervisor.stop()


def main():
    logger.add(str(PROJECT_ROOT / "logs" / "trader.log"), rotation="10 MB", retention="7 days")
    gui = NativeGUI()
    try:
        gui.run()
    except KeyboardInterrupt:
        gui.supervisor.stop()
    finally:
        logger.info("Native GUI stopped.")


if __name__ == "__main__":
    main()
'@

Write-File "src/native_gui.py" $nativeGuiPy

# ============================================================
# 4. Install dependencies
# ============================================================
Write-Host ""
Write-Host "=== Installing dependencies ===" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install matplotlib --quiet

Write-Host ""
Write-Host "=== FINAL BOOTSTRAP COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Run:"
Write-Host "  .\START.bat"
Write-Host ""