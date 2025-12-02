# Plugin Management UI Screenshots

## Plugin List Page (`/settings/plugins/`)

The plugin list page shows all installed plugins with:
- Plugin name, description, version, and author
- Enable/Disable status badges
- Loaded status indicator
- Quick actions: Health Check, Enable/Disable, Settings
- Sync Plugins button to discover new plugins
- Metadata: min/max version, dependencies

Layout:
```
┌─────────────────────────────────────────────────────────────────┐
│ Plugins                                      [Sync Plugins] btn │
│ Manage and configure webnet plugins                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ Hello World               [Enabled] [Loaded]              │  │
│ │ A simple example plugin...                                │  │
│ │ Version: 1.0.0  By: webnet Team                           │  │
│ │                                    [Health] [Disable] [⚙]│  │
│ │────────────────────────────────────────────────────────────  │
│ │ Min Version: 1.0.0  Dependencies: none                    │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ Custom Plugin            [Disabled]                        │  │
│ │ Custom functionality for...                                │  │
│ │ Version: 2.1.0  By: Acme Corp                              │  │
│ │                                    [Health] [Enable] [⚙]  │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Plugin Detail Page (`/settings/plugins/{id}/`)

The detail page has three tabs:

### Settings Tab (Default)
- Plugin information (name, version, author, install date, compatibility)
- Global settings (JSON editor)
- Health status (with details)

```
┌─────────────────────────────────────────────────────────────────┐
│ Plugins > Hello World                           [Enabled] badge │
│ A simple example plugin demonstrating webnet plugin system...   │
├─────────────────────────────────────────────────────────────────┤
│ [Settings] [Customer Configuration] [Audit Log]                 │
├─────────────────────────────────────────────────────────────────┤
│ Plugin Information                                               │
│ Name: hello_world        Version: 1.0.0                         │
│ Author: webnet Team      Installed: 2025-12-02 08:00           │
│                                                                  │
│ Global Settings                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ {                                                           │ │
│ │   "greeting_message": "Hello, World!",                      │ │
│ │   "show_timestamp": true                                    │ │
│ │ }                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ [Save Settings]                                                  │
│                                                                  │
│ Health Status                                                    │
│ ✓ Healthy                                                       │
│ Hello World plugin is running perfectly!                        │
│ Details: { "version": "1.0.0", "status": "operational" }       │
└─────────────────────────────────────────────────────────────────┘
```

### Customer Configuration Tab
- List of customer-specific configurations
- Enable/disable per customer
- Customer-specific settings override

```
┌─────────────────────────────────────────────────────────────────┐
│ [Settings] [Customer Configuration] [Audit Log]                 │
├─────────────────────────────────────────────────────────────────┤
│ Customer-Specific Configuration                                  │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ Acme Corp                                                  │  │
│ │ Enabled · Last updated: 2025-12-02 08:00                   │  │
│ │                                   [Disable] [⚙ Settings]  │  │
│ │                                                            │  │
│ │ Customer Settings (JSON)  [collapsed by default]           │  │
│ │ ┌─────────────────────────────────────────────────────┐   │  │
│ │ │ { "custom_setting": "value" }                        │   │  │
│ │ └─────────────────────────────────────────────────────┘   │  │
│ │ [Save Settings]                                            │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ Global Tech                                                │  │
│ │ Disabled · Last updated: 2025-12-01 15:30                  │  │
│ │                                    [Enable] [⚙ Settings]  │  │
│ └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Audit Log Tab
- Chronological list of all plugin actions
- Action type badges (enable, disable, configure, error)
- Success/failure indicators
- User, customer, timestamp
- Expandable details (JSON)

```
┌─────────────────────────────────────────────────────────────────┐
│ [Settings] [Customer Configuration] [Audit Log]                 │
├─────────────────────────────────────────────────────────────────┤
│ Audit Log                                                        │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ [Enable] ✓                                                 │  │
│ │ By admin · 2025-12-02 08:15:30                             │  │
│ │ > Show details                                             │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ [Configure] ✓                                              │  │
│ │ By admin for Acme Corp · 2025-12-02 08:10:00               │  │
│ │ > Show details                                             │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ [Disable] ✗                                                │  │
│ │ By operator for Global Tech · 2025-12-01 15:30:00          │  │
│ │ Error: Plugin has active dependencies                      │  │
│ │ > Show details                                             │  │
│ └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Navigation Integration

The "Plugins" menu item is added to the Admin section in the sidebar:

```
Admin
├── Users & Roles
├── Plugins          ← NEW
└── Audit Log (coming soon)
```

When on `/settings/plugins/` or any plugin page, the menu item is highlighted.

## HTMX Features

All interactive elements use HTMX for smooth, SPA-like experience:

1. **Enable/Disable buttons** - Swap plugin card in place without page reload
2. **Health Check** - Opens modal with live health status
3. **Settings forms** - Submit without page reload, show success message
4. **Tab switching** - Load content on demand via HTMX
5. **Customer config** - Toggle settings panel without reload
6. **Sync Plugins** - Trigger sync action and update list

## Responsive Design

- Uses Tailwind CSS with dark mode support
- Card-based layout for plugins
- Responsive grid/flex layouts
- Mobile-friendly forms and buttons
- Icons from Heroicons/Lucide

## Color Scheme

- **Enabled**: Green badges and buttons
- **Disabled**: Gray badges and buttons
- **Loaded**: Blue indicator badge
- **Success**: Green checkmark icons
- **Error**: Red X icons
- **Primary actions**: Blue/primary color buttons
- **Danger actions**: Red border/text for disable

## Interactive Elements

1. **Sync Plugins** - Spinner indicator during sync
2. **Enable/Disable** - Immediate visual feedback, card updates in place
3. **Health Check** - Modal dialog with formatted JSON details
4. **Settings Editor** - JSON textarea with monospace font
5. **Tabs** - Active tab highlighted with blue underline
6. **Expandable Details** - Collapsed by default, click to show
7. **Customer Settings** - Hidden by default, toggle with gear icon

This UI provides a complete, user-friendly interface for managing plugins without requiring API knowledge or command-line access.
