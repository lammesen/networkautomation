import { useSearchParams } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/page-header'
import { UsersTab } from './UsersTab'
import { CustomersTab } from './CustomersTab'
import { CredentialsTab } from './CredentialsTab'
import { Users, Building2, Key } from 'lucide-react'

const TABS = [
  { value: 'users', label: 'Users', icon: Users },
  { value: 'customers', label: 'Customers', icon: Building2 },
  { value: 'credentials', label: 'Credentials', icon: Key },
] as const

type TabValue = typeof TABS[number]['value']

export function AdminView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as TabValue) || 'users'

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Administration"
        description="Manage users, customers, and credentials"
      />

      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
          {TABS.map(({ value, label, icon: Icon }) => (
            <TabsTrigger key={value} value={value} className="gap-2">
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <UsersTab />
        </TabsContent>

        <TabsContent value="customers" className="space-y-4">
          <CustomersTab />
        </TabsContent>

        <TabsContent value="credentials" className="space-y-4">
          <CredentialsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
