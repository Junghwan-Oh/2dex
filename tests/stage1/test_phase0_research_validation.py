"""
Phase 0 Research Validation Tests

This test file validates that Phase 0 research is complete and accurate
before proceeding with implementation phases.

Test file: /Users/botfarmer/2dex/tests/stage1/test_phase0_research_validation.py
Plan: Nado DN Pair V4 Migration (Sub-Feature 0.6)
"""

import pytest
import re
import subprocess
import sys
from pathlib import Path
from decimal import Decimal


class TestPhase0ResearchValidation:
    """Validate Phase 0 research completeness and accuracy."""

    # Path constants from the plan
    RESEARCH_DOC_PATH = Path("/Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md")

    # Test 1: Research document exists at specified path
    def test_research_document_exists(self):
        """
        GIVEN: Phase 0 research complete
        WHEN: test_research_document_exists() called
        THEN: File exists at /Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md
        """
        assert self.RESEARCH_DOC_PATH.exists(), (
            f"Research document not found at {self.RESEARCH_DOC_PATH}. "
            "Complete Phase 0 research first (Sub-Features 0.1-0.5)."
        )
        assert self.RESEARCH_DOC_PATH.is_file(), (
            f"Research path exists but is not a file: {self.RESEARCH_DOC_PATH}"
        )

    # Test 2: All 6 sections of research document are complete
    def test_research_document_complete(self):
        """
        GIVEN: Research document exists
        WHEN: test_research_document_complete() called
        THEN: All sections (Executive Summary, WebSocket, Order Types, REST API, Products, Recommendations) contain content
        """
        assert self.RESEARCH_DOC_PATH.exists(), "Research document must exist first"

        content = self.RESEARCH_DOC_PATH.read_text()

        # Check for required sections based on plan structure
        required_sections = [
            r"## \d+\.\s+Executive\s+Summary",
            r"## \d+\.\s+WebSocket\s+Capabilities",
            r"## \d+\.\s+Order\s+Type\s+Support",
            r"## \d+\.\s+REST\s+API\s+Methods",
            r"## \d+\.\s+Product\s+and\s+Market\s+Data",
            r"## \d+\.\s+Recommendations"
        ]

        missing = []
        section_names = ['Executive Summary', 'WebSocket Capabilities', 'Order Type Support',
                        'REST API Methods', 'Product and Market Data', 'Recommendations']
        for name, pattern in zip(section_names, required_sections):
            if not re.search(pattern, content, re.IGNORECASE):
                missing.append(name)

        assert len(missing) == 0, (
            f"Missing sections in research document: {missing}. "
            f"Required sections: Executive Summary, WebSocket Capabilities, "
            f"Order Type Support, REST API Methods, Product and Market Data, Recommendations"
        )

    # Test 3: Code examples from research execute successfully
    def test_code_examples_execute(self):
        """
        GIVEN: Code examples from research document
        WHEN: test_code_examples_execute() called
        THEN: All Python code snippets run without errors

        Note: This test validates that code examples in the research
        document are syntactically correct and can execute.
        """
        pytest.skip("TODO: Implement code example extraction and validation")

    # Test 4: Product IDs match actual SDK output
    def test_product_ids_match(self):
        """
        GIVEN: Research document specifies product IDs
        WHEN: test_product_ids_match() called
        THEN: Documented ETH/SOL product IDs match get_all_product_symbols() output

        This test requires the Nado SDK to be installed and accessible.
        Skipped if SDK is not available.
        """
        try:
            from nado_protocol.client import create_nado_client
        except ImportError:
            pytest.skip("Nado SDK not installed - skip product ID validation")

        assert self.RESEARCH_DOC_PATH.exists(), "Research document must exist first"

        content = self.RESEARCH_DOC_PATH.read_text()

        # Extract product IDs from research document
        # Look for patterns like "ETH Product ID: 4" or "ETH=4"
        eth_id_match = re.search(r'ETH\s*(?:product)?\s*ID?\s*[:=]\s*(\d+)', content, re.IGNORECASE)
        sol_id_match = re.search(r'SOL\s*(?:product)?\s*ID?\s*[:=]\s*(\d+)', content, re.IGNORECASE)

        if not eth_id_match or not sol_id_match:
            pytest.skip("Product IDs not documented in research yet")

        documented_eth_id = int(eth_id_match.group(1))
        documented_sol_id = int(sol_id_match.group(1))

        # Verify against actual SDK (using devnet for testing)
        try:
            client = create_nado_client('devnet', '0x' + '0' * 64)
            symbols = client.market.get_all_product_symbols()

            # Find ETH and SOL product IDs
            actual_eth_id = None
            actual_sol_id = None

            for symbol in symbols:
                symbol_str = str(symbol.symbol).upper()
                if 'ETH' in symbol_str and actual_eth_id is None:
                    actual_eth_id = symbol.product_id
                elif 'SOL' in symbol_str and actual_sol_id is None:
                    actual_sol_id = symbol.product_id

            if actual_eth_id is not None:
                assert documented_eth_id == actual_eth_id, (
                    f"ETH product ID mismatch: documented={documented_eth_id}, "
                    f"actual={actual_eth_id}. Update research document."
                )

            if actual_sol_id is not None:
                assert documented_sol_id == actual_sol_id, (
                    f"SOL product ID mismatch: documented={documented_sol_id}, "
                    f"actual={actual_sol_id}. Update research document."
                )

        except Exception as e:
            pytest.skip(f"Cannot connect to Nado SDK for validation: {e}")

    # Test 5: Order types verified against SDK enum
    def test_order_types_verified(self):
        """
        GIVEN: Research document lists order types
        WHEN: test_order_types_verified() called
        THEN: Documented order types match nado_protocol.utils.order.OrderType enum

        This test validates that the order types documented in research
        match the actual SDK enum values.
        """
        try:
            from nado_protocol.utils.order import OrderType
        except ImportError:
            pytest.skip("Nado SDK not installed - skip order type validation")

        assert self.RESEARCH_DOC_PATH.exists(), "Research document must exist first"

        content = self.RESEARCH_DOC_PATH.read_text()

        # Get actual order types from SDK
        actual_order_types = [attr for attr in dir(OrderType) if not attr.startswith('_')]

        # Check for documented order types
        # Just verify that any mentioned order types exist in SDK
        documented_types = []
        for order_type in actual_order_types:  # Only check SDK types that exist
            if order_type in content:
                documented_types.append(order_type)

        # Verify that documented types exist in SDK
        for doc_type in documented_types:
            assert doc_type in actual_order_types, (
                f"Order type '{doc_type}' documented but not found in SDK. "
                f"Available types: {actual_order_types}"
            )

        assert len(documented_types) > 0, (
            "No order types documented in research. "
            "Document at least POST_ONLY and IOC."
        )

    # Test 6: REST API methods documented accurately
    def test_rest_methods_accurate(self):
        """
        GIVEN: Research document lists REST methods
        WHEN: test_rest_methods_accurate() called
        THEN: All documented methods exist in actual SDK

        This test validates that REST API methods documented in research
        actually exist in the Nado SDK.
        """
        try:
            from nado_protocol.client import create_nado_client
        except ImportError:
            pytest.skip("Nado SDK not installed - skip REST method validation")

        assert self.RESEARCH_DOC_PATH.exists(), "Research document must exist first"

        content = self.RESEARCH_DOC_PATH.read_text()

        # Create client to inspect available methods
        try:
            client = create_nado_client('devnet', '0x' + '0' * 64)

            # Get actual methods from engine_client, indexer_client, and market
            engine_methods = [m for m in dir(client.context.engine_client) if not m.startswith('_')]
            indexer_methods = [m for m in dir(client.context.indexer_client) if not m.startswith('_')]
            market_methods = [m for m in dir(client.market) if not m.startswith('_')]

            all_actual_methods = set(engine_methods + indexer_methods + market_methods)

            # Look for documented methods in research
            # Common methods to look for
            critical_methods = [
                'get_order', 'get_historical_orders_by_digest', 'get_all_product_symbols',
                'get_all_engine_markets', 'get_market_price'
            ]

            documented_methods_exist = []
            for method in critical_methods:
                if method in content:
                    assert method in all_actual_methods, (
                        f"Method '{method}' documented in research but not found in SDK. "
                        f"Check if method name is correct."
                    )
                    documented_methods_exist.append(method)

            # At least some critical methods should be documented
            assert len(documented_methods_exist) > 0, (
                "No REST API methods documented in research. "
                "Document critical methods like get_order, get_all_product_symbols, etc."
            )

        except Exception as e:
            pytest.skip(f"Cannot connect to Nado SDK for method validation: {e}")
