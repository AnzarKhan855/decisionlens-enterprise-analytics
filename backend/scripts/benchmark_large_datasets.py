"""
Enterprise Production Scale & Large Dataset Benchmark
Evaluates DecisionLens streaming ingestion, Parquet conversion,
profiling, and intelligence across 10MB, 50MB, and 100MB synthetic datasets.
"""

import os
import sys
import time
import json
import uuid
import tempfile
import tracemalloc
from pathlib import Path
from typing import Dict, Any

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.ingestion.domain_classifier import DatasetDomainClassifier
from app.services.ingestion_job_service import IngestionJobService, JobState
from app.semantic_model.engine import build_semantic_model
from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
from app.database.duckdb_engine import DuckDBEngine


def generate_synthetic_csv(target_mb: float, output_path: Path) -> int:
    """Generates a realistic enterprise retail transactions CSV reaching target_mb."""
    import random
    from datetime import datetime, timedelta

    stores = [f"STORE-{i:03d}" for i in range(1, 21)]
    categories = ["Electronics", "Apparel", "Home & Kitchen", "Automotive", "Industrial", "Beauty", "Sports"]
    payment_methods = ["CREDIT_CARD", "DEBIT_CARD", "ACH", "WIRE", "PAYPAL"]
    base_date = datetime(2024, 1, 1)

    target_bytes = int(target_mb * 1024 * 1024)
    written_bytes = 0
    row_count = 0

    header = "transaction_id,timestamp,store_id,customer_id,product_category,quantity,unit_price,discount_pct,total_amount,payment_method,is_returned\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        written_bytes += len(header.encode("utf-8"))

        batch = []
        batch_size = 5000
        while written_bytes < target_bytes:
            for _ in range(batch_size):
                row_count += 1
                tx_id = f"TX-{row_count:08d}"
                dt = (base_date + timedelta(minutes=random.randint(0, 525600))).strftime("%Y-%m-%d %H:%M:%S")
                store = random.choice(stores)
                cust = f"CUST-{random.randint(1, 15000):06d}"
                cat = random.choice(categories)
                qty = random.randint(1, 10)
                price = round(random.uniform(5.0, 450.0), 2)
                discount = round(random.choice([0.0, 0.05, 0.10, 0.15, 0.20]), 2)
                total = round(qty * price * (1.0 - discount), 2)
                pm = random.choice(payment_methods)
                ret = 1 if random.random() < 0.04 else 0

                batch.append(f"{tx_id},{dt},{store},{cust},{cat},{qty},{price},{discount},{total},{pm},{ret}\n")

            chunk = "".join(batch)
            f.write(chunk)
            written_bytes += len(chunk.encode("utf-8"))
            batch.clear()

    return row_count


def benchmark_dataset(size_label: str, target_mb: float) -> Dict[str, Any]:
    """Runs an end-to-end benchmark on a dataset of target_mb."""
    print(f"\n=======================================================")
    print(f"[*] Starting Benchmark for {size_label} ({target_mb} MB)")
    print(f"=======================================================")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"bench_{size_label}_"))
    csv_path = temp_dir / f"benchmark_{size_label}.csv"

    # Step 0: Generate synthetic CSV
    gen_start = time.perf_counter()
    rows = generate_synthetic_csv(target_mb, csv_path)
    gen_time = time.perf_counter() - gen_start
    actual_mb = csv_path.stat().st_size / (1024 * 1024)
    print(f"  Generated {rows:,} rows in {gen_time:.2f}s ({actual_mb:.2f} MB)")

    ws_id = f"ws-bench-{int(target_mb)}mb-{uuid.uuid4().hex[:6]}"
    dataset_id = f"ds-bench-{int(target_mb)}mb"

    # Track process memory
    tracemalloc.start()
    pipeline_start = time.perf_counter()

    # Step 1: Memory-Safe Streaming Simulation (1MB chunks)
    stream_start = time.perf_counter()
    ParquetStorageManager.ensure_directories()
    raw_dest = ParquetStorageManager.get_raw_path(dataset_id, csv_path.name)

    chunk_size = 1024 * 1024
    stream_chunks = 0
    with open(csv_path, "rb") as src, open(raw_dest, "wb") as dst:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            stream_chunks += 1
    stream_time = time.perf_counter() - stream_start
    stream_throughput_mbs = actual_mb / stream_time if stream_time > 0 else 0
    print(f"  [1] Streaming Ingestion: {stream_time:.3f}s ({stream_throughput_mbs:.1f} MB/s, {stream_chunks} chunks)")

    # Step 2: DuckDB Parquet Conversion
    parquet_start = time.perf_counter()
    parquet_path = GenericDataLoader.convert_to_parquet(raw_dest, dataset_id)
    parquet_time = time.perf_counter() - parquet_start
    parquet_size_mb = parquet_path.stat().st_size / (1024 * 1024)
    compression_ratio = actual_mb / parquet_size_mb if parquet_size_mb > 0 else 1.0
    print(f"  [2] DuckDB Parquet Conversion: {parquet_time:.3f}s (Size: {parquet_size_mb:.2f} MB, {compression_ratio:.1f}x compression)")

    # Step 3: Semantic Data Profiler
    profile_start = time.perf_counter()
    profile = SemanticDataProfiler.profile(parquet_path)
    profile_time = time.perf_counter() - profile_start
    profiled_rows = profile.get("total_rows", 0)
    profiled_cols = len(profile.get("columns", {}))
    print(f"  [3] Column Profiling: {profile_time:.3f}s ({profiled_rows:,} rows, {profiled_cols} columns)")

    # Step 4: Domain Classification
    domain_start = time.perf_counter()
    domain_res = DatasetDomainClassifier.classify(parquet_path, csv_path.name)
    domain_time = time.perf_counter() - domain_start
    detected_domain = domain_res.get("domain", "Unknown")
    print(f"  [4] Domain Classification: {domain_time:.3f}s (Domain: {detected_domain})")

    # Step 5: Semantic Model & Executive Intelligence
    from app.services.workspace_service import EnterpriseWorkspaceManager
    intel_start = time.perf_counter()
    EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, f"Benchmark {size_label}", industry=detected_domain)
    EnterpriseWorkspaceManager.register_table(ws_id, dataset_id, [{"name": c, "type": "VARCHAR"} for c in profile.get("columns", {})], rows, str(parquet_path))
    sem_model = build_semantic_model(workspace_id=ws_id, force_rebuild=True)
    intel_time = time.perf_counter() - intel_start
    measures_cnt = len(sem_model.get("measures", []))
    dims_cnt = len(sem_model.get("dimensions", []))
    print(f"  [5] Semantic Model & Intelligence: {intel_time:.3f}s (Measures: {measures_cnt}, Dimensions: {dims_cnt})")

    # Step 6: DuckDB Analytical Query Throughput
    query_start = time.perf_counter()
    con = DuckDBEngine.get_connection()
    safe_path = parquet_path.as_posix()
    kpi_result = con.execute(f"""
        SELECT
            product_category,
            COUNT(*) as tx_count,
            SUM(total_amount) as total_rev,
            AVG(total_amount) as avg_order,
            AVG(discount_pct) as avg_discount
        FROM read_parquet('{safe_path}')
        GROUP BY product_category
        ORDER BY total_rev DESC
    """).fetchall()
    query_time = time.perf_counter() - query_start
    print(f"  [6] DuckDB Analytical KPI Aggregation: {query_time:.4f}s ({len(kpi_result)} categories computed)")

    total_pipeline_time = time.perf_counter() - pipeline_start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mem_mb = peak_mem / (1024 * 1024)
    throughput_rps = rows / total_pipeline_time if total_pipeline_time > 0 else 0

    print(f"  --> Total Pipeline Latency: {total_pipeline_time:.2f}s")
    print(f"  --> Peak Memory Consumption: {peak_mem_mb:.2f} MB")
    print(f"  --> Ingestion Throughput: {throughput_rps:,.0f} rows/second")

    # Cleanup raw benchmark files
    try:
        if csv_path.exists():
            csv_path.unlink()
        temp_dir.rmdir()
    except Exception:
        pass

    return {
        "size_label": size_label,
        "target_mb": target_mb,
        "actual_mb": round(actual_mb, 2),
        "rows": rows,
        "columns": profiled_cols,
        "domain": detected_domain,
        "streaming_time_s": round(stream_time, 3),
        "streaming_throughput_mbs": round(stream_throughput_mbs, 1),
        "parquet_time_s": round(parquet_time, 3),
        "parquet_size_mb": round(parquet_size_mb, 2),
        "compression_ratio": round(compression_ratio, 2),
        "profiling_time_s": round(profile_time, 3),
        "semantic_model_time_s": round(intel_time, 3),
        "analytical_query_time_s": round(query_time, 4),
        "total_pipeline_time_s": round(total_pipeline_time, 2),
        "peak_memory_mb": round(peak_mem_mb, 2),
        "throughput_rows_per_s": round(throughput_rps, 0),
        "status": "PASS",
    }


def main():
    print("=================================================================")
    print("  DECISIONLENS ENTERPRISE LARGE DATASET BENCHMARK SUITE")
    print("=================================================================")

    benchmarks = [
        ("10MB", 10.0),
        ("50MB", 50.0),
        ("100MB", 100.0),
    ]

    results = []
    for label, mb in benchmarks:
        res = benchmark_dataset(label, mb)
        results.append(res)

    print("\n=================================================================")
    print("  FINAL LARGE DATASET BENCHMARK RESULTS SUMMARY")
    print("=================================================================")
    print(f"{'Size':<8} | {'Rows':<10} | {'Stream (s)':<11} | {'Parquet (s)':<12} | {'Comp. Ratio':<12} | {'Total (s)':<10} | {'Peak RAM':<10} | {'Status':<6}")
    print("-" * 90)
    for r in results:
        print(f"{r['size_label']:<8} | {r['rows']:<10,d} | {r['streaming_time_s']:<11.2f} | {r['parquet_time_s']:<12.2f} | {r['compression_ratio']:<12.1f}x | {r['total_pipeline_time_s']:<10.2f} | {r['peak_memory_mb']:<7.1f} MB | {r['status']:<6}")

    # Write results JSON
    out_json = BACKEND_DIR / "data" / "evaluation_results" / "large_dataset_benchmark.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved detailed benchmark metrics to: {out_json}")


if __name__ == "__main__":
    main()
