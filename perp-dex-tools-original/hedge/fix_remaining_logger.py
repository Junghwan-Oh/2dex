# Fix remaining logger.log() calls that are missing the second parameter
with open('exchanges/grvt.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix specific lines
fixes = {
    815: '                    self.logger.log(f"[ITERATIVE] Order failed (iteration {iteration})", "WARNING")\n',
    877: '                    self.logger.log(\n',
    878: '                        f"[ITERATIVE] Partial fill: {filled_quantity}/{remaining} ETH filled",\n',
    879: '                        "WARNING"\n',
    880: '                    )\n',
    883: '                self.logger.log(f"[ITERATIVE] Exception in iteration {iteration}: {e}", "ERROR")\n'
}

for line_num, new_line in fixes.items():
    if line_num - 1 < len(lines):
        if '\n' in new_line:
            # Multi-line replacement
            if line_num == 877:
                lines[line_num - 1] = new_line
                lines[line_num] = '                        f"[ITERATIVE] Partial fill: {filled_quantity}/{remaining} ETH filled",\n'
                lines[line_num + 1] = '                        "WARNING"\n'
                lines[line_num + 2] = '                    )\n'
            else:
                lines[line_num - 1] = new_line
        else:
            lines[line_num - 1] = new_line + '\n'

with open('exchanges/grvt.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed remaining logger.log() calls')
