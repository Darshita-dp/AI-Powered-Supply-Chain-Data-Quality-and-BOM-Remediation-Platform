# ERD — Core Warehouse Model (target design)

Conformed core layer. Staging/raw carry the same grain plus audit columns; the quality
layer references core keys. This is the design target; column lists abbreviate to key
fields.

```mermaid
erDiagram
    DIM_PART {
        string part_key PK
        string source_part_number
        string normalized_part_number
        string description
        string category
        string uom
        string lifecycle_status
        string manufacturer_part_number
        string source_system
    }
    DIM_SUPPLIER {
        string supplier_key PK
        string supplier_id
        string supplier_name
        string normalized_name
        string country
        string currency
        string source_system
    }
    DIM_PLANT {
        string plant_key PK
        string plant_code
        string plant_name
        string region
    }
    DIM_WAREHOUSE {
        string warehouse_key PK
        string warehouse_code
        string plant_key FK
    }
    DIM_DATE {
        date date_key PK
    }

    FACT_BOM_RELATIONSHIP {
        string bom_rel_key PK
        string parent_part_key FK
        string child_part_key FK
        decimal quantity_per
        string uom
        string revision
        date effective_from
        date effective_to
    }
    FACT_INVENTORY {
        string part_key FK
        string warehouse_key FK
        date snapshot_date FK
        decimal on_hand_qty
        decimal on_hand_value
    }
    FACT_FUTURE_DEMAND {
        string part_key FK
        string plant_key FK
        date demand_date FK
        decimal demand_qty
    }
    FACT_PURCHASE_ORDER {
        string po_line_key PK
        string part_key FK
        string supplier_key FK
        string plant_key FK
        date order_date FK
        decimal order_qty
        decimal unit_price
        string currency
    }
    FACT_STANDARD_COST {
        string part_key FK
        string plant_key FK
        date effective_from
        decimal standard_cost
        string currency
    }
    FACT_LEAD_TIME {
        string part_key FK
        string supplier_key FK
        date effective_from
        int lead_time_days
    }
    SUPPLIER_PART {
        string supplier_key FK
        string part_key FK
        string supplier_part_number
        decimal quoted_price
        int quoted_lead_time_days
    }

    DIM_PART ||--o{ FACT_BOM_RELATIONSHIP : "parent"
    DIM_PART ||--o{ FACT_BOM_RELATIONSHIP : "child"
    DIM_PART ||--o{ FACT_INVENTORY : ""
    DIM_PART ||--o{ FACT_FUTURE_DEMAND : ""
    DIM_PART ||--o{ FACT_PURCHASE_ORDER : ""
    DIM_PART ||--o{ FACT_STANDARD_COST : ""
    DIM_PART ||--o{ FACT_LEAD_TIME : ""
    DIM_PART ||--o{ SUPPLIER_PART : ""
    DIM_SUPPLIER ||--o{ SUPPLIER_PART : ""
    DIM_SUPPLIER ||--o{ FACT_PURCHASE_ORDER : ""
    DIM_SUPPLIER ||--o{ FACT_LEAD_TIME : ""
    DIM_PLANT ||--o{ DIM_WAREHOUSE : ""
    DIM_PLANT ||--o{ FACT_FUTURE_DEMAND : ""
    DIM_PLANT ||--o{ FACT_PURCHASE_ORDER : ""
    DIM_PLANT ||--o{ FACT_STANDARD_COST : ""
    DIM_WAREHOUSE ||--o{ FACT_INVENTORY : ""
    DIM_DATE ||--o{ FACT_INVENTORY : ""
    DIM_DATE ||--o{ FACT_FUTURE_DEMAND : ""
    DIM_DATE ||--o{ FACT_PURCHASE_ORDER : ""
```

## Quality layer (design target)

```mermaid
erDiagram
    DQ_RULE {
        string rule_id PK
        string name
        string domain
        string severity
        string rule_type
        int version
    }
    DQ_RULE_EXECUTION {
        string execution_id PK
        string rule_id FK
        string batch_id
        timestamp executed_at
    }
    DQ_ISSUE {
        string issue_id PK
        string rule_id FK
        string execution_id FK
        string entity_type
        string entity_key
        string status
        decimal priority_score
    }
    DQ_ISSUE_EVIDENCE {
        string evidence_id PK
        string issue_id FK
        string field
        string failed_value
        string expected
    }
    IMPACT_CALC {
        string issue_id FK
        int affected_assemblies
        decimal demand_qty_exposed
        decimal inventory_value_exposed
        decimal po_value_exposed
    }
    REMEDIATION_PROPOSAL {
        string proposal_id PK
        string issue_id FK
        string provider
        string model
        decimal confidence
        string status
    }
    REMEDIATION_DECISION {
        string decision_id PK
        string proposal_id FK
        string reviewer
        string decision
        timestamp decided_at
    }

    DQ_RULE ||--o{ DQ_RULE_EXECUTION : ""
    DQ_RULE_EXECUTION ||--o{ DQ_ISSUE : ""
    DQ_ISSUE ||--o{ DQ_ISSUE_EVIDENCE : ""
    DQ_ISSUE ||--|| IMPACT_CALC : ""
    DQ_ISSUE ||--o{ REMEDIATION_PROPOSAL : ""
    REMEDIATION_PROPOSAL ||--o{ REMEDIATION_DECISION : ""
```
