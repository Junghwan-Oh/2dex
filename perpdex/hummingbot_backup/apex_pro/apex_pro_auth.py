"""
Authentication module for Apex Pro Exchange Connector

Implements Hummingbot AuthBase pattern with Apex Pro's ZK-rollup authentication.
"""

import sys
import time
import hmac
import hashlib
import base64
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest, WSRequest
from hummingbot.connector.time_synchronizer import TimeSynchronizer

import hummingbot.connector.exchange.apex_pro.apex_pro_constants as CONSTANTS


class ApexProAuth(AuthBase):
    """
    Authentication wrapper for Apex Pro API requests.

    Implements Hummingbot's AuthBase interface with Apex-specific ZK-rollup signing.
    Uses HMAC-SHA256 for REST API authentication.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
        zk_seeds: str,
        zk_l2_key: str,
        network_id: int,
        time_provider: Optional[TimeSynchronizer] = None,
    ):
        """
        Initialize Apex Pro authentication.

        Args:
            api_key: API key from Apex Pro
            api_secret: API secret from Apex Pro
            api_passphrase: API passphrase from Apex Pro
            zk_seeds: ZK-rollup seed phrase
            zk_l2_key: Layer 2 private key
            network_id: Blockchain network ID (Arbitrum mainnet = 42161)
            time_provider: Time synchronizer (optional)
        """
        self._api_key = api_key
        self._api_secret = api_secret
        self._api_passphrase = api_passphrase
        self._zk_seeds = zk_seeds
        self._zk_l2_key = zk_l2_key
        self._network_id = network_id
        self._time_provider = time_provider

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        """
        Add authentication headers to REST request.

        Args:
            request: Request to authenticate

        Returns:
            Request with auth headers added
        """
        headers = self._generate_auth_headers(
            method=request.method,
            path_url=request.url.path if hasattr(request.url, 'path') else str(request.url),
            params=request.params,
            data=request.data
        )

        request.headers = {**request.headers, **headers} if request.headers is not None else headers
        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        WebSocket authentication (not used for Apex public feeds).

        Args:
            request: WebSocket request

        Returns:
            Original request (no auth needed for public WebSocket)
        """
        return request

    def _generate_auth_headers(
        self,
        method: RESTMethod,
        path_url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate authentication headers for API requests.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path_url: API endpoint path
            params: Query parameters (for GET requests)
            data: Request body data (for POST requests)

        Returns:
            Dictionary of authentication headers
        """
        timestamp = str(int(time.time() * 1000))  # Milliseconds

        # Build request string for signature (matching apexomni SDK format)
        # For GET requests: params go in the path, data is empty
        # For POST requests: data goes in the signature
        if data:
            # For POST/DELETE requests with body data
            # Handle both dict and JSON string
            if isinstance(data, str):
                import json
                data = json.loads(data)
            sortedItems = sorted(data.items(), key=lambda x: x[0], reverse=False)
            dataString = '&'.join(f'{key}={value}' for key, value in sortedItems if value is not None)
            messageString = f"{timestamp}{method.name}{path_url}{dataString}"
        else:
            # For GET requests: params are already in path_url, no dataString
            messageString = f"{timestamp}{method.name}{path_url}"

        # Generate HMAC-SHA256 signature (matching apexomni SDK)
        # 1. Base64 encode the secret
        # 2. HMAC-SHA256 with the message
        # 3. Base64 encode the result
        hashed = hmac.new(
            base64.standard_b64encode(self._api_secret.encode('utf-8')),
            msg=messageString.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        signature = base64.standard_b64encode(hashed.digest()).decode()

        return {
            "APEX-API-KEY": self._api_key,
            "APEX-PASSPHRASE": self._api_passphrase,
            "APEX-SIGNATURE": signature,
            "APEX-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    def get_zk_keys(self) -> Dict[str, Any]:
        """
        Get ZK-rollup keys for L2 operations.

        Returns:
            Dictionary with ZK seeds and L2 key
        """
        return {
            "zk_seeds": self._zk_seeds,
            "zk_l2_key": self._zk_l2_key,
            "network_id": self._network_id,
        }

    @property
    def api_key(self) -> str:
        """Get API key."""
        return self._api_key

    @property
    def api_secret(self) -> str:
        """Get API secret."""
        return self._api_secret

    @property
    def api_passphrase(self) -> str:
        """Get API passphrase."""
        return self._api_passphrase
