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