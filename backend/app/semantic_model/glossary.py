from typing import Any, Dict, List

from app.semantic_model.core import BusinessTerm


BUSINESS_TERM_DEFINITIONS = {
    "revenue": "The total income generated from business operations before expenses.",
    "sales": "The exchange of goods or services for monetary value.",
    "profit": "The financial gain after subtracting costs and expenses from revenue.",
    "cost": "The monetary value of resources used to produce goods or deliver services.",
    "amount": "A quantity or sum of money.",
    "price": "The amount expected or given in payment for goods or services.",
    "quantity": "The number of units of a product or service involved in a transaction.",
    "discount": "A reduction applied to the usual price.",
    "tax": "A compulsory financial charge imposed by a governing authority.",
    "margin": "The difference between revenue and cost, expressed as a value or percentage.",
    "shipment": "The action of sending goods to a destination.",
    "delivery": "The process of transporting goods to a designated location.",
    "supplier": "A person or organization that supplies goods or services.",
    "warehouse": "A facility for storage of goods or materials.",
    "inventory": "A list or record of items held in stock or available for use.",
    "stock": "The quantity of goods or materials held in storage or available.",
    "employee": "A person employed for wages or salary.",
    "department": "A distinct section or division of an organization.",
    "salary": "A fixed regular payment for employment.",
    "invoice": "A document listing goods or services with prices and terms.",
    "payment": "The action of paying money for goods or services.",
    "transaction": "An instance of conducting business or an exchange of value.",
    "category": "A class or division of items with shared characteristics.",
    "subcategory": "A further division within a category.",
    "brand": "A name or mark identifying a product or service.",
    "sku": "Stock Keeping Unit; a unique identifier for a distinct product or service item.",
    "geography": "A location or region associated with business data.",
    "region": "A geographic area or administrative division.",
    "city": "A large urban area.",
    "state": "A principal territorial division of a nation.",
    "country": "A nation with its own government occupying a territory.",
    "quarter": "One of four divisions of a year, often used in reporting.",
    "year": "A period of twelve months used for reporting or planning.",
    "month": "A period of approximately four weeks used for reporting.",
    "day": "A period of 24 hours used for time-based analysis.",
}


def generate_business_glossary(
    workspace_id: str,
    domain: str,
    tables_meta: List[Dict[str, Any]],
    measures: List[str]
) -> List[Dict[str, Any]]:
    glossary: List[Dict[str, Any]] = []

    glossary.append(BusinessTerm(
        term="Business Workspace",
        definition=f"Container for multi-table dataset '{workspace_id}' in domain '{domain}'.",
        domain=domain,
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Fact Table",
        definition="Primary transactional table containing measurable business metrics and foreign keys to dimensions.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Dimension Table",
        definition="Descriptive master entity table providing context for fact table metrics through attributes and hierarchies.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Bridge Table",
        definition="Junction table resolving many-to-many relationships between dimension tables.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Lookup Table",
        definition="Reference mapping table used to enrich dimension attributes; not used for direct analytical queries.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Reference Table",
        definition="Static master data table (e.g., geography, calendar) supporting analytical queries and joins.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Primary Key",
        definition="A unique identifier for each record in a table; ensures entity integrity.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Foreign Key",
        definition="A column or set of columns in one table that references the primary key of another table, establishing a relationship.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Measure",
        definition="A numeric column that can be aggregated (summed, averaged, etc.) to produce business KPIs and metrics.",
        domain="Semantic Model",
    ).__dict__)

    glossary.append(BusinessTerm(
        term="Hierarchy",
        definition="A logical grouping of columns that represent levels of aggregation, such as Year > Quarter > Month > Day.",
        domain="Semantic Model",
    ).__dict__)

    for t in tables_meta:
        role = t.get("role", "")
        tname = t.get("table_name", "")
        row_count = t.get("row_count", 0)

        if role == "Fact Table":
            glossary.append(BusinessTerm(
                term=tname,
                definition=f"Enterprise fact table containing {row_count:,} transactional records with {len(t.get('measures', []))} measurable metrics.",
                domain=domain,
                table=tname,
            ).__dict__)
        elif role == "Dimension Table":
            glossary.append(BusinessTerm(
                term=tname,
                definition=f"Dimension table for master entity '{tname}' with {len(t.get('columns', []))} descriptive attributes and {row_count:,} records.",
                domain=domain,
                table=tname,
            ).__dict__)
        elif role == "Lookup Table":
            glossary.append(BusinessTerm(
                term=tname,
                definition=f"Lookup/mapping table providing reference data to enrich dimension attributes in '{domain}' domain.",
                domain=domain,
                table=tname,
            ).__dict__)
        elif role == "Reference Table":
            glossary.append(BusinessTerm(
                term=tname,
                definition=f"Reference master data table providing static context for analytical queries in '{domain}' domain.",
                domain=domain,
                table=tname,
            ).__dict__)

    for m in measures[:15]:
        term = m.replace("_", " ").title()
        definition = BUSINESS_TERM_DEFINITIONS.get(m.lower(), f"Numeric measure column '{m}' used for aggregation and KPI calculation in {domain}.")
        glossary.append(BusinessTerm(
            term=term,
            definition=definition,
            domain=domain,
            column=m,
        ).__dict__)

    return glossary