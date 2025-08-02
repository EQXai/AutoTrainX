'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { 
  Brain, 
  LayoutDashboard, 
  Database, 
  Settings,
  FileText,
  HardDrive,
  Zap
} from 'lucide-react'

const navigation = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Jobs',
    href: '/dashboard/jobs',
    icon: Brain,
  },
  {
    name: 'Datasets',
    href: '/dashboard/datasets',
    icon: Database,
  },
  {
    name: 'Models',
    href: '/dashboard/models',
    icon: FileText,
  },
  {
    name: 'Presets',
    href: '/dashboard/presets',
    icon: Zap,
  },
  {
    name: 'Database',
    href: '/dashboard/database',
    icon: HardDrive,
  },
  {
    name: 'Settings',
    href: '/dashboard/settings',
    icon: Settings,
  },
]

export function MainNav() {
  const pathname = usePathname()

  return (
    <nav className="flex items-center space-x-4 lg:space-x-6">
      <Link href="/dashboard" className="flex items-center space-x-2">
        <Brain className="h-6 w-6" />
        <span className="font-bold">AutoTrainX</span>
      </Link>
      <div className="hidden md:flex md:space-x-4">
        {navigation.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center space-x-2 text-sm font-medium transition-colors hover:text-primary",
                pathname === item.href
                  ? "text-foreground"
                  : "text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}