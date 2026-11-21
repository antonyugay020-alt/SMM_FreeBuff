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