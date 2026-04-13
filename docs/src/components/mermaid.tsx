'use client'

import mermaid from 'mermaid'
import { useTheme } from 'next-themes'
import { useEffect, useRef } from 'react'


// Unique ID for Mermaid container
let i = 0

/**
 * Mermaid component to render diagrams from mermaid syntax.
 * It automatically adapts to the current theme (light/dark).
 * @param {object} props - The component props.
 * @param {string} props.children - The mermaid syntax string.
 * @returns {JSX.Element} The rendered mermaid diagram.
 */
export function Mermaid({ children }: { children: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const { resolvedTheme } = useTheme()
  const id = `mermaid-svg-${i++}`

  useEffect(() => {
    if (ref.current && children) {
      // Set the theme based on the current resolved theme
      const theme = resolvedTheme === 'dark' ? 'dark' : 'default'
      mermaid.initialize({ startOnLoad: false, theme })

      mermaid.render(id, children).then(({ svg }) => {
        if (ref.current) {
          ref.current.innerHTML = svg
        }
      })
    }
  }, [children, id, resolvedTheme])

  return (
    <div ref={ref} key={id} />
  )
}
