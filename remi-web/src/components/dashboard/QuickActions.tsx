'use client'

import { cn } from '@/utils/cn'

interface QuickAction {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  onClick: () => void
  color: 'blue' | 'green' | 'purple' | 'orange'
}

const quickActions: QuickAction[] = [
  {
    id: 'search-contacts',
    title: 'Search Contacts',
    description: 'Find conversations with specific people',
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    onClick: () => console.log('Search contacts'),
    color: 'blue',
  },
  {
    id: 'view-insights',
    title: 'View Insights',
    description: 'Check AI-generated relationship insights',
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    onClick: () => console.log('View insights'),
    color: 'purple',
  },
  {
    id: 'connect-platform',
    title: 'Connect Platform',
    description: 'Add a new communication platform',
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
    ),
    onClick: () => console.log('Connect platform'),
    color: 'green',
  },
  {
    id: 'export-data',
    title: 'Export Data',
    description: 'Download your communication data',
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    onClick: () => console.log('Export data'),
    color: 'orange',
  },
]

export function QuickActions({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      <h3 className="text-lg font-semibold">Quick Actions</h3>
      
      <div className="grid grid-cols-1 gap-4">
        {quickActions.map((action) => (
          <button
            key={action.id}
            onClick={action.onClick}
            className={cn(
              'p-4 rounded-lg border border-border text-left transition-all duration-200',
              'hover:shadow-md hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
              'group'
            )}
          >
            <div className="flex items-start space-x-3">
              <div
                className={cn(
                  'flex-shrink-0 p-2 rounded-lg transition-colors',
                  action.color === 'blue' && 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400',
                  action.color === 'green' && 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400',
                  action.color === 'purple' && 'bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-400',
                  action.color === 'orange' && 'bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-400'
                )}
              >
                {action.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                  {action.title}
                </h4>
                <p className="text-xs text-muted-foreground mt-1">
                  {action.description}
                </p>
              </div>
              <div className="flex-shrink-0">
                <svg
                  className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}