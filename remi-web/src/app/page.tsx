'use client'

import { useState } from 'react'
import { SearchBar } from '@/components/search/SearchBar'
import { ContactSuggestions } from '@/components/contacts/ContactSuggestions'
import { RecentActivity } from '@/components/dashboard/RecentActivity'
import { QuickActions } from '@/components/dashboard/QuickActions'

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-primary">R.E.M.I</h1>
              <span className="text-sm text-muted-foreground">
                Real-time External Memory Interface
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <button className="p-2 rounded-lg hover:bg-accent transition-colors">
                <span className="sr-only">Settings</span>
                ⚙️
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Search Section */}
        <section className="mb-12">
          <div className="max-w-2xl mx-auto text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">
              Find conversations with anyone, instantly
            </h2>
            <p className="text-muted-foreground text-lg">
              Search your messages by contact, topic, or natural language queries
            </p>
          </div>
          
          <div className="max-w-4xl mx-auto">
            <SearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search for messages with John, files from Sarah, or commitments due this week..."
              className="mb-6"
            />
            
            {searchQuery && (
              <ContactSuggestions
                query={searchQuery}
                onContactSelect={(contact) => {
                  console.log('Selected contact:', contact)
                }}
              />
            )}
          </div>
        </section>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Quick Actions */}
          <div className="lg:col-span-1">
            <QuickActions />
          </div>

          {/* Recent Activity */}
          <div className="lg:col-span-2">
            <RecentActivity />
          </div>
        </div>

        {/* Feature Highlights */}
        <section className="mt-16">
          <h3 className="text-2xl font-bold text-center mb-8">
            Intelligent Communication Management
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center p-6 rounded-lg border border-border">
              <div className="text-4xl mb-4">🔍</div>
              <h4 className="text-lg font-semibold mb-2">Contact-Based Search</h4>
              <p className="text-muted-foreground">
                Find all conversations, files, and commitments related to any contact
              </p>
            </div>
            <div className="text-center p-6 rounded-lg border border-border">
              <div className="text-4xl mb-4">🤖</div>
              <h4 className="text-lg font-semibold mb-2">AI Insights</h4>
              <p className="text-muted-foreground">
                Get proactive reminders and relationship insights powered by AI
              </p>
            </div>
            <div className="text-center p-6 rounded-lg border border-border">
              <div className="text-4xl mb-4">🔄</div>
              <h4 className="text-lg font-semibold mb-2">Real-time Sync</h4>
              <p className="text-muted-foreground">
                Stay updated across all devices with instant synchronization
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}