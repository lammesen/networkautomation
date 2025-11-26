import React, { createContext, useContext, useMemo, useState } from "react"
import { cn } from "@/lib/utils"

type TabsContextValue = {
  value: string
  setValue: (val: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string
  defaultValue?: string
  onValueChange?: (val: string) => void
  children: React.ReactNode
}

export function Tabs({ value, defaultValue, onValueChange, children, className }: TabsProps) {
  const [internal, setInternal] = useState(defaultValue || "")
  const current = value !== undefined ? value : internal

  const ctx = useMemo<TabsContextValue>(
    () => ({
      value: current,
      setValue: (val) => {
        setInternal(val)
        onValueChange?.(val)
      },
    }),
    [current, onValueChange]
  )

  return (
    <TabsContext.Provider value={ctx}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

function useTabsContext() {
  const ctx = useContext(TabsContext)
  if (!ctx) throw new Error("Tabs components must be used within <Tabs>")
  return ctx
}

export const TabsList: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div
    className={cn(
      "inline-flex h-10 items-center justify-center rounded-md bg-slate-100 p-1 text-slate-500",
      "dark:bg-slate-800 dark:text-slate-400",
      className
    )}
    {...props}
  >
    {children}
  </div>
)

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({ value, children, className, ...props }) => {
  const { value: current, setValue } = useTabsContext()
  const active = current === value
  return (
    <button
      type="button"
      className={cn(
        "inline-flex min-w-[100px] items-center justify-center whitespace-nowrap rounded-sm px-3 py-1 text-sm font-medium transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        active
          ? "bg-white text-slate-900 shadow dark:bg-slate-900 dark:text-slate-50"
          : "text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-50",
        className
      )}
      aria-pressed={active}
      onClick={() => setValue(value)}
      {...props}
    >
      {children}
    </button>
  )
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

export const TabsContent: React.FC<TabsContentProps> = ({ value, children, className, ...props }) => {
  const { value: current } = useTabsContext()
  if (current !== value) return null
  return (
    <div
      className={cn(
        "mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2",
        "dark:ring-offset-slate-900",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
