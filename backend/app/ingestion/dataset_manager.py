from pathlib import Path
from typing import Optional
import pandas as pd

from app.database.storage import ParquetStorageManager
from app.database.duckdb_engine import DuckDBEngine


class DatasetManager:
    """
    Dataset Manager provides access to dataset Parquet files and data query executions
    keyed by dataset_id, replacing in-memory singletons.
    """

    @staticmethod
    def get_parquet_path(dataset_id: str) -> Path:
        path = ParquetStorageManager.get_parquet_path(dataset_id)
        if not path.exists():
            raise FileNotFoundError(f"Dataset '{dataset_id}' not found in storage.")
        return path

    @staticmethod
    def get_dataframe(dataset_id: str, limit: Optional[int] = None) -> pd.DataFrame:
        parquet_path = DatasetManager.get_parquet_path(dataset_id)
        path_str = str(parquet_path).replace("\\", "/")
        limit_clause = f" LIMIT {limit}" if limit else ""
        sql = f"SELECT * FROM read_parquet('{path_str}'){limit_clause}"
        return DuckDBEngine.query_to_df(sql)

    @staticmethod
    def execute_sql(dataset_id: str, sql_suffix: str) -> pd.DataFrame:
        parquet_path = DatasetManager.get_parquet_path(dataset_id)
        path_str = str(parquet_path).replace("\\", "/")
        sql = f"SELECT * FROM read_parquet('{path_str}') {sql_suffix}"
        return DuckDBEngine.query_to_df(sql)