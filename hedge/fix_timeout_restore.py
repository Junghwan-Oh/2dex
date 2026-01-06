#!/usr/bin/env python3
"""
Restore 180s timeout to cancel-replace loops in hedge_mode_2dex.py
ROOT CAUSE: RESTORATION_HISTORY_2DEX_HEDGE_MODE.md incorrectly analyzed original template
CORRECT PATTERN: Original has 180s timeout, not infinite loop
"""
import re

# Read file
with open('hedge_mode_2dex.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: executeOpenCycle - Add timeout check after line 433 (elapsed calculation)
pattern1 = r'(currentTime = time\.time\(\)\s+elapsed = currentTime - startTime)\s+(if elapsed > 10:)'

replacement1 = r'''\1

                    # Timeout check (original template: 180s per order)
                    if elapsed > 180:
                        self.logger.error("[TIMEOUT] PRIMARY order timeout after 180s, cancelling...")
                        await self.primaryClient.cancel_order(primaryResult.order_id)
                        self.fillRateStats['timeout'] += 1
                        self.logTradeToCsv(
                            self.primaryExchangeName, 'PRIMARY_MAKER', direction,
                            str(makerPrice), str(self.orderQuantity), 'timeout'
                        )
                        return False

                    \2'''

content = re.sub(pattern1, replacement1, content, count=1)

# Fix 2: executeCloseCycle - Add timeout check  
pattern2 = r'(# Active BBO monitoring for cancel-and-replace decision\s+currentTime = time\.time\(\)\s+elapsed = currentTime - startTime)\s+(if elapsed > 10:  # After 10 seconds, check if order price is stale)'

replacement2 = r'''\1

                    # Timeout check (original template: 180s per order)
                    if elapsed > 180:
                        self.logger.error("[TIMEOUT] PRIMARY close order timeout after 180s, cancelling...")
                        await self.primaryClient.cancel_order(primaryResult.order_id)
                        self.fillRateStats['timeout'] += 1
                        self.logTradeToCsv(
                            self.primaryExchangeName, 'PRIMARY_MAKER', oppositeDirection,
                            str(closePrice), str(closeSize), 'timeout_close'
                        )
                        return False

                    \2'''

content = re.sub(pattern2, replacement2, content, count=1)

# Fix 3: Update misleading comments
content = content.replace(
    '# Infinite retry pattern - no timeout break, only exit on FILLED',
    '# Active monitoring with 180s timeout (original template pattern)'
)

# Write back
with open('hedge_mode_2dex.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] 180s timeout restored to both executeOpenCycle and executeCloseCycle")
print("[OK] Misleading 'Infinite retry' comments corrected")
print("[OK] hedge_mode_2dex.py updated successfully")
