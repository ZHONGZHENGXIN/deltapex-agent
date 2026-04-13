'use client'

import { useTheme } from 'nextra-theme-docs'
import { useMemo } from 'react'
import Marquee from 'react-fast-marquee'
import { PanelParticles } from '@/components/PanelParticles'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { HoverEffect } from '@/components/ui/card-hover-effect'
import { useLocale } from '@/hooks'
import { cn } from '@/lib/utils'
import { Section } from './Section'
import { SetupHero } from './Setup'

export const StackItem = ({
  className,
}: {
  className: string
},
) => {
  return (
    <div className={cn(
      'mx-6 size-[50px]',
      'text-neutral-800 dark:text-neutral-100',
      'transition-all duration-300 transform opacity-75',
      'hover:scale-125 hover:opacity-100',
      className,
    )}
    >
    </div>
  )
}

export default function HomepageHero() {
  const { t } = useLocale()

  const featureList = t('featureList')
  const faqs = t('faqs')

  const { resolvedTheme } = useTheme()

  const processedFeatureList = useMemo(() => {
    const icons = [
      'icon-[material-symbols--rocket-launch-outline]',
      'icon-[icon-park-outline--international]',
      'icon-[nonicons--typescript-16]',
      'icon-[carbon--face-satisfied] hover:icon-[carbon--face-wink]',
      'icon-[teenyicons--tailwind-outline]',
      'icon-[tabler--calendar-code]',
      'icon-[carbon--color-palette]',
      'icon-[carbon--ibm-cloud-transit-gateway]',
      'icon-[carbon--flash]',
    ]

    const iconStyles = [
      { bg: 'bg-sky-100 dark:bg-sky-900/40', text: 'text-sky-500 dark:text-sky-400' },
      { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-500 dark:text-red-400' },
      { bg: 'bg-yellow-100 dark:bg-yellow-900/40', text: 'text-yellow-500 dark:text-yellow-400' },
      { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-500 dark:text-green-400' },
      { bg: 'bg-indigo-100 dark:bg-indigo-900/40', text: 'text-indigo-500 dark:text-indigo-400' },
      { bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-500 dark:text-purple-400' },
      { bg: 'bg-pink-100 dark:bg-pink-900/40', text: 'text-pink-500 dark:text-pink-400' },
      { bg: 'bg-slate-100 dark:bg-slate-900/40', text: 'text-slate-500 dark:text-slate-400' },
      { bg: 'bg-orange-100 dark:bg-orange-900/40', text: 'text-orange-500 dark:text-orange-400' },
    ]

    return featureList.map((item, index) => {
      const style = iconStyles[index] || iconStyles[0]
      return {
        ...item,
        icon: <span className={cn(icons[index] || icons[0], style.text)}></span>,
        iconBgClassName: style.bg,
      }
    })
  }, [featureList])

  return (
    <>
      <PanelParticles />
      <SetupHero />
      <div className="relative top-[-18px] mb-[-10px] flex justify-center py-[0px] z-2">
        <a
          href="https://nextjs.org"
          target="_blank"
          rel="noopener noreferrer"
          className="w-[150px] h-[40px] flex flex-col items-center gap-[20px]"
        >
          <img
            className="dark:invert"
            src="/img/next.svg"
            style={{ width: '100%', height: 'auto' }}
          />
        </a>
      </div>
      <div className="relative z-1 pb-10 md:pb-[100px]">
        <Section
          title="Tech Stack"
          titleProps={{
            disabledAnimation: false,
          }}
        >
          <div className="flex justify-center w-full max-w-7xl h-[80px] my-[30px]">
            <Marquee
              pauseOnHover
              autoFill
              gradient
              direction="right"
              gradientColor="var(--background)"
              speed={60}
            >
              <StackItem className="icon-[akar-icons--nextjs-fill]" />
              <StackItem className="icon-[simple-icons--react]" />
              <StackItem className="icon-[simple-icons--tailwindcss]" />
              <StackItem className="icon-[teenyicons--framer-outline]" />
              <StackItem className="icon-[simple-icons--shadcnui]" />
              <StackItem className="icon-[simple-icons--typescript]" />
              <StackItem className="icon-[fa6-brands--sass]" />
              <StackItem className="icon-[teenyicons--eslint-outline]" />
              <StackItem className="icon-[simple-icons--postcss]" />
              <StackItem className="icon-[simple-icons--nextra]" />
              <StackItem className="icon-[line-md--iconify1]" />
            </Marquee>
          </div>
        </Section>
        <Section
          title="Features"
          description={t('featuresDesc')}
        >
          <div className="flex justify-center w-full max-w-7xl">
            <HoverEffect items={processedFeatureList} />
          </div>
        </Section>
        <Section
          title="Frequently Asked Questions"
          tallPaddingY
        >
          <Accordion
            type="single"
            collapsible
            className="w-full max-w-5xl"
          >
            {
              faqs.map((faqItem, index) => (
                <AccordionItem
                  value={faqItem.question}
                  key={index}
                >
                  <AccordionTrigger>{faqItem.question}</AccordionTrigger>
                  <AccordionContent>
                    {faqItem.answer}
                  </AccordionContent>
                </AccordionItem>
              ))
            }
          </Accordion>
        </Section>
      </div>
    </>
  )
}
