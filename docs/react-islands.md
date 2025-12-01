# React Islands Guide

Guide to using React Islands in the webnet application for interactive components within HTMX-rendered pages.

## Table of Contents
- [Overview](#overview)
- [When to Use Islands](#when-to-use-islands)
- [Creating an Island](#creating-an-island)
- [Registering Islands](#registering-islands)
- [Using Islands in Templates](#using-islands-in-templates)
- [Props and Data Flow](#props-and-data-flow)
- [HTMX Integration](#htmx-integration)
- [Hydration Lifecycle](#hydration-lifecycle)
- [Best Practices](#best-practices)

## Overview

React Islands are isolated React components that hydrate specific parts of an HTMX-rendered page. They provide interactivity where HTMX alone isn't sufficient, while maintaining the server-rendered architecture.

### Architecture

- **95% HTMX**: Server-rendered templates with HTMX for dynamic updates
- **5% React Islands**: Interactive components requiring complex client-side logic
- **Island Registry**: Central registry in `backend/static/src/islands.tsx`
- **Auto-Hydration**: Islands automatically hydrate on page load and after HTMX swaps

## When to Use Islands

### ✅ Use React Islands For:
- Complex data tables with sorting/filtering
- Interactive charts and visualizations
- Real-time WebSocket components (e.g., terminal)
- Rich form components (date pickers, autocomplete)
- Drag-and-drop interfaces
- Complex state management

### ❌ Don't Use Islands For:
- Simple forms (use HTMX)
- Static content (use templates)
- Basic tables (use HTMX partials)
- Simple buttons/links (use HTMX)

## Creating an Island

### 1. Create Component File

```tsx
// backend/static/src/components/islands/MyIsland.tsx
import * as React from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

interface MyIslandProps {
  items: Array<{ id: number; name: string; status: string }>;
  actionUrl: string;
  onUpdate?: () => void;
}

export default function MyIsland({ items, actionUrl, onUpdate }: MyIslandProps) {
  const [selected, setSelected] = React.useState<number[]>([]);
  const htmx = (window as any).htmx;

  const handleAction = (id: number) => {
    htmx.ajax('POST', `${actionUrl}${id}/`, {
      target: '#result',
      swap: 'innerHTML',
      values: { id }
    });
    
    if (onUpdate) {
      onUpdate();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>My Island Component</CardTitle>
      </CardHeader>
      <CardContent>
        {items.map(item => (
          <div key={item.id} className="flex items-center justify-between p-2">
            <span>{item.name}</span>
            <Button onClick={() => handleAction(item.id)}>
              Action
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

### 2. Component Structure

```tsx
// Standard island component structure
import * as React from "react";
import { /* shadcn components */ } from "../ui/...";

interface MyIslandProps {
  // Define props interface
}

export default function MyIsland(props: MyIslandProps) {
  // Component logic
  return (
    // JSX
  );
}
```

## Registering Islands

### Add to Registry

```tsx
// backend/static/src/islands.tsx
import MyIsland from "./components/islands/MyIsland";

const islandComponents: Record<string, React.ComponentType<any>> = {
  // ... existing components
  DataTable,
  JobsTable,
  MyIsland,  // Add here
};
```

### Export Pattern

Islands should use default export:

```tsx
// ✅ Good
export default function MyIsland() { }

// ❌ Bad
export function MyIsland() { }
export const MyIsland = () => { }
```

## Using Islands in Templates

### Basic Usage

```html
{# backend/templates/myfeature/list.html #}
<div data-island="MyIsland" 
     data-props='{{ island_props_json|escapejs }}'>
</div>
```

### Generating Props JSON

```python
# In Django view
from django.http import JsonResponse
import json

def my_view(request):
    items = MyModel.objects.filter(customer_id=customer_id)
    
    island_props = {
        "items": [
            {"id": item.id, "name": item.name, "status": item.status}
            for item in items
        ],
        "actionUrl": "/api/my-action/"
    }
    
    context = {
        "island_props_json": json.dumps(island_props),
        "items": items
    }
    return render(request, "myfeature/list.html", context)
```

### Props Format

Props are passed as JSON string in `data-props` attribute:

```html
<div data-island="MyIsland" 
     data-props='{"items": [{"id": 1, "name": "Item 1"}], "actionUrl": "/api/action/"}'>
</div>
```

**Important**: Use `|escapejs` filter to escape JSON for HTML:

```html
data-props='{{ props_json|escapejs }}'
```

## Props and Data Flow

### Props Interface

Define TypeScript interface for props:

```tsx
interface MyIslandProps {
  // Primitive types
  title: string;
  count: number;
  enabled: boolean;
  
  // Arrays
  items: Array<{ id: number; name: string }>;
  
  // Objects
  config: {
    apiUrl: string;
    timeout: number;
  };
  
  // Optional
  onUpdate?: () => void;
}
```

### Accessing HTMX

Islands can interact with HTMX:

```tsx
export default function MyIsland({ actionUrl }: MyIslandProps) {
  const htmx = (window as any).htmx;
  
  const handleClick = () => {
    htmx.ajax('POST', actionUrl, {
      target: '#result',
      swap: 'innerHTML',
      values: { key: 'value' }
    });
  };
  
  return <Button onClick={handleClick}>Submit</Button>;
}
```

### Updating Parent HTMX Content

Islands can trigger HTMX updates:

```tsx
const refreshTable = () => {
  htmx.ajax('GET', '/devices/', {
    target: '#devices-table',
    swap: 'innerHTML'
  });
};
```

## HTMX Integration

### Triggering HTMX from Islands

```tsx
export default function DeviceFilters({ filters }: DeviceFiltersProps) {
  const htmx = (window as any).htmx;
  
  const handleFilterChange = (vendor: string) => {
    htmx.ajax('GET', `/devices/?vendor=${vendor}`, {
      target: '#devices-table',
      swap: 'innerHTML'
    });
  };
  
  return (
    <Select onValueChange={handleFilterChange}>
      {/* options */}
    </Select>
  );
}
```

### Receiving Updates from HTMX

Islands automatically re-hydrate after HTMX swaps. Use effects to react:

```tsx
export default function MyIsland({ items }: MyIslandProps) {
  React.useEffect(() => {
    // React to prop changes after HTMX swap
    console.log('Items updated:', items);
  }, [items]);
  
  return <div>{/* render items */}</div>;
}
```

## Hydration Lifecycle

### Initial Hydration

1. Page loads with `data-island` attributes
2. `islands.tsx` scans DOM for islands
3. Components hydrate with props from `data-props`
4. React components mount

### Re-Hydration After HTMX Swap

1. HTMX swaps content
2. `htmx:afterSwap` event fires
3. Island hydrator scans new content
4. Existing islands update, new islands mount

### Code Flow

```tsx
// backend/static/src/islands.tsx

// Initial hydration on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", hydrateIslands);
} else {
  hydrateIslands();
}

// Re-hydrate after HTMX swaps
document.body.addEventListener("htmx:afterSwap", (e) => {
  hydrateIslands(e.detail.target);
});

document.body.addEventListener("htmx:afterSettle", (e) => {
  hydrateIslands(e.detail.target);
});
```

## Best Practices

### 1. Keep Islands Focused
Each island should have a single responsibility:

```tsx
// ✅ Good - focused component
export default function DeviceTable({ devices }: DeviceTableProps) {
  // Table logic only
}

// ❌ Bad - too many responsibilities
export default function DevicePage({ devices, filters, actions }: Props) {
  // Table + filters + actions
}
```

### 2. Use shadcn Components
Leverage existing UI components:

```tsx
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Table } from "../ui/table";
```

### 3. Handle Missing HTMX Gracefully
```tsx
const htmx = (window as any).htmx;
if (!htmx) {
  console.warn("HTMX not available");
  return <div>HTMX required</div>;
}
```

### 4. Type Props Correctly
```tsx
// ✅ Good - typed interface
interface Props {
  items: Array<{ id: number; name: string }>;
}

// ❌ Bad - any types
function MyIsland(props: any) { }
```

### 5. Provide Fallback Content
```html
<div data-island="MyIsland" data-props='{{ props_json }}'>
  <!-- Fallback for no-JS -->
  <noscript>
    <div>JavaScript required for this component</div>
  </noscript>
</div>
```

### 6. Avoid Direct DOM Manipulation
```tsx
// ✅ Good - React state
const [count, setCount] = React.useState(0);

// ❌ Bad - direct DOM
document.getElementById('count').textContent = count.toString();
```

### 7. Clean Up Effects
```tsx
React.useEffect(() => {
  const timer = setInterval(() => {
    // Update
  }, 1000);
  
  return () => clearInterval(timer);  // Cleanup
}, []);
```

## Examples

### Data Table Island
```tsx
// backend/static/src/components/islands/DataTable.tsx
import * as React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";

interface DataTableProps {
  columns: Array<{ key: string; label: string }>;
  rows: Array<Record<string, any>>;
}

export default function DataTable({ columns, rows }: DataTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map(col => (
            <TableHead key={col.key}>{col.label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, idx) => (
          <TableRow key={idx}>
            {columns.map(col => (
              <TableCell key={col.key}>{row[col.key]}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Interactive Filter Island
```tsx
// backend/static/src/components/islands/FilterBar.tsx
import * as React from "react";
import { Input } from "../ui/input";
import { Select } from "../ui/select";

interface FilterBarProps {
  vendors: string[];
  onFilter: (filters: Record<string, string>) => void;
}

export default function FilterBar({ vendors, onFilter }: FilterBarProps) {
  const [search, setSearch] = React.useState("");
  const [vendor, setVendor] = React.useState("");
  
  React.useEffect(() => {
    const timer = setTimeout(() => {
      onFilter({ search, vendor });
    }, 500);
    return () => clearTimeout(timer);
  }, [search, vendor]);
  
  return (
    <div className="flex gap-4">
      <Input
        placeholder="Search..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <Select value={vendor} onValueChange={setVendor}>
        <option value="">All Vendors</option>
        {vendors.map(v => (
          <option key={v} value={v}>{v}</option>
        ))}
      </Select>
    </div>
  );
}
```

## Building Islands

### Build Command
```bash
make backend-build-js
```

### Watch Mode (Development)
```bash
make backend-watch
```

### Build Configuration
Build configuration is in `backend/esbuild.config.js`. Islands are bundled into `backend/staticfiles/src/islands.js`.

## Debugging

### Check Island Registration
```javascript
// In browser console
console.log(window.islandComponents);  // Should show registered components
```

### Verify Props Parsing
```tsx
export default function MyIsland(props: MyIslandProps) {
  console.log('Island props:', props);  // Debug props
  return <div>{/* ... */}</div>;
}
```

### Check Hydration
Islands log hydration events:
```
[Islands] Found 3 islands to hydrate
[Islands] Hydrating: DataTable
[Islands] DataTable props parsed: ["columns", "rows"]
```

## References

- [HTMX Patterns](./htmx-patterns.md)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [React Documentation](https://react.dev/)
