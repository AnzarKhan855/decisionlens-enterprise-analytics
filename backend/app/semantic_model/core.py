from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class TableRole(Enum):
    FACT = "Fact Table"
    DIMENSION = "Dimension Table"
    BRIDGE = "Bridge Table"
    LOOKUP = "Lookup Table"
    REFERENCE = "Reference Table"
    METADATA = "Metadata Table"


class SpecializedTableType(Enum):
    EMPLOYEE_TABLE = "Employee Table"
    GEOGRAPHIC_TABLE = "Geographic Table"
    TIME_TABLE = "Time Table"


class RelationshipCardinality(Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:M"


class BusinessDomain(Enum):
    RETAIL_ECOMMERCE = "Retail & E-Commerce"
    FINANCE_BANKING = "Finance & Banking"
    HEALTHCARE = "Healthcare"
    HUMAN_RESOURCES = "Human Resources"
    LOGISTICS_SUPPLY_CHAIN = "Logistics & Supply Chain"
    MANUFACTURING = "Manufacturing"
    TELECOMMUNICATIONS = "Telecommunications"
    INSURANCE = "Insurance"
    MARKETING_ADVERTISING = "Marketing & Advertising"
    SAAS_SUBSCRIPTION = "SaaS & Subscription"
    CRM_SALES = "CRM & Sales"
    GOVERNMENT_PUBLIC_SECTOR = "Government & Public Sector"
    REAL_ESTATE = "Real Estate"
    HOSPITALITY_TOURISM = "Hospitality & Tourism"
    AGRICULTURE = "Agriculture"
    ENERGY_UTILITIES = "Energy & Utilities"
    EDUCATION = "Education"
    CYBERSECURITY = "Cybersecurity"
    GENERIC_BUSINESS = "Generic Business"


class DatasetType(Enum):
    RETAIL = "Retail"
    CYBERSECURITY = "Cybersecurity"
    HEALTHCARE = "Healthcare"
    FINANCE = "Finance"
    BANKING = "Banking"
    MANUFACTURING = "Manufacturing"
    HUMAN_RESOURCES = "HR"
    MARKETING = "Marketing"
    TELECOMMUNICATIONS = "Telecom"
    INSURANCE = "Insurance"
    GOVERNMENT = "Government"
    EDUCATION = "Education"
    LOGISTICS = "Logistics"
    ENERGY = "Energy"
    MIXED = "Mixed"
    UNKNOWN = "Unknown"


class ColumnSemanticType(Enum):
    MEASURE = "measure"
    DIMENSION = "dimension"
    IDENTIFIER = "identifier"
    TEMPORAL = "temporal"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    FREE_TEXT = "free_text"
    GEOGRAPHICAL = "geographical"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    HOSTNAME = "hostname"
    USER_ID = "user_id"
    EMPLOYEE_ID = "employee_id"
    CUSTOMER_ID = "customer_id"
    PRODUCT_ID = "product_id"
    SESSION_ID = "session_id"
    TRANSACTION_ID = "transaction_id"
    SEVERITY = "severity"
    STATUS = "status"
    THREAT = "threat"
    VULNERABILITY = "vulnerability"
    ASSET = "asset"
    DEVICE = "device"
    LOG_TYPE = "log_type"
    CVE = "cve"
    MITRE_TECHNIQUE = "mitre_technique"


class TimeGrain(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    HOURLY = "hourly"
    MINUTE = "minute"
    SECOND = "second"


class PredictionTaskType(Enum):
    REGRESSION = "regression"
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    TIME_SERIES = "time_series"
    CLUSTERING = "clustering"
    ANOMALY_DETECTION = "anomaly_detection"
    FORECASTING = "forecasting"


class DataQualityDimension(Enum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    ACCURACY = "accuracy"


class AnomalyCategory(Enum):
    STATISTICAL_OUTLIER = "statistical_outlier"
    BUSINESS_OUTLIER = "business_outlier"
    UNEXPECTED_TREND = "unexpected_trend"
    RARE_EVENT = "rare_event"


@dataclass
class PrimaryKey:
    table: str
    column: str
    data_type: str
    confidence: float = 0.0
    uniqueness_ratio: float = 0.0
    null_ratio: float = 0.0
    is_primary_key: bool = False
    is_candidate_key: bool = False
    detection_basis: str = "naming_pattern+uniqueness+nullability"


@dataclass
class ForeignKey:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str = "1:N"
    confidence_score: float = 0.0
    status: str = "ACTIVE"


@dataclass
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: RelationshipCardinality = RelationshipCardinality.ONE_TO_MANY
    confidence_score: float = 0.0
    status: str = "ACTIVE_JOIN"
    relationship_type: str = "foreign_key"


@dataclass
class Hierarchy:
    hierarchy_type: str
    levels: List[str]
    table: str = ""
    description: str = ""


@dataclass
class Measure:
    name: str
    data_type: str
    table: str
    aggregation: str = "SUM"
    business_type: str = "numeric"
    description: str = ""


@dataclass
class TimeColumn:
    column: str
    data_type: str
    granularity: str = "datetime"
    is_primary_time: bool = False
    table: str = ""


@dataclass
class BusinessEntity:
    name: str
    table: str
    entity_type: str
    confidence: float = 0.0


@dataclass
class BusinessTerm:
    term: str
    definition: str
    domain: str
    table: str = ""
    column: str = ""
    synonyms: List[str] = field(default_factory=list)


@dataclass
class TableMetadata:
    table_name: str
    file_path: str = ""
    file_name: str = ""
    role: TableRole = TableRole.DIMENSION
    specialized_type: Optional[SpecializedTableType] = None
    columns: List[Dict[str, Any]] = field(default_factory=list)
    column_names: List[str] = field(default_factory=list)
    row_count: int = 0
    primary_keys: List[PrimaryKey] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    time_columns: List[TimeColumn] = field(default_factory=list)
    hierarchies: List[Hierarchy] = field(default_factory=list)
    business_entities: List[str] = field(default_factory=list)
    business_terms: List[BusinessTerm] = field(default_factory=list)
    is_fact: bool = False
    is_analytical: bool = True
    is_lookup: bool = False
    description: str = ""
    reason: str = ""
    domain: str = "Generic Business"
    profile: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticModel:
    workspace_id: str
    status: str = "READY"
    is_lookup_only: bool = False
    domain: str = "Generic Business"
    domain_confidence: float = 50.0
    domain_reason: str = ""
    domain_matched_columns: List[str] = field(default_factory=list)
    dataset_type: str = "Unknown"
    dataset_type_confidence: float = 0.0
    generated_at: str = ""
    primary_fact_table: Optional[str] = None
    tables: List[TableMetadata] = field(default_factory=list)
    table_roles: Dict[str, List[str]] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    primary_keys: Dict[Tuple[str, str], PrimaryKey] = field(default_factory=dict)
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    time_columns: List[TimeColumn] = field(default_factory=list)
    hierarchies: List[Hierarchy] = field(default_factory=list)
    business_entities: List[str] = field(default_factory=list)
    specialized_table_types: Dict[str, str] = field(default_factory=dict)
    mermaid_diagram: str = ""
    lineage: Optional[Dict[str, Any]] = None
    glossary: List[BusinessTerm] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    column_classifications: List[Dict[str, Any]] = field(default_factory=list)
    time_intelligence: List[Dict[str, Any]] = field(default_factory=list)
    kpis: List[Dict[str, Any]] = field(default_factory=list)
    prediction_preparation: Dict[str, Any] = field(default_factory=dict)
    data_quality_scores: Dict[str, Any] = field(default_factory=dict)
    anomaly_preparation: Dict[str, Any] = field(default_factory=dict)
    schema_type: str = "unknown"
    schema_type_confidence: float = 0.0


class AnomalySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KPI:
    name: str
    column: str
    table: str
    metric_type: str
    aggregation: str
    value: float
    unit: str = ""
    description: str = ""
    confidence: float = 0.0
    source_dataset: str = ""


@dataclass
class TargetVariable:
    column: str
    table: str
    variable_type: str
    confidence: float
    reason: str = ""
    is_prediction_target: bool = False


@dataclass
class PredictionCandidate:
    column: str
    table: str
    candidate_type: str
    confidence: float
    reason: str = ""
    suitable_algorithms: List[str] = field(default_factory=list)


@dataclass
class MissingValueReport:
    column: str
    table: str
    null_count: int
    null_percentage: float
    missing_value_type: str
    impact: str = ""


@dataclass
class DataQualityReport:
    overall_score: float
    total_rows: int
    total_columns: int
    columns_with_high_null_rate: List[str]
    columns_with_moderate_null_rate: List[str]
    high_cardinality_columns: List[str]
    potentially_redundant_columns: List[str]
    negative_numeric_values: Dict[str, int]
    empty_string_columns: List[str]
    duplicate_rows: int
    outliers_detected: int
    issues: List[str]


@dataclass
class Anomaly:
    column: str
    table: str
    anomaly_type: str
    severity: AnomalySeverity
    value: float
    expected_value: float
    deviation: float
    description: str = ""


@dataclass
class ColumnClassification:
    name: str
    data_type: str
    semantic_type: str
    business_role: str = ""
    unit: str = ""
    is_measure: bool = False
    is_dimension: bool = False
    is_temporal: bool = False
    is_identifier: bool = False
    confidence: float = 0.0


@dataclass
class TimeIntelligence:
    column: str
    grain: str
    is_primary: bool = False
    date_format: str = ""
    min_value: str = ""
    max_value: str = ""
    distinct_periods: int = 0
    seasonality_detected: bool = False
    trend_direction: str = "stable"
    rolling_windows: List[str] = field(default_factory=list)


@dataclass
class DataQualityScores:
    completeness: float = 100.0
    uniqueness: float = 100.0
    consistency: float = 100.0
    validity: float = 100.0
    accuracy: float = 100.0
    overall_score: float = 100.0
    null_percentage: float = 0.0
    duplicate_percentage: float = 0.0
    outlier_percentage: float = 0.0
    issues: List[str] = field(default_factory=list)


@dataclass
class PredictionPreparation:
    target_variables: List[TargetVariable] = field(default_factory=list)
    prediction_candidates: List[PredictionCandidate] = field(default_factory=list)
    recommended_task_type: str = "none"
    recommended_algorithms: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class AnomalyPreparation:
    statistical_outliers: List[Dict[str, Any]] = field(default_factory=list)
    business_outliers: List[Dict[str, Any]] = field(default_factory=list)
    unexpected_trends: List[Dict[str, Any]] = field(default_factory=list)
    rare_events: List[Dict[str, Any]] = field(default_factory=list)
    overall_risk_level: str = "LOW"
    preparation_notes: List[str] = field(default_factory=list)