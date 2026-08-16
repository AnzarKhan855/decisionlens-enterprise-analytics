import re
import os

files_to_fix = [
    "backend/app/analytics/universal_engine.py",
    "backend/app/services/dynamic_dashboard_service.py",
    "backend/app/ai/universal_copilot_brain.py",
    "backend/app/api/v1/upload.py",
    "backend/app/services/workspace_service.py",
    "backend/app/analytics/chart_engine.py",
    "backend/app/analytics/data_catalog_engine.py",
    "backend/app/semantic_model/engine.py",
    "backend/app/semantic_model/cache.py",
    "backend/app/database/duckdb_engine.py",
]

for filepath in files_to_fix:
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    if not os.path.exists(full_path):
        continue

    with open(full_path, 'r') as f:
        content = f.read()

    # Replace bare 'except Exception:' followed by 'pass' with logging
    # We need to be careful to only replace in specific contexts
    original = content

    # Pattern: except Exception:\n            pass
    content = re.sub(
        r'(\s+)except Exception:\n(\s+)pass\n',
        r'\1except Exception:\n\2    logger = get_logger(__name__)\n\2    logger.warning("[SilentFailure] Exception swallowed", exc_info=True)\n\2    pass\n',
        content
    )

    if content != original:
        with open(full_path, 'w') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
    else:
        print(f"No changes: {filepath}")
