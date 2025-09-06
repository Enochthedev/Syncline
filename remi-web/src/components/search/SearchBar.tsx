'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { cn } from '@/utils/cn'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  onFocus?: () => void
  onBlur?: () => void
  autoFocus?: boolean
}

export function SearchBar({
  value,
  onChange,
  placeholder = 'Search messages, contacts, or files...',
  className,
  onFocus,
  onBlur,
  autoFocus = false,
}: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const debouncedValue = useDebounce(value, 300)

  const handleFocus = useCallback(() => {
    setIsFocused(true)
    onFocus?.()
  }, [onFocus])

  const handleBlur = useCallback(() => {
    setIsFocused(false)
    onBlur?.()
  }, [onBlur])

  const handleClear = useCallback(() => {
    onChange('')
    inputRef.current?.focus()
  }, [onChange])

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])

  return (
    <div className={cn('relative', className)}>
      <div
        className={cn(
          'relative flex items-center rounded-lg border border-border bg-background transition-all duration-200',
          isFocused && 'ring-2 ring-ring ring-offset-2 ring-offset-background',
          'hover:border-primary/50'
        )}
      >
        {/* Search Icon */}
        <div className="absolute left-3 flex items-center justify-center">
          <svg
            className="h-5 w-5 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          className={cn(
            'w-full bg-transparent py-3 pl-10 pr-12 text-sm placeholder:text-muted-foreground',
            'focus:outline-none focus:ring-0',
            'disabled:cursor-not-allowed disabled:opacity-50'
          )}
        />

        {/* Clear Button */}
        {value && (
          <button
            onClick={handleClear}
            className="absolute right-3 flex items-center justify-center p-1 rounded-md hover:bg-accent transition-colors"
            type="button"
          >
            <svg
              className="h-4 w-4 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Search Suggestions Indicator */}
      {debouncedValue && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
        </div>
      )}
    </div>
  )
}