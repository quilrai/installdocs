// @ts-check
const { themes } = require('prism-react-renderer');

const baseUrl = process.env.SITE_BASE_URL || '/';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'WhiteMatter Endpoint Agent Docs',
  tagline: 'Adapt AI Securely',
  // Favicons: one solid tile (white WM on #B080F7) in every format, so the icon
  // shows on light and dark tab bars. No prefers-color-scheme in the SVG:
  // Safari 26+ uses SVG favicons but ignores media queries in them.
  // Set here, not via `favicon`, so the ICO carries `sizes` and browsers that
  // support SVG pick the SVG. static/favicon.ico covers /favicon.ico.
  headTags: [
    {
      tagName: 'link',
      attributes: { rel: 'icon', href: `${baseUrl}img/whitematter-favicon.ico`, sizes: '32x32' },
    },
    {
      tagName: 'link',
      attributes: { rel: 'icon', type: 'image/svg+xml', href: `${baseUrl}img/whitematter-favicon.svg` },
    },
    {
      tagName: 'link',
      attributes: { rel: 'apple-touch-icon', href: `${baseUrl}img/whitematter-apple-touch-icon.png` },
    },
  ],

  url: process.env.SITE_URL || 'https://installdocs.quilrai.dev',
  baseUrl,

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
      image: 'img/whitematter-social.png',
      navbar: {
        title: '',
        logo: {
          alt: 'WhiteMatter',
          src: 'img/whitematter-logo-black.svg',
          srcDark: 'img/whitematter-logo-white.svg',
          width: 160,
          height: 16,
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
            // Native <a> so React Router does not treat /sop as a docs route
            // (href: '/sop/' 404s in `docusaurus start`). Point at index.html so
            // the static file is served locally and under SITE_BASE_URL on Pages.
            type: 'html',
            position: 'left',
            value: `<a class="navbar__link" href="${(process.env.SITE_BASE_URL || '/').replace(/\/?$/, '/')}sop/index.html">Deployment SOP</a>`,
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
            label: 'WhiteMatter',
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
              { label: 'WhiteMatter', href: 'https://www.quilr.ai/' },
              { label: 'All Docs', href: 'https://docs.quilrai.dev/' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} WhiteMatter — Adapt AI Securely.`,
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
