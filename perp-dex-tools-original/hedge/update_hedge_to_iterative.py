import re

# Read the file
with open('DN_alternate_backpack_grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the place_hedge_order method and update it to use iterative approach for GRVT
# We need to modify both OPEN and CLOSE sections to use iterative_market_order

old_open_section = '''                else:
                    # OPEN: Use MARKET order for immediate fill (same as CLOSE)
                    self.logger.info(
                        f"[OPEN] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                    )

                    # Get position before placing order
                    pos_before = await self.hedge_client.get_account_positions()

                    # Place market order for immediate fill
                    order_info = await self.hedge_client.place_market_order(
                        contract_id=self.hedge_contract_id,
                        quantity=quantity,
                        side=order_side,
                    )

                    # Wait briefly for execution and verify
                    await asyncio.sleep(1.0)
                    pos_after = await self.hedge_client.get_account_positions()
                    position_change = abs(pos_after - pos_before)

                    if position_change >= quantity * Decimal("0.9"):
                        actual_fill_price = best_ask if side == "buy" else best_bid
                        self.logger.info(
                            f"[OPEN] [{self.hedge_exchange.upper()}] [MARKET FILLED]: "
                            f"{quantity} @ ~{actual_fill_price} (pos: {pos_before} -> {pos_after})"
                        )'''

new_open_section = '''                else:
                    # OPEN: Use ITERATIVE market order for GRVT to handle liquidity constraints
                    if self.hedge_exchange.lower() == "grvt":
                        self.logger.info(
                            f"[OPEN] [{self.hedge_exchange.upper()}] Using ITERATIVE MARKET order for liquidity depth consumption"
                        )

                        # Use iterative market order for GRVT
                        result = await self.hedge_client.place_iterative_market_order(
                            contract_id=self.hedge_contract_id,
                            target_quantity=quantity,
                            side=order_side,
                            max_iterations=20,
                            max_tick_offset=10,
                            max_fill_duration=30,
                        )

                        if result['success']:
                            actual_fill_price = result['average_price']
                            total_filled = result['total_filled']
                            iterations = result['iterations']

                            self.logger.info(
                                f"[OPEN] [{self.hedge_exchange.upper()}] [ITERATIVE FILLED]: "
                                f"{total_filled} @ avg ${actual_fill_price:.2f} "
                                f"({iterations} iterations, ${result['total_fees']:.4f} fees)"
                            )

                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(actual_fill_price),
                                quantity=str(total_filled),
                                order_type="hedge_open_iterative",
                                mode="iterative_market",
                            )

                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = actual_fill_price
                            return True
                        else:
                            self.logger.error(
                                f"[OPEN] Iterative market order failed: {result.get('reason', 'Unknown')}. "
                                f"Filled {result['total_filled']}/{quantity} ETH"
                            )
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False
                    else:
                        # Non-GRVT exchanges: Use regular market order
                        self.logger.info(
                            f"[OPEN] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                        )

                        # Get position before placing order
                        pos_before = await self.hedge_client.get_account_positions()

                        # Place market order for immediate fill
                        order_info = await self.hedge_client.place_market_order(
                            contract_id=self.hedge_contract_id,
                            quantity=quantity,
                            side=order_side,
                        )

                        # Wait briefly for execution and verify
                        await asyncio.sleep(1.0)
                        pos_after = await self.hedge_client.get_account_positions()
                        position_change = abs(pos_after - pos_before)

                        if position_change >= quantity * Decimal("0.9"):
                            actual_fill_price = best_ask if side == "buy" else best_bid
                            self.logger.info(
                                f"[OPEN] [{self.hedge_exchange.upper()}] [MARKET FILLED]: "
                                f"{quantity} @ ~{actual_fill_price} (pos: {pos_before} -> {pos_after})"
                            )'''

old_close_section = '''                # SOLUTION 3: CLOSE uses true market order for immediate fill
                if order_type == "CLOSE":
                    self.logger.info(
                        f"[CLOSE] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                    )
                    # Get position before placing order (REST API for reliability)
                    pos_before_close = await self.hedge_client.get_account_positions()

                    # Use true market order (no timeout, immediate fill)
                    order_info = await self.hedge_client.place_market_order(
                        contract_id=self.hedge_contract_id,
                        quantity=quantity,
                        side=order_side,
                    )

                    # Market orders fill immediately - verify with REST API
                    await asyncio.sleep(1.0)  # Brief wait for execution
                    pos_after_close = await self.hedge_client.get_account_positions()
                    position_change = abs(pos_after_close - pos_before_close)

                    if position_change >= quantity * Decimal("0.9"):
                        actual_fill_price = best_ask if side == "buy" else best_bid
                        self.logger.info(
                            f"[CLOSE] [{self.hedge_exchange.upper()}] [FILLED]: "
                            f"{quantity} @ ~{actual_fill_price} (pos: {pos_before_close} -> {pos_after_close})"
                        )

                        self.log_trade_to_csv(
                            exchange=self.hedge_exchange.upper(),
                            side=side,
                            price=str(actual_fill_price),
                            quantity=str(quantity),
                            order_type="hedge_close",
                            mode="market_taker",
                        )

                        self.hedge_order_filled = True
                        self.order_execution_complete = True
                        self.last_hedge_fill_price = actual_fill_price
                        return True
                    else:
                        self.logger.error(
                            f"[CLOSE] Market order failed to fill (pos: {pos_before_close} -> {pos_after_close})"
                        )
                        self.hedge_order_filled = False
                        self.order_execution_complete = False
                        return False'''

new_close_section = '''                # SOLUTION 3: CLOSE uses iterative market order for GRVT, regular market for others
                if order_type == "CLOSE":
                    if self.hedge_exchange.lower() == "grvt":
                        self.logger.info(
                            f"[CLOSE] [{self.hedge_exchange.upper()}] Using ITERATIVE MARKET order for liquidity depth consumption"
                        )

                        # Use iterative market order for GRVT
                        result = await self.hedge_client.place_iterative_market_order(
                            contract_id=self.hedge_contract_id,
                            target_quantity=quantity,
                            side=order_side,
                            max_iterations=20,
                            max_tick_offset=10,
                            max_fill_duration=30,
                        )

                        if result['success']:
                            actual_fill_price = result['average_price']
                            total_filled = result['total_filled']
                            iterations = result['iterations']

                            self.logger.info(
                                f"[CLOSE] [{self.hedge_exchange.upper()}] [ITERATIVE FILLED]: "
                                f"{total_filled} @ avg ${actual_fill_price:.2f} "
                                f"({iterations} iterations, ${result['total_fees']:.4f} fees)"
                            )

                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(actual_fill_price),
                                quantity=str(total_filled),
                                order_type="hedge_close_iterative",
                                mode="iterative_market",
                            )

                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = actual_fill_price
                            return True
                        else:
                            self.logger.error(
                                f"[CLOSE] Iterative market order failed: {result.get('reason', 'Unknown')}. "
                                f"Filled {result['total_filled']}/{quantity} ETH"
                            )
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False
                    else:
                        # Non-GRVT exchanges: Use regular market order
                        self.logger.info(
                            f"[CLOSE] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                        )
                        # Get position before placing order (REST API for reliability)
                        pos_before_close = await self.hedge_client.get_account_positions()

                        # Use true market order (no timeout, immediate fill)
                        order_info = await self.hedge_client.place_market_order(
                            contract_id=self.hedge_contract_id,
                            quantity=quantity,
                            side=order_side,
                        )

                        # Market orders fill immediately - verify with REST API
                        await asyncio.sleep(1.0)  # Brief wait for execution
                        pos_after_close = await self.hedge_client.get_account_positions()
                        position_change = abs(pos_after_close - pos_before_close)

                        if position_change >= quantity * Decimal("0.9"):
                            actual_fill_price = best_ask if side == "buy" else best_bid
                            self.logger.info(
                                f"[CLOSE] [{self.hedge_exchange.upper()}] [FILLED]: "
                                f"{quantity} @ ~{actual_fill_price} (pos: {pos_before_close} -> {pos_after_close})"
                            )

                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(actual_fill_price),
                                quantity=str(quantity),
                                order_type="hedge_close",
                                mode="market_taker",
                            )

                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = actual_fill_price
                            return True
                        else:
                            self.logger.error(
                                f"[CLOSE] Market order failed to fill (pos: {pos_before_close} -> {pos_after_close})"
                            )
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False'''

# Replace the sections
content = content.replace(old_close_section, new_close_section)
content = content.replace(old_open_section, new_open_section)

# Also need to remove the 0.2 ETH hard limit in grvt.py since we're using iterative approach
# But we'll keep it as a safety comment

# Write the updated content
with open('DN_alternate_backpack_grvt.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('SUCCESS: Updated place_hedge_order to use iterative market orders for GRVT')
print('Both BUILD and UNWIND phases now use iterative approach')
