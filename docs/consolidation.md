# Consolidation and Corporate Actions Guide

## Overview

The ORM Capital Calculator Engine provides comprehensive consolidation and corporate action management capabilities to handle entity hierarchies, multi-level capital calculations, and regulatory compliance for M&A activities. This system ensures accurate capital calculations at consolidated, sub-consolidated, and subsidiary levels while maintaining complete audit trails for regulatory disclosure.

## Key Features

### Entity Hierarchy Management
- **Multi-level Consolidation**: Support for consolidated, sub-consolidated, and subsidiary levels
- **Organizational Structure**: Parent-child entity relationships with flexible hierarchy
- **Regulatory Identifiers**: RBI entity codes and LEI (Legal Entity Identifier) support
- **Active Status Management**: Entity lifecycle management with activation/deactivation

### Corporate Actions Processing
- **Action Types**: Acquisitions, divestitures, mergers, spin-offs, and restructuring
- **RBI Approval Workflow**: Structured approval process with reference tracking
- **Disclosure Management**: Automatic Pillar 3 disclosure identification and tracking
- **Business Impact**: Automatic BI inclusion/exclusion based on action type

### Consolidation Calculations
- **Level-specific Calculations**: Capital calculations at different consolidation levels
- **Entity-own Losses**: Uses only entity's own losses at each level (per RBI requirements)
- **Corporate Action Adjustments**: Automatic inclusion of prior BI for acquisitions
- **Disclosure Tracking**: Complete audit trail for regulatory reporting

## Entity Management

### Entity Model

```python
class Entity:
    id: str                          # Unique entity identifier
    name: str                        # Entity name
    entity_type: str                 # bank, subsidiary, branch
    parent_entity_id: Optional[str]  # Parent in hierarchy
    consolidation_level: str         # consolidated, sub_consolidated, subsidiary
    rbi_entity_code: Optional[str]   # RBI regulatory code
    lei_code: Optional[str]          # Legal Entity Identifier
    is_active: bool                  # Active status
    incorporation_date: Optional[date]
    regulatory_approval_date: Optional[date]
```

### API Endpoints

#### Create Entity
```http
POST /api/v1/consolidation/entities
Authorization: Bearer <token>
Content-Type: application/json

{
    "id": "BANK_001",
    "name": "Main Bank",
    "entity_type": "bank",
    "consolidation_level": "consolidated",
    "rbi_entity_code": "RBI001",
    "lei_code": "LEI123456789",
    "incorporation_date": "2000-01-01"
}
```

#### Get Entity Hierarchy
```http
GET /api/v1/consolidation/entities/{entity_id}/hierarchy
Authorization: Bearer <token>
```

Response includes complete hierarchy with children and consolidation mappings:
```json
{
    "entity": {
        "id": "BANK_001",
        "name": "Main Bank",
        "entity_type": "bank",
        "consolidation_level": "consolidated"
    },
    "children": [
        {
            "entity": {
                "id": "SUB_001",
                "name": "Subsidiary 1",
                "parent_entity_id": "BANK_001"
            },
            "children": []
        }
    ],
    "consolidation_mappings": []
}
```

## Corporate Actions

### Corporate Action Types

1. **Acquisition**: Acquiring another entity
   - Automatically sets `prior_bi_inclusion_required = true`
   - Includes 3-year prior BI of acquired entity
   - Requires Pillar 3 disclosure

2. **Divestiture**: Selling/divesting entity or portion
   - Automatically sets `bi_exclusion_required = true`
   - Excludes divested BI from subsequent periods
   - Requires RBI approval and disclosure

3. **Merger**: Combining entities
   - Custom business logic based on merger structure
   - May require both inclusion and exclusion adjustments

4. **Spin-off**: Creating new entity from existing operations
   - Similar to divestiture with entity creation
   - Requires careful BI attribution

### Corporate Action Workflow

#### 1. Registration
```http
POST /api/v1/consolidation/corporate-actions
Authorization: Bearer <token>

{
    "id": "CA_001",
    "action_type": "acquisition",
    "target_entity_id": "SUB_001",
    "acquirer_entity_id": "BANK_001",
    "transaction_value": "1000000000",
    "ownership_percentage": "100",
    "announcement_date": "2025-08-01",
    "effective_date": "2025-08-29",
    "description": "Acquisition of Subsidiary 1"
}
```

#### 2. RBI Approval
```http
PUT /api/v1/consolidation/corporate-actions/{action_id}/approve
Authorization: Bearer <token>

?rbi_approval_reference=RBI/2025/001&approval_date=2025-08-15
```

#### 3. Completion
```http
PUT /api/v1/consolidation/corporate-actions/{action_id}/complete
Authorization: Bearer <token>

?completion_date=2025-08-29
```

### Corporate Action Status Flow

```
PROPOSED → RBI_APPROVED → COMPLETED
    ↓
CANCELLED (if needed)
```

## Consolidation Calculations

### Calculation Request

```http
POST /api/v1/consolidation/calculate
Authorization: Bearer <token>

{
    "parent_entity_id": "BANK_001",
    "consolidation_level": "consolidated",
    "calculation_date": "2025-08-29",
    "include_subsidiaries": true,
    "include_corporate_actions": true
}
```

### Consolidation Levels

#### 1. Consolidated Level
- **Scope**: All active entities in the group
- **Usage**: Full group capital calculation
- **Regulatory**: Basel III consolidated capital requirements

#### 2. Sub-consolidated Level
- **Scope**: Entities up to sub-consolidated level
- **Usage**: Regional or business line consolidation
- **Regulatory**: Sub-group capital requirements

#### 3. Subsidiary Level
- **Scope**: Individual subsidiary only
- **Usage**: Entity-specific capital calculation
- **Regulatory**: Individual entity requirements

### Calculation Logic

#### Business Indicator Consolidation
```python
# For each entity in scope:
entity_bi = get_entity_bi(entity_id, calculation_date)  # 3-year average

# Apply corporate action adjustments:
if acquisition and prior_bi_inclusion_required:
    entity_bi += get_prior_bi_for_acquisition(action, calculation_date)

if divestiture and bi_exclusion_required:
    entity_bi -= get_divested_bi(action, calculation_date)

consolidated_bi = sum(adjusted_bi for all entities)
```

#### Loss Consolidation
```python
# Use only entity's own losses at each level (RBI requirement)
for entity in entities:
    entity_losses = get_entity_losses(entity_id, 10_year_period)
    # No cross-entity loss aggregation
    
consolidated_losses = sum(entity_losses for all entities)
```

### Calculation Result

```json
{
    "parent_entity_id": "BANK_001",
    "consolidation_level": "consolidated",
    "calculation_date": "2025-08-29",
    "included_entities": ["BANK_001", "SUB_001", "SUB_002"],
    "excluded_entities": ["SUB_003"],
    "corporate_actions_applied": ["CA_001"],
    "consolidated_bi": "5000000000.00",
    "consolidated_losses": "250000000.00",
    "entity_contributions": {
        "BANK_001": {
            "business_indicator": "3000000000.00",
            "losses": "150000000.00",
            "entity_name": "Main Bank"
        },
        "SUB_001": {
            "business_indicator": "2000000000.00",
            "losses": "100000000.00",
            "entity_name": "Subsidiary 1"
        }
    },
    "disclosure_items": ["acquisition_CA_001_SUB_001"]
}
```

## Regulatory Compliance

### RBI Requirements

#### Requirement 3.1: Multi-level Calculations
- ✅ Calculate capital at consolidated, sub-consolidated, and subsidiary levels
- ✅ Use only entity's own losses at each level
- ✅ Maintain separate calculations for each level

#### Requirement 3.2: Acquisition Processing
- ✅ Immediately include prior 3-year BI of acquired entity
- ✅ Log acquisition for disclosure
- ✅ Maintain audit trail with RBI approval reference

#### Requirement 3.3: Divestiture Processing
- ✅ Exclude divested BI from subsequent periods when RBI-approved
- ✅ Log divestiture for disclosure
- ✅ Maintain 3-year retention for disclosure items

### Pillar 3 Disclosure

#### Automatic Identification
- Corporate actions requiring disclosure are automatically flagged
- Disclosure period tracking (default: 36 months)
- Disclosure item generation for regulatory reporting

#### Disclosure Items Format
```
{action_type}_{action_id}_{target_entity_id}
Example: "acquisition_CA_001_SUB_001"
```

#### Disclosure Tracking
- Effective date tracking
- Disclosure period calculation
- Automatic expiry handling
- Audit trail maintenance

## Database Schema

### Entities Table
```sql
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    parent_entity_id TEXT REFERENCES entities(id),
    consolidation_level TEXT NOT NULL,
    rbi_entity_code TEXT,
    lei_code TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    incorporation_date DATE,
    regulatory_approval_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Corporate Actions Table
```sql
CREATE TABLE corporate_actions (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    target_entity_id TEXT NOT NULL REFERENCES entities(id),
    acquirer_entity_id TEXT REFERENCES entities(id),
    transaction_value DECIMAL(15,2),
    ownership_percentage DECIMAL(5,2),
    announcement_date DATE NOT NULL,
    rbi_approval_date DATE,
    completion_date DATE,
    effective_date DATE NOT NULL,
    rbi_approval_reference TEXT,
    requires_pillar3_disclosure BOOLEAN DEFAULT TRUE,
    disclosure_period_months INTEGER DEFAULT 36,
    prior_bi_inclusion_required BOOLEAN DEFAULT FALSE,
    bi_exclusion_required BOOLEAN DEFAULT FALSE,
    description TEXT,
    additional_details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Consolidation Mappings Table
```sql
CREATE TABLE consolidation_mappings (
    id TEXT PRIMARY KEY,
    parent_entity_id TEXT NOT NULL REFERENCES entities(id),
    child_entity_id TEXT NOT NULL REFERENCES entities(id),
    consolidation_level TEXT NOT NULL,
    ownership_percentage DECIMAL(5,2) NOT NULL,
    voting_control_percentage DECIMAL(5,2),
    consolidation_method TEXT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Security and Permissions

### Required Permissions

#### Entity Management
- **CREATE/UPDATE**: `WRITE_BI_DATA` (Corporate Finance Analyst)
- **READ**: `READ_BI_DATA` (Risk Analyst and above)

#### Corporate Actions
- **CREATE**: `WRITE_BI_DATA` (Corporate Finance Analyst)
- **APPROVE**: `APPROVE_PARAMETERS` (Model Risk Manager)
- **READ**: `READ_BI_DATA` (Risk Analyst and above)

#### Consolidation Calculations
- **EXECUTE**: `CALCULATE_SMA`, `CALCULATE_BIA`, or `CALCULATE_TSA`
- **READ RESULTS**: `READ_JOBS`

### Audit Trail

All consolidation operations are logged with:
- User identification
- Timestamp
- Operation details
- Input parameters
- Results summary
- Corporate actions applied
- Disclosure items generated

## Usage Examples

### Example 1: Bank Acquisition

```python
# 1. Create acquired entity
entity_data = {
    "id": "ACQUIRED_BANK",
    "name": "Acquired Bank Ltd",
    "entity_type": "bank",
    "consolidation_level": "subsidiary"
}

# 2. Register acquisition
action_data = {
    "id": "ACQ_2025_001",
    "action_type": "acquisition",
    "target_entity_id": "ACQUIRED_BANK",
    "acquirer_entity_id": "MAIN_BANK",
    "transaction_value": "5000000000",
    "ownership_percentage": "100",
    "announcement_date": "2025-06-01",
    "effective_date": "2025-08-29"
}

# 3. Get RBI approval
# (Manual process with RBI)

# 4. Approve in system
approve_data = {
    "rbi_approval_reference": "RBI/DBR/2025/001",
    "approval_date": "2025-07-15"
}

# 5. Complete acquisition
complete_data = {
    "completion_date": "2025-08-29"
}

# 6. Calculate consolidated capital
consolidation_request = {
    "parent_entity_id": "MAIN_BANK",
    "consolidation_level": "consolidated",
    "calculation_date": "2025-08-29",
    "include_corporate_actions": true
}
```

### Example 2: Subsidiary Divestiture

```python
# 1. Register divestiture
action_data = {
    "id": "DIV_2025_001",
    "action_type": "divestiture",
    "target_entity_id": "SUBSIDIARY_A",
    "ownership_percentage": "60",  # Partial divestiture
    "announcement_date": "2025-05-01",
    "effective_date": "2025-09-01"
}

# 2. After RBI approval and completion
# 3. Calculate impact
consolidation_request = {
    "parent_entity_id": "MAIN_BANK",
    "consolidation_level": "consolidated",
    "calculation_date": "2025-09-30",
    "include_corporate_actions": true
}
# Result will exclude 60% of SUBSIDIARY_A's BI
```

## Best Practices

### Entity Management
1. **Unique Identifiers**: Use consistent entity ID format across systems
2. **Regulatory Codes**: Maintain accurate RBI entity codes and LEI codes
3. **Hierarchy Updates**: Update parent-child relationships promptly
4. **Status Management**: Deactivate entities properly when no longer active

### Corporate Actions
1. **Early Registration**: Register actions as soon as announced
2. **Documentation**: Maintain detailed descriptions and supporting documents
3. **Approval Tracking**: Track RBI approval status and references
4. **Effective Dates**: Use accurate effective dates for calculations

### Consolidation Calculations
1. **Regular Updates**: Perform calculations at regular intervals
2. **Data Quality**: Ensure underlying BI and loss data is accurate
3. **Validation**: Cross-check results with manual calculations
4. **Audit Trail**: Maintain complete audit trails for all calculations

### Compliance
1. **Disclosure Tracking**: Monitor disclosure requirements and deadlines
2. **Regulatory Updates**: Stay current with RBI guideline changes
3. **Documentation**: Maintain comprehensive documentation for audits
4. **Testing**: Regular testing of consolidation logic and calculations