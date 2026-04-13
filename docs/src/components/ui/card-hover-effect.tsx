'use client'

import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { cn } from '@/lib/utils'


export const Card = ({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) => {
  return (
    <div
      className={cn(
        'relative rounded-2xl h-full w-full p-8 overflow-hidden',
        'border duration-500',
        'bg-background dark:bg-black',
        'border-black/[0.1] dark:border-white/[0.2]',
        'transition-all duration-500',
        'shadow-md shadow-black/[0.05]',
        'hover:shadow-xl hover:shadow-black/[0.1]',
        'dark:shadow-md dark:shadow-white/[0.05]',
        'dark:hover:shadow-xl dark:hover:shadow-white/[0.1]',
        'transform-gpu hover:-translate-x-2 hover:-translate-y-2',
        className,
      )}
      style={{
        background: 'radial-gradient(circle, rgba(100, 100, 100, 0.05) 0%, rgba(255, 255, 255, 0) 50%)',
      }}
    >
      {children}
    </div>
  )
}

export const CardIcon = ({
  className,
  children,
}: {
  className?: string
  children?: React.ReactNode
}) => {
  return (
    <div className={cn(
      'absolute top-4 right-4',
      'flex justify-center items-center',
      'rounded-[6px]',
      'size-[64px]',
      'text-[32px]',
      'transition-all duration-300 group-hover:scale-[12] group-hover:opacity-50',
      className,
    )}
    >
      {children}
    </div>
  )
}
export const CardTitle = ({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) => {
  return (
    <h4 className={cn(
      'text-zinc-800 dark:text-zinc-100',
      'font-bold tracking-wide text-xl pr-16',
      'origin-left transition-all duration-300',
      'group-hover:text-black dark:group-hover:text-white group-hover:scale-[1.2]',
      className,
    )}
    >
      {children}
    </h4>
  )
}

export const CardDescription = ({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) => {
  return (
    <p
      className={cn(
        'mt-4 tracking-wide leading-relaxed text-base pr-16',
        'text-zinc-600 dark:text-zinc-400',
        'origin-left transition-all duration-300',
        'group-hover:text-zinc-800 dark:group-hover:text-zinc-200 group-hover:scale-[1.1]',
        className,
      )}
    >
      {children}
    </p>
  )
}

export const HoverEffect = ({
  items,
  className,
}: {
  items: {
    title: string
    description: string
    link?: string
    icon: ReactNode
    iconBgClassName?: string
  }[]
  className?: string
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  return (
    <div
      className={cn(
        'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 py-[10px]',
        className,
      )}
    >
      {items.map((item, idx) => (
        <div
          key={idx}
          className="relative group block p-4 h-full w-full"
          onMouseEnter={() => setHoveredIndex(idx)}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          <AnimatePresence>
            {hoveredIndex === idx && (
              <motion.span
                className="z-[-1] absolute inset-0 h-full w-full bg-neutral-200/[0.3] dark:bg-neutral-500/[0.5] block rounded-3xl"
                layoutId="hoverBackground"
                initial={{ opacity: 0 }}
                animate={{
                  opacity: 1,
                  transition: { duration: 0.5 },
                }}
                exit={{
                  opacity: 0,
                  transition: { duration: 0.3, delay: 0.2 },
                }}
              />
            )}
          </AnimatePresence>
          <Card>
            <CardIcon className={item.iconBgClassName}>{item.icon}</CardIcon>
            <CardTitle>{item.title}</CardTitle>
            <CardDescription>{item.description}</CardDescription>
          </Card>
        </div>
      ))}
    </div>
  )
}
