import re

# Read the file
with open('grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# New iterative market order method
new_method = '''
    async def place_iterative_market_order(
        self,
        contract_id: str,
        target_quantity: Decimal,
        side: str,
        max_iterations: int = 20,
        max_tick_offset: int = 10,
        max_fill_duration: int = 30,
    ) -> dict:
        """Place iterative market orders to fill target_quantity by consuming GRVT liquidity depth.

        Strategy:
        1. Place market order for remaining quantity
        2. If partial fill, retry at 1-tick worse price
        3. Repeat until target_quantity filled or max_iterations/max_tick_offset reached

        Args:
            contract_id: GRVT contract symbol
            target_quantity: Total quantity to fill
            side: 'buy' or 'sell'
            max_iterations: Maximum retry attempts (default: 20)
            max_tick_offset: Maximum price degradation in ticks (default: 10)
            max_fill_duration: Maximum time to complete fill in seconds (default: 30)

        Returns:
            dict: {
                'total_filled': Decimal,
                'total_fees': Decimal,
                'average_price': Decimal,
                'iterations': int,
                'success': bool,
                'reason': str (if failed)
            }
        """
        import time

        start_time = time.time()
        total_filled = Decimal("0")
        total_fees = Decimal("0")
        iteration = 0
        tick_offset = 0
        price_history = []

        self.logger.info(
            f"[ITERATIVE] Starting {side.upper()} {target_quantity} ETH fill"
        )

        while total_filled < target_quantity:
            # Safety checks
            iteration += 1

            if iteration > max_iterations:
                reason = f"Max iterations ({max_iterations}) exceeded"
                self.logger.error(f"[ITERATIVE] {reason}")
                return {
                    'total_filled': total_filled,
                    'total_fees': total_fees,
                    'average_price': sum(price_history) / len(price_history) if price_history else None,
                    'iterations': iteration,
                    'success': False,
                    'reason': reason
                }

            if tick_offset > max_tick_offset:
                reason = f"Max tick offset ({max_tick_offset}) exceeded"
                self.logger.error(f"[ITERATIVE] {reason}")
                return {
                    'total_filled': total_filled,
                    'total_fees': total_fees,
                    'average_price': sum(price_history) / len(price_history) if price_history else None,
                    'iterations': iteration,
                    'success': False,
                    'reason': reason
                }

            if time.time() - start_time > max_fill_duration:
                reason = f"Max fill duration ({max_fill_duration}s) exceeded"
                self.logger.error(f"[ITERATIVE] {reason}")
                return {
                    'total_filled': total_filled,
                    'total_fees': total_fees,
                    'average_price': sum(price_history) / len(price_history) if price_history else None,
                    'iterations': iteration,
                    'success': False,
                    'reason': reason
                }

            # Calculate remaining quantity
            remaining = target_quantity - total_filled

            # Get current BBO with tick offset
            best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

            # Apply tick offset (worsen price for our side)
            tick_size = Decimal("0.01")  # ETH_USDT_Perp tick size
            if side == "buy":
                # Buying: pay more (worse price)
                base_price = best_ask
                adjusted_price = base_price + (tick_offset * tick_size)
            else:
                # Selling: receive less (worse price)
                base_price = best_bid
                adjusted_price = base_price - (tick_offset * tick_size)

            # Place market order
            try:
                # IMPORTANT: Remove the 0.2 ETH limit for iterative approach
                # We handle this by iterating instead of rejecting
                order_result = self.rest_client.create_order(
                    symbol=contract_id,
                    order_type="market",
                    side=side,
                    amount=remaining
                )

                if not order_result:
                    self.logger.warning(f"[ITERATIVE] Order failed (iteration {iteration})")
                    tick_offset += 1
                    continue

                # Extract order info
                metadata = order_result.get("metadata", {})
                client_order_id = metadata.get("client_order_id")

                # Wait for order to process
                await asyncio.sleep(0.5)

                # Get order info to check fill
                order_info = await self.get_order_info(client_order_id=client_order_id)

                if order_info and order_info.status == "FILLED":
                    filled_quantity = order_info.executed_quantity
                    fill_price = order_info.price

                    total_filled += filled_quantity
                    price_history.append(float(fill_price))

                    # Calculate fee (approximate 0.05% taker fee)
                    fee = filled_quantity * fill_price * Decimal("0.0005")
                    total_fees += fee

                    self.logger.info(
                        f"[ITERATIVE] Iteration {iteration}: Filled {filled_quantity} @ ${fill_price} "
                        f"(offset: {tick_offset} ticks, total: {total_filled}/{target_quantity})"
                    )

                    # Check if we're done
                    if total_filled >= target_quantity:
                        avg_price = sum(price_history) / len(price_history)
                        self.logger.info(
                            f"[ITERATIVE] SUCCESS: Filled {total_filled} ETH @ avg ${avg_price:.2f} "
                            f"in {iteration} iterations"
                        )

                        # Update local position
                        if side == "buy":
                            self._local_position += total_filled
                        else:
                            self._local_position -= total_filled

                        return {
                            'total_filled': total_filled,
                            'total_fees': total_fees,
                            'average_price': Decimal(str(avg_price)),
                            'iterations': iteration,
                            'success': True
                        }

                    # Partial fill: increment tick offset for next attempt
                    if filled_quantity < remaining:
                        tick_offset += 1
                        self.logger.debug(
                            f"[ITERATIVE] Partial fill: {filled_quantity}/{remaining}, "
                            f"increasing tick offset to {tick_offset}"
                        )

                else:
                    # Order not filled or failed
                    self.logger.warning(
                        f"[ITERATIVE] Order not filled (iteration {iteration}, status: {order_info.status if order_info else 'UNKNOWN'})"
                    )
                    tick_offset += 1

            except Exception as e:
                self.logger.error(f"[ITERATIVE] Exception in iteration {iteration}: {e}")
                tick_offset += 1
                await asyncio.sleep(1)  # Wait before retry

        # Should not reach here, but just in case
        return {
            'total_filled': total_filled,
            'total_fees': total_fees,
            'average_price': sum(price_history) / len(price_history) if price_history else None,
            'iterations': iteration,
            'success': False,
            'reason': 'Exited loop without completion'
        }

'''

# Find the end of place_market_order method (around line 480)
# Look for the next method definition
insert_marker = '    async def cancel_order('

if insert_marker in content:
    # Insert the new method before cancel_order
    content = content.replace(insert_marker, new_method + insert_marker)

    with open('grvt.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print('SUCCESS: Added place_iterative_market_order method before cancel_order')
else:
    print('ERROR: Could not find cancel_order method to use as insertion marker')
