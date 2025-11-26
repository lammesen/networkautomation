import { useEffect, useRef } from 'react'
import Editor, { OnMount, BeforeMount } from '@monaco-editor/react'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'

// Network device config language tokens for syntax highlighting
const CISCO_IOS_TOKENS = {
  keywords: [
    'interface', 'ip', 'address', 'no', 'shutdown', 'description', 'vlan',
    'router', 'bgp', 'ospf', 'eigrp', 'network', 'neighbor', 'route-map',
    'access-list', 'permit', 'deny', 'any', 'host', 'eq', 'gt', 'lt',
    'line', 'vty', 'console', 'password', 'login', 'transport', 'input',
    'output', 'logging', 'snmp-server', 'community', 'hostname', 'enable',
    'secret', 'service', 'banner', 'motd', 'exec', 'timeout', 'privilege',
    'aaa', 'authentication', 'authorization', 'accounting', 'tacacs',
    'radius', 'ntp', 'server', 'clock', 'timezone', 'spanning-tree',
    'portfast', 'bpduguard', 'channel-group', 'mode', 'switchport',
    'trunk', 'access', 'native', 'allowed', 'encapsulation', 'dot1q',
    'crypto', 'isakmp', 'ipsec', 'transform-set', 'tunnel', 'source',
    'destination', 'protection', 'ipsec-isakmp', 'match', 'set', 'prefix-list',
    'route-target', 'rd', 'import', 'export', 'vrf', 'definition', 'context',
  ],
  interfaces: [
    'GigabitEthernet', 'FastEthernet', 'Ethernet', 'Serial', 'Loopback',
    'Vlan', 'Port-channel', 'Tunnel', 'BVI', 'TenGigabitEthernet',
    'TwentyFiveGigE', 'FortyGigabitEthernet', 'HundredGigE', 'mgmt',
  ],
  operators: ['eq', 'neq', 'gt', 'lt', 'ge', 'le', 'range'],
}

interface CodeEditorProps {
  value: string
  onChange?: (value: string) => void
  language?: 'cisco-ios' | 'yaml' | 'json' | 'diff' | 'plaintext'
  height?: string | number
  readOnly?: boolean
  className?: string
  showLineNumbers?: boolean
  showMinimap?: boolean
  wordWrap?: 'on' | 'off' | 'wordWrapColumn' | 'bounded'
}

export function CodeEditor({
  value,
  onChange,
  language = 'plaintext',
  height = 400,
  readOnly = false,
  className,
  showLineNumbers = true,
  showMinimap = false,
  wordWrap = 'on',
}: CodeEditorProps) {
  const { resolvedTheme } = useTheme()
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null)

  // Register custom language for Cisco IOS configs
  const handleBeforeMount: BeforeMount = (monaco) => {
    // Only register if not already registered
    if (!monaco.languages.getLanguages().some((lang) => lang.id === 'cisco-ios')) {
      monaco.languages.register({ id: 'cisco-ios' })

      monaco.languages.setMonarchTokensProvider('cisco-ios', {
        defaultToken: '',
        ignoreCase: true,
        tokenizer: {
          root: [
            // Comments (lines starting with !)
            [/^!.*$/, 'comment'],
            // Interface names
            [
              new RegExp(`\\b(${CISCO_IOS_TOKENS.interfaces.join('|')})\\d*[\\/\\d]*`, 'i'),
              'type.identifier',
            ],
            // IP addresses
            [/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/\d{1,2})?\b/, 'number'],
            // MAC addresses
            [/\b[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\b/, 'number'],
            // Keywords
            [
              new RegExp(`\\b(${CISCO_IOS_TOKENS.keywords.join('|')})\\b`, 'i'),
              'keyword',
            ],
            // Numbers
            [/\b\d+\b/, 'number'],
            // Strings in quotes
            [/"[^"]*"/, 'string'],
            [/'[^']*'/, 'string'],
            // Section headers (indentation-based)
            [/^\s*\S+/, { cases: { '@keywords': 'keyword', '@default': '' } }],
          ],
        },
      })

      // Set language configuration for bracket matching, etc.
      monaco.languages.setLanguageConfiguration('cisco-ios', {
        comments: {
          lineComment: '!',
        },
        brackets: [],
        autoClosingPairs: [
          { open: '"', close: '"' },
          { open: "'", close: "'" },
        ],
      })
    }

    // Register diff language highlighting improvements
    if (!monaco.languages.getLanguages().some((lang) => lang.id === 'unified-diff')) {
      monaco.languages.register({ id: 'unified-diff' })

      monaco.languages.setMonarchTokensProvider('unified-diff', {
        tokenizer: {
          root: [
            [/^@@.*@@/, 'keyword'], // Hunk headers
            [/^\+\+\+.*/, 'type'], // New file header
            [/^---.*/, 'type'], // Old file header
            [/^\+.*/, 'string'], // Added lines
            [/^-.*/, 'invalid'], // Removed lines
            [/^\\.*/, 'comment'], // No newline at end
          ],
        },
      })
    }
  }

  const handleEditorMount: OnMount = (editor, _monaco) => {
    editorRef.current = editor
  }

  // Map our language names to Monaco language IDs
  const getMonacoLanguage = (lang: string) => {
    switch (lang) {
      case 'cisco-ios':
        return 'cisco-ios'
      case 'diff':
        return 'unified-diff'
      case 'yaml':
        return 'yaml'
      case 'json':
        return 'json'
      default:
        return 'plaintext'
    }
  }

  return (
    <div className={cn('rounded-md border overflow-hidden', className)}>
      <Editor
        height={height}
        language={getMonacoLanguage(language)}
        value={value}
        onChange={(val) => onChange?.(val ?? '')}
        theme={resolvedTheme === 'dark' ? 'vs-dark' : 'light'}
        beforeMount={handleBeforeMount}
        onMount={handleEditorMount}
        options={{
          readOnly,
          minimap: { enabled: showMinimap },
          lineNumbers: showLineNumbers ? 'on' : 'off',
          wordWrap,
          scrollBeyondLastLine: false,
          fontSize: 13,
          fontFamily: 'ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace',
          tabSize: 2,
          automaticLayout: true,
          padding: { top: 8, bottom: 8 },
          scrollbar: {
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
          },
          renderLineHighlight: readOnly ? 'none' : 'line',
          contextmenu: !readOnly,
          quickSuggestions: !readOnly,
          folding: true,
          foldingStrategy: 'indentation',
          // Diff-specific options
          renderSideBySide: false,
          // Accessibility
          accessibilitySupport: 'auto',
        }}
      />
    </div>
  )
}

// Specialized diff viewer component
interface DiffViewerProps {
  diff: string
  height?: string | number
  className?: string
}

export function DiffViewer({ diff, height = 400, className }: DiffViewerProps) {
  return (
    <CodeEditor
      value={diff}
      language="diff"
      height={height}
      readOnly
      showMinimap={false}
      className={className}
    />
  )
}

// Config viewer for network device configurations
interface ConfigViewerProps {
  config: string
  height?: string | number
  className?: string
  onChange?: (value: string) => void
  readOnly?: boolean
}

export function ConfigViewer({
  config,
  height = 400,
  className,
  onChange,
  readOnly = true,
}: ConfigViewerProps) {
  return (
    <CodeEditor
      value={config}
      onChange={onChange}
      language="cisco-ios"
      height={height}
      readOnly={readOnly}
      showMinimap={false}
      className={className}
    />
  )
}
