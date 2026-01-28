# Read the file
with open('DN_alternate_backpack_grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the CLOSE section
search_pattern = '''                # SOLUTION 3: CLOSE uses true market order for immediate fill
                if order_type == "CLOSE":
                    self.logger.info(
                        f"[CLOSE] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                    )
                    # Get position before placing order (REST API for reliability)
                    pos_before_close = await self.hedge_client.get_account_positions()

                    # Use true market order (no timeout, immediate fill)
                    order_info = await self.hedge_client.place_market_order('''

replacement = '''                # SOLUTION 3: CLOSE uses iterative market order for GRVT, regular for others
                if order_type == "CLOSE":
                    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2"):
                        self.logger.info(f"[CLOSE] Using ITERATIVE market order for {quantity} ETH")
                        result = await self.hedge_client.place_iterative_market_order(
                            contract_id=self.hedge_contract_id,
                            target_quantity=quantity,
                            side=order_side,
                            max_iterations=20,
                            max_tick_offset=10,
                            max_fill_duration=30
                        )

                        if result['success']:
                            self.logger.info(
                                f"[CLOSE] [ITERATIVE] Filled {result['total_filled']} @ ${result['average_price']:.2f} "
                                f"({result['iterations']} iterations)"
                            )
                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(result['average_price']),
                                quantity=str(result['total_filled']),
                                order_type="hedge_close_iterative",
                                mode="iterative_market"
                            )
                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = result['average_price']
                            return True
                        else:
                            self.logger.error(f"[CLOSE] Iterative failed: {result.get('reason', 'unknown')}")
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False
                    else:
                        # Regular market order for small sizes or non-GRVT
                        self.logger.info(
                            f"[CLOSE] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                        )
                        # Get position before placing order (REST API for reliability)
                        pos_before_close = await self.hedge_client.get_account_positions()

                        # Use true market order (no timeout, immediate fill)
                        order_info = await self.hedge_client.place_market_order('''

# Replace
if search_pattern in content:
    content = content.replace(search_pattern, replacement)
    print('SUCCESS: Added iterative logic to CLOSE section')
else:
    print('ERROR: Pattern not found')

# Write back
with open('DN_alternate_backpack_grvt.py', 'w', encoding='utf-8') as f:
    f.write(content)
