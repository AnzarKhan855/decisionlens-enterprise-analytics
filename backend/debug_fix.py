import re
import os

filepath = "backend/app/analytics/universal_engine.py"

with open(filepath, 'r') as f:
    content = f.read()

print(f"Original length: {len(content)}")
print(f"Has 'except Exception:': {'except Exception:' in content}")

# Check if get_logger is already imported
has_logger = "from app.logging.logger import get_logger" in content
print(f"Has get_logger import: {has_logger}")

# Add get_logger import if missing
if not has_logger:
    lines = content.split('\n')
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    lines.insert(last_import_idx + 1, 'from app.logging.logger import get_logger')
    lines.insert(last_import_idx + 2, 'logger = get_logger(__name__)')
    content = '\n'.join(lines)
    print("Added logger import")

# Replace bare except clauses
lines = content.split('\n')
new_lines = []
i = 0
count = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if stripped == 'except Exception:':
        # Check if next line is pass
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line == 'pass':
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(line)
                new_lines.append(f'{indent}    logger = get_logger(__name__)')
                new_lines.append(f'{indent}    logger.warning("[SilentFailure] Exception swallowed", exc_info=True)')
                new_lines.append(lines[i + 1])  # pass
                i += 2
                count += 1
                continue
    new_lines.append(line)
    i += 1

content = '\n'.join(new_lines)
print(f"Fixed {count} bare except clauses")
print(f"New length: {len(content)}")

with open(filepath, 'w') as f:
    f.write(content)
print("Written to file")
