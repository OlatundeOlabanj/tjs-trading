"""
Bybit Service — order placement, position query, balance check.
Supports both testnet and live. HMAC-SHA256 signed requests.
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

LIVE_URL = "https://api.bybit.com"
TEST_URL = "https://api-testnet.bybit.com"


class BybitService:
    def __init__(self, api_key: str, api_secret: str, is_live: bool = False):
        self.api_key    = api_key
        self.api_secret = api_secret
        self.base_url   = LIVE_URL if is_live else TEST_URL
        self.recv_window = 5000

    def _sign(self, params: dict) -> dict:
        ts = str(int(time.time() * 1000))
        query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        sign_str = f"{ts}{self.api_key}{self.recv_window}{query}"
        sig = hmac.new(
            self.api_secret.encode(), sign_str.encode(), hashlib.sha256
        ).hexdigest()
        return {**params, "timestamp": ts, "sign": sig}

    def _headers(self, ts: str, sign: str) -> dict:
        return {
            "X-BAPI-API-KEY":     self.api_key,
            "X-BAPI-TIMESTAMP":   ts,
            "X-BAPI-SIGN":        sign,
            "X-BAPI-RECV-WINDOW": str(self.recv_window),
            "Content-Type":       "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> Optional[dict]:
        ts = str(int(time.time() * 1000))
        body = json.dumps(payload)
        sign_str = f"{ts}{self.api_key}{self.recv_window}{body}"
        sig = hmac.new(
            self.api_secret.encode(), sign_str.encode(), hashlib.sha256
        ).hexdigest()
        headers = self._headers(ts, sig)
        try:
            r = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers, data=body, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Bybit POST {endpoint} error: {e}")
            return None

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        ts = str(int(time.time() * 1000))
        sorted_params = dict(sorted(params.items()))
        query = "&".join([f"{k}={v}" for k, v in sorted_params.items()])
        sign_str = f"{ts}{self.api_key}{self.recv_window}{query}"
        sig = hmac.new(
            self.api_secret.encode(), sign_str.encode(), hashlib.sha256
        ).hexdigest()
        headers = self._headers(ts, sig)
        try:
            r = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers, params=sorted_params, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Bybit GET {endpoint} error: {e}")
            return None

    def place_order(
        self, symbol: str, side: str, qty: float,
        stop_loss: float = None, take_profit: float = None,
        leverage: int = 1, order_type: str = "Market",
        category: str = "linear"
    ) -> Optional[dict]:
        payload = {
            "category":  category,
            "symbol":    symbol,
            "side":      side,
            "orderType": order_type,
            "qty":       str(qty),
            "leverage":  str(leverage),
            "timeInForce": "GTC",
        }
        if stop_loss:   payload["stopLoss"]   = str(stop_loss)
        if take_profit: payload["takeProfit"] = str(take_profit)

        result = self._post("/v5/order/create", payload)
        if result and result.get("retCode") == 0:
            return result.get("result", {})
        logger.error(f"Bybit place_order error: {result}")
        return None

    def cancel_order(self, symbol: str, order_id: str, category: str = "linear") -> bool:
        result = self._post("/v5/order/cancel", {
            "category": category, "symbol": symbol, "orderId": order_id
        })
        return result and result.get("retCode") == 0

    def get_wallet_balance(self, account_type: str = "UNIFIED") -> Optional[dict]:
        result = self._get("/v5/account/wallet-balance", {"accountType": account_type})
        if result and result.get("retCode") == 0:
            return result.get("result", {})
        return None

    def get_positions(self, category: str = "linear", symbol: str = None) -> list:
        params = {"category": category, "limit": "50"}
        if symbol: params["symbol"] = symbol
        result = self._get("/v5/position/list", params)
        if result and result.get("retCode") == 0:
            return result.get("result", {}).get("list", [])
        return []

    def get_order_history(self, category: str = "linear", limit: int = 20) -> list:
        result = self._get("/v5/order/history", {
            "category": category, "limit": str(limit)
        })
        if result and result.get("retCode") == 0:
            return result.get("result", {}).get("list", [])
        return []
