# webnet Codebase Audit Report

**Date:** 2025-12-01
**Scope:** Full comprehensive audit (security, performance, architecture, quality)
**Auditor:** codebase-auditor agent

---

## Executive Summary

The webnet codebase demonstrates **excellent foundational architecture** with proper multi-tenancy, RBAC, and encryption patterns. Previous audit recommendations have been largely implemented. This audit identified **2 critical**, **4 important**, and **8 minor** findings requiring attention.

| Severity | Count | Primary Categories |
|----------|-------|-------------------|
| Critical | 2 | Security (tenant isolation, SSH) |
| Important | 4 | Performance, Security |
| Minor | 8 | Code Quality, Type Safety |

**Overall Assessment:** Production-ready with the caveat that Critical findings should be addressed first. The codebase follows Django/DRF best practices and has strong tenant isolation.

---

## Findings by Severity

### Critical (Must Fix)

| # | Category | File | Line | Issue | Remediation |
|---|----------|------|------|-------|-------------|
| 1 | Security | jobs/tasks.py | 296 | Device query without customer scoping in topology_discovery | Add `customer=job.customer` to filter |
| 2 | Security | core/ssh.py | 41 | `known_hosts=None` disables SSH host verification | Implement host key verification or user acknowledgment |

### Important (Should Fix)

| # | Category | File | Line | Issue | Remediation |
|---|----------|------|------|-------|-------------|
| 3 | Security | api/views.py | 632-663 | ConfigViewSet snapshot/diff endpoints missing tenant validation | Add ObjectCustomerPermission or customer access check |
| 4 | Performance | api/views.py | 245 | N+1 query in DeviceViewSet.jobs action | Add select_related("customer", "user") |
| 5 | Performance | api/views.py | 250 | N+1 query in DeviceViewSet.snapshots action | Add select_related("device", "job") |
| 6 | Performance | api/views.py | 466-472 | JobLogsView queries without select_related | Add optimization to job and logs queries |

### Minor (Nice to Have)

| # | Category | File | Line | Issue | Remediation |
|---|----------|------|------|-------|-------------|
| 7 | Quality | settings.py | 23+ | mypy errors due to env() return type | Cast with `str(env("KEY") or "default")` |
| 8 | Quality | core/ssh.py | 22 | SSHResult type mismatch with asyncssh | Handle bytes|str|None properly |
| 9 | Quality | api/views.py | 101 | Bare except Exception in refresh endpoint | Use specific exceptions or log |
| 10 | Quality | api/consumers.py | 83 | Bare except Exception | Log exception details |
| 11 | Quality | jobs/tasks.py | 259 | neighbors list needs type annotation | Add `list[dict[str, str]]` |
| 12 | Architecture | api/views.py | 692-703 | TopologyLinkViewSet.clear deletes without confirmation | Consider adding dry_run parameter |
| 13 | Architecture | jobs/tasks.py | 185-218 | Rollback tasks are placeholder stubs | Implement or document as TODO |
| 14 | Quality | Various | - | 19 broad `except Exception` blocks | Narrow exception types or add logging |

---

## Category Summaries

### Security

**Strengths:**
- Fernet encryption for credentials with mandatory ENCRYPTION_KEY in production
- SECRET_KEY required in production (not hardcoded default)
- ALLOWED_HOSTS must be explicitly configured in production
- Rate limiting on login endpoint (5/minute via LoginRateThrottle)
- JWT authentication with proper expiration handling
- API Key authentication with hashed storage (SHA256)
- CSRF protection enabled with secure cookies in production
- HSTS configured (31536000 seconds in production)
- Password validators configured (similarity, length, common, numeric)
- WebSocket consumers properly authenticate and check tenant access

**Issues Found:**

1. **CRITICAL: Missing Customer Scoping in topology_discovery_job** (Line 296)
   ```python
   # Current - allows cross-tenant data leakage
   device = Device.objects.filter(hostname=host).first()
   
   # Required fix
   device = Device.objects.filter(hostname=host, customer=job.customer).first()
   ```

2. **CRITICAL: SSH Host Verification Disabled** (core/ssh.py:41)
   ```python
   conn = await asyncssh.connect(..., known_hosts=None)  # Vulnerable to MITM
   ```
   This disables SSH host key verification, making connections vulnerable to man-in-the-middle attacks.

3. **IMPORTANT: ConfigViewSet endpoints lack tenant validation**
   - `snapshot(pk)` - fetches any snapshot by ID
   - `device_snapshots(device_id)` - no customer check
   - `diff(device_id)` - minimal customer check but could be bypassed

### Performance

**Strengths:**
- ViewSets define queryset with select_related() at class level
- Pagination configured (PAGE_SIZE=50)
- Models have indexes on frequently queried fields
- ComplianceOverviewView uses Subquery to avoid N+1
- UI views use proper select_related/prefetch_related

**Issues Found:**

1. **N+1 Query Patterns** in DeviceViewSet action methods:
   ```python
   # Line 245 - jobs action
   jobs = Job.objects.filter(target_summary_json__device_id=pk)  # No select_related
   
   # Line 250 - snapshots action  
   snaps = ConfigSnapshot.objects.filter(device_id=pk)  # No select_related
   
   # Line 255 - topology action
   links = TopologyLink.objects.filter(local_device_id=pk)  # No select_related
   ```

2. **JobLogsView** (Line 466-472) performs two queries without optimization

### Architecture

**Strengths:**
- Clean separation of Django apps by domain
- Consistent ViewSet patterns with CustomerScopedQuerysetMixin
- Proper URL routing with DRF routers
- WebSocket consumers follow Channels patterns
- Celery tasks properly isolated with JobService abstraction
- Signals used for real-time broadcasting

**Observations:**
- ConfigViewSet uses manual URL routing rather than @action decorators (acceptable pattern)
- TopologyLinkViewSet has `clear` action that bulk-deletes (consider dry_run option)
- Placeholder tasks (rollback_preview/commit) claim success without work

### Code Quality

**Strengths:**
- Ruff linter passes with zero warnings
- Consistent code style (Black formatted)
- Good docstrings on modules and complex functions
- Type hints on most public functions
- Proper use of `from __future__ import annotations`

**Issues Found:**
- 34 mypy errors, primarily in settings.py due to env() return type
- 19 broad `except Exception` blocks that could mask issues
- SSHResult dataclass expects `str` but asyncssh returns `bytes|str|None`

### Test Coverage

**Strengths:**
- 44 tests covering critical paths
- RBAC scoping tests verify tenant isolation
- WebSocket authentication tests
- API flow tests for CRUD operations
- Tests use proper fixtures (set_encryption_key autouse)

**Test Categories:**
| Category | Files | Tests |
|----------|-------|-------|
| API Flows | 3 | 12 |
| Auth/RBAC | 4 | 10 |
| WebSocket | 4 | 12 |
| UI/HTMX | 4 | 8 |
| Integration | 2 | 2 |

**Coverage Gaps:**
- No tests for ConfigViewSet snapshot/diff methods
- Limited edge case testing for WebSocket disconnection
- Placeholder tasks lack implementation tests

### Dependencies

**Current Dependencies (pyproject.toml):**
- Django >= 5.1 (latest stable)
- djangorestframework >= 3.15.2 (latest stable)
- channels >= 4.1.0 (latest stable)
- cryptography >= 43.0.0 (latest stable)
- napalm >= 4.1.0, netmiko >= 4.4.0, nornir >= 3.4.1

**Assessment:** All major dependencies are at recent stable versions. No known CVEs in current versions.

---

## Statistics

| Metric | Count |
|--------|-------|
| Django Apps | 10 |
| Python Files | ~60 |
| Template Files | ~40 |
| Lines of Python | ~5,500 |
| API ViewSets | 12 |
| UI Views | 18 |
| Celery Tasks | 9 |
| WebSocket Consumers | 3 |
| Database Models | 10 |
| Test Files | 16 |
| Test Cases | 44 |
| Critical Issues | 2 |
| Important Issues | 4 |
| Minor Issues | 8 |

---

## Recommended Priority Actions

### Immediate (Before Production)

1. **Fix topology_discovery customer scoping** (Critical #1)
   ```python
   # backend/webnet/jobs/tasks.py line 296
   device = Device.objects.filter(hostname=host, customer=job.customer).first()
   ```

2. **Address SSH host verification** (Critical #2)
   Either implement proper host key verification or document the risk with user acknowledgment.

3. **Add tenant validation to ConfigViewSet** (Important #3)
   Add customer access checks to snapshot, device_snapshots, and diff methods.

### Short-term (Next Sprint)

4. **Fix N+1 queries in DeviceViewSet actions** (Important #4-6)
   Add select_related to jobs, snapshots, and topology actions.

5. **Add tests for ConfigViewSet endpoints**
   Verify tenant isolation with cross-customer test cases.

### Long-term

6. **Fix mypy type errors** in settings.py
7. **Replace broad except Exception** with specific exceptions
8. **Implement placeholder tasks** or mark as deprecated
9. **Add type annotations** to remaining untyped functions

---

## Appendix: Detailed Findings

### A. Critical Finding #1: Tenant Isolation Bypass in Topology Discovery

**Location:** `backend/webnet/jobs/tasks.py` lines 296-303

**Code:**
```python
for host, r in res.items():
    _log_host_result(js, job, host, r)
    device = Device.objects.filter(hostname=host).first()  # BUG: No customer filter
    if not device or r.failed:
        continue
    neighbors = _parse_cdp_neighbors(str(r.result))
    for n in neighbors:
        remote_dev = Device.objects.filter(
            customer=device.customer, hostname=n["remote_hostname"]  # This is correct
        ).first()
```

**Issue:** Line 296 queries Device by hostname only, potentially returning a device from a different customer if hostnames are reused across tenants.

**Impact:** Cross-tenant data leakage; topology links could be created referencing wrong devices.

**Fix:**
```python
device = Device.objects.filter(hostname=host, customer=job.customer).first()
```

### B. Critical Finding #2: SSH MITM Vulnerability

**Location:** `backend/webnet/core/ssh.py` line 36-42

**Code:**
```python
conn = await asyncssh.connect(
    host=host,
    port=port,
    username=username,
    password=password,
    known_hosts=None,  # VULNERABLE
)
```

**Issue:** Setting `known_hosts=None` disables SSH host key verification, making the connection vulnerable to man-in-the-middle attacks.

**Impact:** An attacker on the network path could intercept SSH credentials and commands.

**Options:**
1. **Accept first-time keys (TOFU):** Store host keys in database on first connection
2. **Require pre-configured keys:** Admin uploads known host keys
3. **User acknowledgment:** Warn user and require confirmation for unknown hosts

### C. Important Finding #3: ConfigViewSet Missing Tenant Checks

**Location:** `backend/webnet/api/views.py` lines 631-663

**Affected Methods:**
- `snapshot(pk)` - Returns any snapshot by ID without customer check
- `device_snapshots(device_id)` - Returns snapshots for any device
- `diff(device_id)` - Compares snapshots without full tenant validation

**Fix Example:**
```python
def snapshot(self, request, pk=None):
    snap = ConfigSnapshot.objects.filter(pk=pk).first()
    if not snap:
        return Response(status=status.HTTP_404_NOT_FOUND)
    # Add tenant check
    if not user_has_customer_access(request.user, snap.device.customer_id):
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(ConfigSnapshotSerializer(snap).data)
```

---

*Report generated by webnet codebase-auditor agent on 2025-12-01*
