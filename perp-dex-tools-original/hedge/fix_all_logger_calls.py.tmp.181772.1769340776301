import re

with open('exchanges/grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix self.logger.log(...) calls to add second parameter
# Pattern: self.logger.log(f"...")  →  self.logger.log(f"...", "INFO")

def add_log_level(match):
    full_call = match.group(0)
    # Extract the message part
    message = match.group(1)

    # Determine log level from context or default to INFO
    # Check surrounding lines for ERROR or WARNING keywords
    return f'self.logger.log({message}, "INFO")'

# Replace logger.log calls without second parameter
content = re.sub(
    r'self\.logger\.log\((f"[^"]+")\)',
    r'self.logger.log(\1, "INFO")',
    content
)

# For ERROR and WARNING contexts, we need to be more specific
# These are already fixed from previous attempts, so just ensure INFO ones work

with open('exchanges/grvt.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed all logger.log() calls to include log level')
