import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <div className="container flex flex-col items-center justify-center gap-12 px-4 py-16">
        <h1 className="text-5xl font-extrabold tracking-tight sm:text-[5rem]">
          AutoTrain<span className="text-primary">X</span>
        </h1>
        <p className="text-xl text-muted-foreground">
          Advanced ML Model Training Pipeline
        </p>
        <div className="flex gap-4">
          <Button asChild size="lg">
            <Link href="/dashboard">
              Go to Dashboard
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/docs">
              Documentation
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}