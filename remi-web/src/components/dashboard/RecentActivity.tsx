'use client'

import { cn } from '@/utils/cn'

interface ActivityItem {
  id: string
  type: 'message' | 'insight' | 'connection'
  title: string
  description: string
  timestamp: Date
  platform?: string
  contact?: string
}

// Mock data
const mockActivity: ActivityItem[] = [
  {
    id: '1',
    type: 'message',
    title: 'New message from John Smith',
    description: 'Hey, can we schedule that meeting for next week?',
    timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
    platform: 'gmail',
    contact: 'John Smith',
  },
  {
    id: '2',
    type: 'insight',
    title: 'Follow-up reminder',
    description: 'You promised to send the project proposal to Sarah Johnson',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
    contact: 'Sarah Johnson',
  },
  {
    id: '3',
    type: 'connection',
    title: 'Platform connected',
    description: 'Successfully connected your Slack workspace',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
    platform: 'slack',
  },
]

export function RecentActivity({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Recent Activity</h3>
        <button className="text-sm text-primary hover:underline">
          View all
        </button>
      </div>

      <div className="space-y-4">
        {mockActivity.map((item) => (
          <div
            key={item.id}
            className="flex items-start space-x-4 p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors cursor-pointer"
          >
            {/* Icon */}
            <div className="flex-shrink-0 mt-1">
              {item.type === 'message' && (
                <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <svg className="h-4 w-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                    <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                  </svg>
                </div>
              )}
              {item.type === 'insight' && (
                <div className="h-8 w-8 rounded-full bg-yellow-100 dark:bg-yellow-900 flex items-center justify-center">
                  <svg className="h-4 w-4 text-yellow-600 dark:text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
              {item.type === 'connection' && (
                <div className="h-8 w-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                  <svg className="h-4 w-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">
                  {item.title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatRelativeTime(item.timestamp)}
                </p>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {item.description}
              </p>
              <div className="flex items-center space-x-2 mt-2">
                {item.platform && (
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-secondary text-secondary-foreground">
                    {item.platform}
                  </span>
                )}
                {item.contact && (
                  <span className="text-xs text-muted-foreground">
                    {item.contact}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) {
    return 'Just now'
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes}m ago`
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600)
    return `${hours}h ago`
  } else {
    const days = Math.floor(diffInSeconds / 86400)
    return `${days}d ago`
  }
}