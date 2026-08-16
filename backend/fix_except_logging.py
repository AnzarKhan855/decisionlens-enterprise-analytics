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
    "backend/app/database/connection.py",
    "backend/app/analytics/semantic_version_engine.py",
    "backend/app/ai/rag/retriever.py",
    "backend/app/cache/redis_cache.py",
    "backend/app/dashboard/storyteller.py",
    "backend/app/semantic_model/data_quality_detector.py",
    "backend/app/semantic_model/relationship_detector.py",
    "backend/app/core/security.py",
    "backend/app/core/enterprise_sso_engine.py",
    "backend/app/api/v1/endpoints/diagnostics.py",
    "backend/app/services/relationship_engine.py",
    "backend/app/services/strategy_engine.py",
    "backend/app/ingestion/generic_loader.py",
    "backend/app/services/refresh_scheduler.py",
    "backend/app/services/task_queue.py",
    "backend/app/ingestion/workspace_discovery.py",
    "backend/app/evaluation/framework.py",
    "backend/app/ingestion/intelligence_engine.py",
    "backend/app/api/v1/workspace_upload.py",
]

for filepath in files_to_fix:
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    if not os.path.exists(full_path):
        continue

    with open(full_path, 'r') as f:
        content = f.read()

    original = content

    # Check if get_logger is already imported
    has_logger = "from app.logging.logger import get_logger" in content or "from app.logging import logger" in content

    # Add get_logger import if missing
    if not has_logger:
        # Find the last import line and add after it
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i

        # Insert get_logger import
        lines.insert(last_import_idx + 1, 'from app.logging.logger import get_logger')
        lines.insert(last_import_idx + 2, 'logger = get_logger(__name__)')
        content = '\n'.join(lines)

    # Replace bare 'except Exception:' followed by 'pass' or other silent handling
    # We look for patterns like:
    #   except Exception:
    #       pass
    # or
    #   except Exception:
    #       <single statement>

    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == 'except Exception:' or line.strip().startswith('except Exception as'):
            # Check if next line is pass or something silent
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line == 'pass' or next_line == 'return None' or next_line == 'return []' or next_line == 'return {}':
                    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                    new_lines.append(line)
                    new_lines.append(f'{indent}    logger = get_logger(__name__)')
                    new_lines.append(f'{indent}    logger.warning("[SilentFailure] Exception swallowed", exc_info=True)')
                    new_lines.append(lines[i + 1])  # pass or return
                    i += 2
                    continue
        new_lines.append(line)
        i += 1

    content = '\n'.join(new_lines)

    if content != original:
        with open(full_path, 'w') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
    else:
        print(f"No changes needed: {filepath}")
