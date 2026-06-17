// @ts-check
const { themes } = require('prism-react-renderer');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Quilr Endpoint Agent Docs',
  tagline: 'Adapt AI Securely',
  favicon: 'img/favicon.ico',

  url: process.env.SITE_URL || 'https://installdocs.quilrai.dev',
  baseUrl: process.env.SITE_BASE_URL || '/',

  organizationName: 'quilr-ai',
  projectName: 'endpoint-agent-docs',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  // Treat .md as CommonMark (no MDX/JSX parsing). Our guides contain
  // inline <bracketed> placeholders and XML snippets that confuse MDX 3.
  // .mdx files (the index, etc.) still get full MDX features.
  markdown: {
    format: 'detect',
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  clientModules: [require.resolve('./src/clientModules/platform-filter.js')],
  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      /** @type {import('@easyops-cn/docusaurus-search-local').PluginOptions} */
      ({
        hashed: true,
        indexDocs: true,
        indexBlog: false,
        indexPages: false,
        docsRouteBasePath: '/',
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
        searchBarShortcut: true,
        searchBarShortcutHint: true,
        searchResultLimits: 12,
        searchResultContextMaxLength: 80,
      }),
    ],
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: undefined,
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      image: 'img/QuilrAI-light.png',
      navbar: {
        title: '',
        logo: {
          alt: 'Quilr AI',
          src: 'img/QuilrAI-light.png',
          srcDark: 'img/QuilrAI-dark.png',
          width: 120,
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'mainSidebar',
            position: 'left',
            label: 'Endpoint Agent',
          },
          {
            type: 'docSidebar',
            sidebarId: 'extensionSidebar',
            position: 'left',
            label: 'Browser Extension',
          },
          {
            href: '/sop/',
            label: 'Deployment SOP',
            position: 'left',
          },
          {
            type: 'search',
            position: 'right',
          },
          {
            href: 'https://docs.quilrai.dev/',
            label: 'All Docs',
            position: 'right',
          },
          {
            href: 'https://www.quilr.ai/',
            label: 'Quilr.ai',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Endpoint Agent',
            items: [
              { label: 'Microsoft Intune — Windows (MSI)', to: '/deployment/intune-windows' },
              { label: 'Microsoft Intune — macOS (pkg)', to: '/deployment/intune-macos' },
              { label: 'Jamf Pro', to: '/deployment/jamf' },
              { label: 'Kandji', to: '/deployment/kandji' },
            ],
          },
          {
            title: 'Reference',
            items: [
              { label: 'Troubleshooting', to: '/reference/troubleshooting' },
              { label: 'URL Exception List — AI', to: '/reference/url-exceptions-ai' },
              { label: 'URL Exception List — Non-AI', to: '/reference/url-exceptions-nonai' },
            ],
          },
          {
            title: 'More',
            items: [
              { label: 'Quilr.ai', href: 'https://www.quilr.ai/' },
              { label: 'All Docs', href: 'https://docs.quilrai.dev/' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Quilr AI — Adapt AI Securely.`,
      },
      prism: {
        theme: themes.github,
        darkTheme: themes.dracula,
        additionalLanguages: ['bash', 'powershell', 'xml-doc', 'json', 'yaml', 'ini', 'docker'],
      },
      docs: {
        sidebar: {
          hideable: true,
          autoCollapseCategories: false,
        },
      },
      tableOfContents: {
        minHeadingLevel: 2,
        maxHeadingLevel: 4,
      },
    }),
};

module.exports = config;
