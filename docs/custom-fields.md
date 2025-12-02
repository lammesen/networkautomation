# Custom Fields

Custom fields allow you to add organization-specific data to models without modifying the database schema. This is useful for:

- Storing integration-specific data (e.g., ServiceNow ticket IDs)
- Tracking organization-specific attributes (e.g., asset tags, cost centers)
- Avoiding model bloat with rarely-used fields

## Supported Models

Custom fields can be added to the following models:

- **Device** - Network devices
- **Credential** - Device credentials
- **Job** - Automation jobs
- **CompliancePolicy** - Compliance policies
- **ConfigSnapshot** - Configuration snapshots
- **ConfigTemplate** - Configuration templates
- **Tag** - Device tags
- **DeviceGroup** - Device groups

## Field Types

The following field types are supported:

| Type | Description | Example |
|------|-------------|---------|
| `text` | Single-line text | Asset tag, serial number |
| `textarea` | Multi-line text | Notes, descriptions |
| `integer` | Whole numbers | Port count, VLAN ID |
| `decimal` | Decimal numbers | Cost, latitude/longitude |
| `boolean` | True/False | Is monitored, is critical |
| `date` | Date only | Purchase date, warranty expiry |
| `datetime` | Date and time | Last maintenance, next review |
| `url` | URL/Web address | Documentation link, vendor portal |
| `json` | Structured JSON data | Complex metadata |
| `select` | Single choice from list | Environment (prod/staging/dev) |
| `multiselect` | Multiple choices from list | Protocols (SSH, SNMP, NetConf) |

## API Usage

### Create a Custom Field Definition

```bash
POST /api/v1/custom-fields/
Content-Type: application/json

{
  "customer": 1,
  "name": "asset_tag",
  "label": "Asset Tag",
  "model_type": "device",
  "field_type": "text",
  "description": "Physical asset tag number",
  "required": false,
  "weight": 100,
  "is_active": true
}
```

### Create a Custom Field with Validation

```bash
POST /api/v1/custom-fields/
Content-Type: application/json

{
  "customer": 1,
  "name": "port_count",
  "label": "Port Count",
  "model_type": "device",
  "field_type": "integer",
  "description": "Number of physical ports",
  "required": true,
  "validation_min": 1,
  "validation_max": 48,
  "default_value": "24",
  "weight": 200,
  "is_active": true
}
```

### Create a Select Field

```bash
POST /api/v1/custom-fields/
Content-Type: application/json

{
  "customer": 1,
  "name": "environment",
  "label": "Environment",
  "model_type": "device",
  "field_type": "select",
  "description": "Deployment environment",
  "required": true,
  "choices": ["production", "staging", "development"],
  "default_value": "development",
  "weight": 50,
  "is_active": true
}
```

### List Custom Field Definitions

```bash
GET /api/v1/custom-fields/

# Filter by model type
GET /api/v1/custom-fields/?model_type=device

# Filter by field type
GET /api/v1/custom-fields/?field_type=text

# Filter active fields only
GET /api/v1/custom-fields/?is_active=true
```

### Using Custom Fields on Objects

Once custom field definitions are created, you can use them on the corresponding models:

```bash
# Create a device with custom fields
POST /api/v1/devices/
Content-Type: application/json

{
  "customer": 1,
  "hostname": "router1",
  "mgmt_ip": "192.168.1.1",
  "vendor": "cisco",
  "platform": "ios",
  "credential": 1,
  "custom_fields": {
    "asset_tag": "A12345",
    "port_count": 48,
    "environment": "production"
  }
}
```

```bash
# Update custom fields on an existing device
PATCH /api/v1/devices/1/
Content-Type: application/json

{
  "custom_fields": {
    "asset_tag": "A54321",
    "environment": "staging"
  }
}
```

## Validation

Custom fields support various validation options:

### Required Fields

Set `required: true` to make a field mandatory. The API will return an error if the field is missing or empty.

### Min/Max for Numeric Fields

For `integer` and `decimal` fields, you can set `validation_min` and `validation_max`:

```json
{
  "field_type": "integer",
  "validation_min": 1,
  "validation_max": 100
}
```

### Regex Validation for Text

For `text` and `textarea` fields, you can provide a regex pattern:

```json
{
  "field_type": "text",
  "validation_regex": "^[A-Z]{2}\\d{5}$"
}
```

### Choices for Select Fields

For `select` and `multiselect` fields, provide a list of valid choices:

```json
{
  "field_type": "select",
  "choices": ["option1", "option2", "option3"]
}
```

## Default Values

You can set default values for custom fields:

```json
{
  "name": "is_monitored",
  "field_type": "boolean",
  "default_value": "true"
}
```

Default values are stored as strings and converted to the appropriate type when retrieved.

## Django Admin

Custom field definitions can be managed through the Django admin interface at `/admin/core/customfielddefinition/`.

## Best Practices

1. **Naming Conventions**: Use `snake_case` for field names (e.g., `asset_tag`, `serial_number`)
2. **Descriptive Labels**: Use human-readable labels (e.g., "Asset Tag", "Serial Number")
3. **Add Descriptions**: Provide clear descriptions to help users understand the field's purpose
4. **Use Validation**: Add validation rules to ensure data quality
5. **Set Reasonable Defaults**: Provide sensible default values where appropriate
6. **Weight Fields**: Use the `weight` field to control display order (lower numbers appear first)
7. **Deactivate Instead of Delete**: Set `is_active: false` instead of deleting field definitions to preserve historical data

## Examples

### Asset Tracking

```json
{
  "name": "asset_tag",
  "label": "Asset Tag",
  "field_type": "text",
  "validation_regex": "^[A-Z]{2}\\d{6}$"
},
{
  "name": "purchase_date",
  "label": "Purchase Date",
  "field_type": "date"
},
{
  "name": "warranty_expiry",
  "label": "Warranty Expiry",
  "field_type": "date"
}
```

### Change Management

```json
{
  "name": "change_ticket",
  "label": "Change Ticket",
  "field_type": "text",
  "description": "ServiceNow change ticket number"
},
{
  "name": "change_window",
  "label": "Change Window",
  "field_type": "datetime"
}
```

### Cost Tracking

```json
{
  "name": "cost_center",
  "label": "Cost Center",
  "field_type": "text"
},
{
  "name": "annual_cost",
  "label": "Annual Cost",
  "field_type": "decimal",
  "validation_min": 0
}
```
