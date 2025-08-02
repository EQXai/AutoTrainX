'use client'

import { Button } from '@/components/ui/button'
import { User } from 'lucide-react'

export function UserNav() {
  return (
    <Button variant="ghost" size="icon">
      <User className="h-5 w-5" />
      <span className="sr-only">User menu</span>
    </Button>
  )
}