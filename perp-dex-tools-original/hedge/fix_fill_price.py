# Fix fill_price variable in iterative method
with open('exchanges/grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the corrupted variable names
content = content.replace('fill_avg_fill_price', 'fill_price')

with open('exchanges/grvt.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed fill_price variable name')
