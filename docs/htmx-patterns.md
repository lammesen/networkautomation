# HTMX Patterns & Conventions

This guide covers HTMX patterns, conventions, and best practices used in the webnet application.

## Table of Contents
- [Template Structure](#template-structure)
- [Partial Templates](#partial-templates)
- [HTMX Attributes](#htmx-attributes)
- [Form Handling](#form-handling)
- [WebSocket Integration](#websocket-integration)
- [Common Patterns](#common-patterns)
- [Best Practices](#best-practices)

## Template Structure

### Base Template
All pages extend `base.html`:

```html
{% extends "base.html" %}
{% block title %}Page Title - webnet{% endblock %}

{% block content %}
<div class="container mx-auto p-6">
  <!-- Page content -->
</div>
{% endblock %}
```

### Page Structure Pattern
```html
{% extends "base.html" %}
{% block title %}Devices - webnet{% endblock %}

{% block content %}
<div class="page-header">
  <h1 class="page-title">Devices</h1>
  <p class="page-subtitle">Manage network device inventory</p>
</div>

<div class="card">
  <!-- Main content -->
</div>
{% endblock %}
```

## Partial Templates

### Naming Convention
- **Partials**: Prefix with `_` (e.g., `_table.html`, `_modal.html`)
- **Full pages**: No prefix (e.g., `list.html`, `detail.html`)

### Location
- Partials: `backend/templates/{app}/_*.html`
- Full pages: `backend/templates/{app}/*.html`

### Example: Table Partial
```html
{# devices/_table.html #}
<div class="relative w-full overflow-auto">
  <table class="table-grid">
    <thead>
      <tr class="table-head-row">
        <th class="table-head-cell">Hostname</th>
        <th class="table-head-cell">Status</th>
      </tr>
    </thead>
    <tbody>
      {% for device in devices %}
      <tr class="table-row">
        <td class="table-cell">{{ device.hostname }}</td>
        <td class="table-cell">
          <span class="badge {% if device.enabled %}badge-success{% else %}badge-error{% endif %}">
            {{ device.enabled|yesno:"Enabled,Disabled" }}
          </span>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

### Including Partials
```html
{# In main template #}
<div id="devices-table">
  {% include "devices/_table.html" %}
</div>
```

## HTMX Attributes

### Core Attributes

| Attribute | Purpose | Example |
|-----------|---------|---------|
| `hx-get` | Load content via GET | `hx-get="/devices/"` |
| `hx-post` | Submit form via POST | `hx-post="/devices/create/"` |
| `hx-target` | Where to swap content | `hx-target="#devices-table"` |
| `hx-swap` | How to swap (innerHTML, outerHTML, beforeend, etc.) | `hx-swap="innerHTML"` |
| `hx-trigger` | When to trigger (load, click, change, etc.) | `hx-trigger="load"` |
| `hx-indicator` | Loading indicator element | `hx-indicator="#loading"` |
| `hx-confirm` | Confirmation dialog | `hx-confirm="Delete device?"` |
| `hx-headers` | Custom headers (CSRF) | `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` |

### Common Patterns

#### Lazy Loading Table
```html
<div id="devices-table"
     hx-get="{% url 'devices-partial' %}"
     hx-trigger="load"
     hx-target="#devices-table"
     hx-swap="innerHTML">
  <div class="animate-pulse">Loading...</div>
</div>
```

#### Filter with Auto-Refresh
```html
<select name="vendor"
        hx-get="/devices/"
        hx-trigger="change"
        hx-target="#devices-table"
        hx-swap="innerHTML">
  <option value="">All Vendors</option>
  <option value="cisco">Cisco</option>
  <option value="juniper">Juniper</option>
</select>
```

#### Form Submission with Partial Update
```html
<form hx-post="/devices/create/"
      hx-target="#devices-table"
      hx-swap="innerHTML"
      hx-indicator="#loading">
  {% csrf_token %}
  <input type="text" name="hostname" required>
  <button type="submit">Create Device</button>
</form>
<div id="loading" class="htmx-indicator">Creating...</div>
```

#### Delete with Confirmation
```html
<button hx-delete="/devices/{{ device.id }}/delete/"
        hx-confirm="Delete {{ device.hostname }}?"
        hx-target="#devices-table"
        hx-swap="innerHTML"
        class="btn-danger">
  Delete
</button>
```

## Form Handling

### CSRF Protection
Always include CSRF token in forms:

```html
<form hx-post="/devices/create/">
  {% csrf_token %}
  <!-- form fields -->
</form>
```

For AJAX requests without forms, use headers:
```html
<div hx-post="/api/devices/"
     hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  <!-- content -->
</div>
```

### Form Validation
Server returns partial with errors on validation failure:

```python
# In view
if form.is_valid():
    device = form.save()
    return render(request, "devices/_table.html", {"devices": devices})
else:
    return render(request, "devices/_form.html", {"form": form}, status=400)
```

```html
{# _form.html #}
<form hx-post="/devices/create/"
      hx-target="#form-container"
      hx-swap="innerHTML">
  {% csrf_token %}
  {{ form.hostname }}
  {% if form.hostname.errors %}
    <div class="error">{{ form.hostname.errors }}</div>
  {% endif %}
  <button type="submit">Create</button>
</form>
```

### Success Handling
Return updated partial after successful submission:

```python
# View returns updated table
return render(request, "devices/_table.html", {"devices": Device.objects.all()})
```

## WebSocket Integration

### Auto-Refresh on Updates
The base template includes WebSocket handling that auto-refreshes tables:

```javascript
// In base.html
function handleUpdate(msg) {
  const refreshMap = {
    'job': { path: '/jobs/', target: '#jobs-table', url: '/jobs/' },
    'device': { path: '/devices/', target: '#devices-table', url: '/devices/' },
  };
  
  const config = refreshMap[msg.entity];
  if (config && path.startsWith(config.path)) {
    htmx.ajax('GET', config.url, { 
      target: config.target, 
      swap: 'innerHTML' 
    });
  }
}
```

### Manual Refresh Trigger
Trigger HTMX refresh from JavaScript:

```javascript
// After WebSocket message
htmx.ajax('GET', '/devices/', {
  target: '#devices-table',
  swap: 'innerHTML'
});
```

## Common Patterns

### Modal Dialog Pattern
```html
{# _modal.html #}
<div id="device-modal" class="modal">
  <div class="modal-content">
    <form hx-post="/devices/create/"
          hx-target="#devices-table"
          hx-swap="innerHTML"
          hx-on::after-request="document.getElementById('device-modal').close()">
      {% csrf_token %}
      <!-- form fields -->
      <button type="submit">Create</button>
    </form>
  </div>
</div>
```

### Search with Debounce
```html
<input type="search"
       name="search"
       hx-get="/devices/"
       hx-trigger="keyup changed delay:500ms"
       hx-target="#devices-table"
       hx-swap="innerHTML"
       placeholder="Search devices...">
```

### Pagination
```html
<div class="pagination">
  {% if page.has_previous %}
    <a hx-get="/devices/?page={{ page.previous_page_number }}"
       hx-target="#devices-table"
       hx-swap="innerHTML">Previous</a>
  {% endif %}
  
  <span>Page {{ page.number }} of {{ page.paginator.num_pages }}</span>
  
  {% if page.has_next %}
    <a hx-get="/devices/?page={{ page.next_page_number }}"
       hx-target="#devices-table"
       hx-swap="innerHTML">Next</a>
  {% endif %}
</div>
```

### Loading States
```html
<div hx-get="/devices/"
     hx-trigger="load"
     hx-indicator="#loading">
  <div id="loading" class="htmx-indicator">
    <div class="spinner">Loading...</div>
  </div>
  <div id="content">
    <!-- Content loads here -->
  </div>
</div>
```

### Error Handling
```html
<div hx-get="/devices/"
     hx-target="#devices-table"
     hx-swap="innerHTML"
     hx-on::htmx:response-error="alert('Error loading devices')">
  <div id="devices-table"></div>
</div>
```

## Best Practices

### 1. Always Use Partials for Swappable Content
✅ **Good:**
```html
<div id="table-container">
  {% include "devices/_table.html" %}
</div>
```

❌ **Bad:**
```html
<div id="table-container">
  <table><!-- full table markup --></table>
</div>
```

### 2. Use Semantic Swap Strategies
- `innerHTML`: Replace content inside element (most common)
- `outerHTML`: Replace entire element
- `beforeend`: Append to end (for lists)
- `afterbegin`: Prepend to beginning

### 3. Provide Loading Feedback
Always include loading indicators:
```html
<div hx-get="/devices/" hx-indicator="#loading">
  <div id="loading" class="htmx-indicator">Loading...</div>
</div>
```

### 4. Handle Errors Gracefully
```python
# In view
try:
    devices = Device.objects.all()
    return render(request, "devices/_table.html", {"devices": devices})
except Exception as e:
    return render(request, "devices/_error.html", {"error": str(e)}, status=500)
```

### 5. Use HTMX Events for Complex Logic
```html
<div hx-post="/devices/create/"
     hx-on::after-request="
       if (event.detail.xhr.status === 201) {
         showToast('Device created');
         closeModal();
       }
     ">
```

### 6. Combine with React Islands When Needed
For complex interactivity, use React Islands:
```html
<div data-island="DataTable" 
     data-props='{{ table_props_json }}'>
  <!-- React component handles complex table logic -->
</div>
```

### 7. Keep Partials Focused
Each partial should have a single responsibility:
- `_table.html`: Table display
- `_form.html`: Form inputs
- `_modal.html`: Modal wrapper
- `_filters.html`: Filter controls

### 8. Use URL Patterns Consistently
- List: `/devices/`
- Detail: `/devices/{id}/`
- Partial: `/devices/?partial=1` or separate endpoint `/devices/partial/`

## Integration with Views

### Django View Pattern
```python
class DeviceListView(TenantScopedView):
    template_name = "devices/list.html"
    partial_name = "devices/_table.html"
    
    def get(self, request):
        devices = self.filter_by_customer(Device.objects.all())
        
        # Check if HTMX partial request
        if request.headers.get('HX-Request'):
            return render(request, self.partial_name, {"devices": devices})
        
        # Full page request
        return render(request, self.template_name, {"devices": devices})
```

### URL Configuration
```python
# urls.py
urlpatterns = [
    path("devices/", views.DeviceListView.as_view(), name="devices-list"),
    # Partial endpoint (optional)
    path("devices/partial/", views.DeviceListPartialView.as_view(), name="devices-partial"),
]
```

## Debugging Tips

1. **Check HTMX Request Header**
   ```python
   if request.headers.get('HX-Request'):
       # HTMX request
   ```

2. **View HTMX Events in Console**
   ```javascript
   document.body.addEventListener('htmx:beforeRequest', (e) => {
     console.log('HTMX Request:', e.detail);
   });
   ```

3. **Inspect Swap Target**
   Ensure `hx-target` selector exists in DOM before HTMX swap.

4. **Check CSRF Token**
   Verify CSRF token is included in form or headers.

5. **Verify Response Format**
   HTMX expects HTML, not JSON (unless using `hx-swap-oob`).

## References

- [HTMX Documentation](https://htmx.org/docs/)
- [HTMX Events](https://htmx.org/reference/#events)
- [HTMX Attributes](https://htmx.org/attributes/)
