# Phase 6: POST_ONLY Entry Option - Decisions

## Decision 1: Parameter Name and Default
**Choice**: `use_post_only` parameter with default `False`

**Rationale**:
- Backward compatibility: Default False maintains existing IOC behavior
- Clear naming: Explicitly describes the feature
- Boolean flag: Simple for CLI usage (`--use-post-only`)

## Decision 2: Fee Rate Implementation
**Choice**: Calculate `FEE_RATE` dynamically based on `use_post_only`

**Rationale**:
- Single source of truth: No hardcoded fee constants scattered in code
- PNL accuracy: Fees tracked correctly for each order mode
- Future-proof: Easy to add more order modes (e.g., "reduce_only")

**Code**:
```python
FEE_RATE = Decimal("0.0002") if self.use_post_only else Decimal("0.0005")
```

## Decision 3: Order Status Handling
**Choice**: Accept both 'FILLED' and 'OPEN' as success for POST_ONLY orders

**Rationale**:
- POST_ONLY orders return 'OPEN' when placed on book (not immediately filled)
- Treating 'OPEN' as success allows the order to rest on book
- In production, would need monitoring for fills or cancellation

**Code**:
```python
eth_filled = eth_result.status == 'FILLED' or (self.use_post_only and eth_result.status == 'OPEN')
```

## Decision 4: API Method Selection
**Choice**: Use `place_open_order()` for POST_ONLY mode

**Rationale**:
- `place_open_order()` already uses `OrderType.POST_ONLY` appendix in NadoClient
- Avoids duplicating order placement logic
- Consistent with existing NadoClient API design

**NadoClient Implementation**:
```python
appendix=build_appendix(order_type=OrderType.POST_ONLY, isolated=True)
```

## Decision 5: Fallback Strategy (Deferred)
**Choice**: Document fallback requirement but defer implementation to V5.4

**Rationale**:
- Scope management: Focus on basic POST_ONLY support in Phase 6
- Complexity: Requires order monitoring and cancellation logic
- Testability: Need to validate basic POST_ONLY flow first

**Required for V5.4**:
- Monitor POST_ONLY order status
- Cancel after timeout if not filled
- Retry with IOC order
- Update CSV logging for order mode transitions

## Decision 6: Logging Strategy
**Choice**: Log order mode at both startup and order placement

**Rationale**:
- Startup log: Confirms configuration before trading begins
- Order log: Provides context for each trade in execution logs
- Debugging: Easy to identify which mode was used for specific trades

**Code**:
```python
# Startup
self.logger.info(f"[CONFIG] Order mode: {self.order_mode.upper()} (POST_ONLY={self.use_post_only})")

# Order placement
self.logger.info(f"[ORDER] Mode: {self.order_mode.upper()}, Fee: {fee_bps:.0f} bps")
```
