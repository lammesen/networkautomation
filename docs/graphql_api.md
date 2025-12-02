# GraphQL API

The webnet application provides a GraphQL API endpoint at `/api/graphql/` for flexible and efficient data querying. The API is built using [Strawberry GraphQL for Django](https://strawberry.rocks/docs/integrations/django) and supports authentication via JWT tokens and API keys.

## Features

- **Customer-scoped queries**: All queries automatically filter data based on user's assigned customers
- **Role-based access**: Admin users can access all customers, while viewers/operators are limited to their assigned customers
- **Efficient data fetching**: GraphQL reduces over-fetching and under-fetching compared to REST
- **Nested queries**: Fetch related data in a single request (e.g., device + jobs + configs)
- **GraphiQL interface**: Interactive API explorer available in development mode

## Endpoint

- **URL**: `/api/graphql/`
- **Development**: GraphiQL interface enabled at the same URL (visit in browser)
- **Production**: GraphiQL disabled (set `graphiql=False` in `urls.py`)

## Authentication

The GraphQL API supports two authentication methods:

### 1. JWT Token (recommended)

First, obtain a JWT token via the REST API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

Use the token in GraphQL requests:

```bash
curl -X POST http://localhost:8000/api/graphql/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ me { username role } }"}'
```

### 2. API Key

Generate an API key via the UI or REST API, then use it:

```bash
curl -X POST http://localhost:8000/api/graphql/ \
  -H "X-API-Key: <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ me { username role } }"}'
```

Or with Authorization header:

```bash
curl -X POST http://localhost:8000/api/graphql/ \
  -H "Authorization: ApiKey <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ me { username role } }"}'
```

## Schema Overview

### Core Types

- **Customer**: Multi-tenant organization
- **User**: User account with role-based permissions
- **Device**: Network device (router, switch, etc.)
- **Credential**: Device authentication credentials (passwords hidden)
- **Job**: Automation job (config backup, compliance check, etc.)
- **JobLog**: Job execution log entries
- **ConfigSnapshot**: Configuration backup
- **ConfigTemplate**: Jinja2 configuration template
- **CompliancePolicy**: Compliance policy definition
- **ComplianceResult**: Compliance check results
- **Tag**: Device organizational tags
- **DeviceGroup**: Static or dynamic device grouping
- **TopologyLink**: Network topology connections

## Example Queries

### Get Current User

```graphql
query {
  me {
    id
    username
    email
    role
    customers {
      id
      name
    }
  }
}
```

### List Customers

```graphql
query {
  customers {
    id
    name
    description
    sshHostKeyPolicy
  }
}
```

### List Devices with Filters

```graphql
query {
  devices(vendor: "cisco", role: "router", limit: 10) {
    id
    hostname
    mgmtIp
    vendor
    platform
    role
    site
    enabled
    customer {
      name
    }
    credential {
      name
      username
    }
    tags {
      name
      color
    }
  }
}
```

### Get Single Device with Related Data

```graphql
query {
  device(id: 1) {
    hostname
    mgmtIp
    vendor
    jobs {
      id
      type
      status
      requestedAt
    }
    configSnapshots {
      id
      createdAt
      source
    }
    tags {
      name
      color
    }
  }
}
```

### List Jobs

```graphql
query {
  jobs(customerId: 1, status: "success", limit: 20) {
    id
    type
    status
    requestedAt
    startedAt
    finishedAt
    user {
      username
    }
    customer {
      name
    }
  }
}
```

### Get Job with Logs

```graphql
query {
  job(id: 123) {
    type
    status
    requestedAt
    finishedAt
    logs(limit: 100) {
      ts
      level
      host
      message
    }
  }
}
```

### Complex Nested Query

```graphql
query {
  customers {
    name
    devices {
      hostname
      vendor
      platform
      tags {
        name
        color
      }
      credential {
        name
        username
      }
    }
    jobs {
      type
      status
      requestedAt
    }
  }
}
```

### Configuration Snapshots

```graphql
query {
  configSnapshots(deviceId: 1, limit: 10) {
    id
    createdAt
    source
    hash
    device {
      hostname
    }
    job {
      type
      status
    }
  }
}
```

### Compliance Policies and Results

```graphql
query {
  compliancePolicies(customerId: 1) {
    id
    name
    description
    createdAt
    results(limit: 5) {
      status
      ts
      device {
        hostname
      }
    }
  }
}
```

### Topology Links

```graphql
query {
  topologyLinks(deviceId: 1, limit: 50) {
    id
    localDevice {
      hostname
    }
    localInterface
    remoteDevice {
      hostname
    }
    remoteInterface
    remoteHostname
    protocol
    discoveredAt
  }
}
```

## Query Parameters

Most list queries support optional filtering parameters:

### Device Queries

- `customerId`: Filter by customer ID
- `hostname`: Filter by hostname (partial match)
- `vendor`: Filter by vendor (partial match)
- `platform`: Filter by platform (partial match)
- `role`: Filter by role (partial match)
- `site`: Filter by site (partial match)
- `enabled`: Filter by enabled status (boolean)
- `limit`: Maximum results to return (default: 100)

### Job Queries

- `customerId`: Filter by customer ID
- `status`: Filter by status (queued, running, success, failed, etc.)
- `type`: Filter by type (config_backup, compliance_check, etc.)
- `limit`: Maximum results to return (default: 100)

## Security

### Customer Scoping

All queries are automatically scoped to the authenticated user's assigned customers:

- **Admin users**: Can access all customers
- **Operator/Viewer users**: Limited to their assigned customers only

Queries for resources outside the user's scope will return empty results or `null`.

### Sensitive Data Protection

- Credential passwords and enable passwords are **never** exposed via GraphQL
- Only usernames and credential names are returned
- All queries require authentication

### Rate Limiting

Consider implementing rate limiting at the nginx/reverse proxy level:

```nginx
limit_req_zone $binary_remote_addr zone=graphql:10m rate=10r/s;

location /api/graphql/ {
    limit_req zone=graphql burst=20;
    proxy_pass http://backend;
}
```

## Development

### GraphiQL Interface

When running in development mode with `DEBUG=true`, visit `http://localhost:8000/api/graphql/` in your browser to access the interactive GraphiQL interface.

Features:
- Query editor with syntax highlighting
- Auto-completion (Ctrl+Space)
- Query history
- Documentation explorer (click "Docs" in the top-right)
- Variables editor
- Response formatting

### Adding New Types

1. Create a Strawberry type in `backend/webnet/graphql_api/types.py`:

```python
@strawberry_django_type(MyModel)
class MyModelType:
    id: auto
    name: auto
    description: auto
```

2. Add queries in `backend/webnet/graphql_api/queries.py`:

```python
@strawberry.field(permission_classes=[IsAuthenticated])
def my_models(self, info: Info, limit: int = 100) -> List[MyModelType]:
    user = get_user_from_info(info)
    customer_ids = get_customer_ids_for_user(user)
    return list(MyModel.objects.filter(customer_id__in=customer_ids)[:limit])
```

3. Add tests in `backend/webnet/tests/test_graphql_api.py`

## Performance

### Query Optimization

The GraphQL implementation uses:

- **DjangoOptimizerExtension**: Automatically optimizes database queries with `select_related()` and `prefetch_related()`
- **Explicit field selection**: Only requested fields are fetched
- **Pagination**: All list queries have default limits

### Best Practices

1. **Use pagination**: Always specify reasonable `limit` parameters
2. **Request only needed fields**: Don't request unnecessary nested data
3. **Filter early**: Use `customerId`, `deviceId`, etc. filters when possible
4. **Monitor query complexity**: Deep nesting can impact performance

## Troubleshooting

### Authentication Errors

```
{
  "errors": [{
    "message": "User is not authenticated"
  }]
}
```

**Solution**: Ensure you're sending a valid JWT token or API key in the request headers.

### Empty Results

If queries return empty arrays when data should exist:

1. Check user's assigned customers
2. Verify customer scoping is correct
3. Confirm the user's role (viewer/operator/admin)

### Field Name Errors

GraphQL uses camelCase for field names:

- ❌ `mgmt_ip`
- ✅ `mgmtIp`

- ❌ `customer_id`
- ✅ `customerId`

## Comparison with REST API

| Feature | REST API | GraphQL API |
|---------|----------|-------------|
| Endpoint | Multiple (`/api/v1/devices/`, `/api/v1/jobs/`) | Single (`/api/graphql/`) |
| Over-fetching | Common | None (request only needed fields) |
| Under-fetching | Requires multiple requests | Single request with nested queries |
| Versioning | URL-based (`/api/v1/`, `/api/v2/`) | Additive schema evolution |
| Caching | Easy (HTTP caching) | Requires custom implementation |
| Learning curve | Lower | Higher |
| Use case | Simple CRUD, public APIs | Complex queries, integrations |

Both APIs are available and coexist. Choose based on your use case:

- **Use REST for**: Simple CRUD operations, public-facing APIs, mobile apps
- **Use GraphQL for**: Complex dashboards, integrations, custom tooling

## Further Reading

- [Strawberry GraphQL Documentation](https://strawberry.rocks/)
- [GraphQL Official Documentation](https://graphql.org/learn/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
