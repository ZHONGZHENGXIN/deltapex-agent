import { generateStaticParamsFor, importPage } from 'nextra/pages'
import { useMDXComponents } from '@/mdx-components'

export const generateStaticParams = generateStaticParamsFor('mdxPath')

export async function generateMetadata(props: PageProps) {
  const params = await props.params

  // 检查是否为静态资源路径，如果是则跳过
  if (params.mdxPath && params.mdxPath.some(segment =>
    segment.includes('.') && (
      segment.endsWith('.svg')
      || segment.endsWith('.png')
      || segment.endsWith('.jpg')
      || segment.endsWith('.jpeg')
      || segment.endsWith('.gif')
      || segment.endsWith('.ico')
      || segment.endsWith('.css')
      || segment.endsWith('.js')
    ),
  )) {
    return {}
  }

  try {
    const { metadata } = await importPage(params.mdxPath, params.lang)
    return metadata
  }
  catch (error) {
    console.warn('Failed to load metadata for path:', params.mdxPath, error)
    return {}
  }
}

type PageProps = Readonly<{
  params: Promise<{
    mdxPath: string[]
    lang: string
  }>
}>

export default async function Page(props: PageProps) {
  const params = await props.params

  // 检查是否为静态资源路径，如果是则返回 404
  if (params.mdxPath && params.mdxPath.some(segment =>
    segment.includes('.') && (
      segment.endsWith('.svg')
      || segment.endsWith('.png')
      || segment.endsWith('.jpg')
      || segment.endsWith('.jpeg')
      || segment.endsWith('.gif')
      || segment.endsWith('.ico')
      || segment.endsWith('.css')
      || segment.endsWith('.js')
    ),
  )) {
    throw new Error('Static resource accessed as page')
  }

  try {
    const result = await importPage(params.mdxPath, params.lang)
    const { default: MDXContent, toc, metadata, sourceCode } = result
    const { wrapper: Wrapper } = useMDXComponents()

    return (
      <Wrapper toc={toc} metadata={metadata} sourceCode={sourceCode}>
        <MDXContent {...props} params={params} />
      </Wrapper>
    )
  }
  catch (error) {
    console.error('Failed to load page:', params.mdxPath, error)
    throw error
  }
}
