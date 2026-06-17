/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  // Top-bar tab #1: "Endpoint Agent" — everything except the browser extension.
  mainSidebar: [
    { type: 'doc', id: 'index',         label: 'Overview' },
    { type: 'doc', id: 'prerequisites', label: 'Prerequisites' },
    {
      type: 'category',
      label: 'Deployment Guides',
      collapsed: false,
      items: [
        {
          type: 'category',
          label: 'Microsoft Intune',
          collapsed: false,
          items: [
            { type: 'doc', id: 'deployment/intune-macos',   label: 'macOS (pkg)' },
            { type: 'doc', id: 'deployment/intune-windows', label: 'Windows (MSI)' },
          ],
        },
        {
          type: 'category',
          label: 'Jamf Pro',
          collapsed: false,
          items: [
            { type: 'doc', id: 'deployment/jamf',           label: 'macOS' },
          ],
        },
        {
          type: 'category',
          label: 'Kandji',
          collapsed: false,
          items: [
            { type: 'doc', id: 'deployment/kandji',         label: 'macOS' },
          ],
        },
        {
          type: 'category',
          label: 'ManageEngine Endpoint Central',
          collapsed: false,
          items: [
            { type: 'doc', id: 'deployment/manageengine-msi', label: 'Windows (MSI)' },
          ],
        },
        {
          type: 'category',
          label: 'Manual',
          collapsed: false,
          items: [
            { type: 'doc', id: 'deployment/macos-manual',   label: 'macOS' },
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      collapsed: false,
      items: [
        { type: 'doc', id: 'reference/validate-installation', label: 'Validate Installation' },
        { type: 'doc', id: 'reference/troubleshooting',       label: 'Troubleshooting' },
        { type: 'doc', id: 'reference/pac-configuration',     label: 'PAC Configuration' },
        { type: 'doc', id: 'reference/zcc-coexistence',      label: 'ZCC Coexistence' },
        { type: 'doc', id: 'reference/url-exceptions-ai',     label: 'URL Exception List — AI Apps' },
        { type: 'doc', id: 'reference/url-exceptions-nonai',  label: 'URL Exception List — Non-AI Apps' },
      ],
    },
  ],

  // Top-bar tab #2: "Browser Extension" — same vendor grouping as Endpoint Agent.
  extensionSidebar: [
    { type: 'doc', id: 'extension/index', label: 'Overview' },
    { type: 'doc', id: 'prerequisites',   label: 'Prerequisites' },
    {
      type: 'category',
      label: 'Deployment Guides',
      collapsed: false,
      items: [
        {
          type: 'category',
          label: 'Microsoft Intune',
          collapsed: false,
          items: [
            { type: 'doc', id: 'extension/intune-macos',   label: 'macOS (pkg)' },
            { type: 'doc', id: 'extension/intune-windows', label: 'Windows (MSI)' },
          ],
        },
        {
          type: 'category',
          label: 'Jamf Pro',
          collapsed: false,
          items: [
            { type: 'doc', id: 'extension/jamf',           label: 'macOS' },
          ],
        },
        {
          type: 'category',
          label: 'Kandji',
          collapsed: false,
          items: [
            { type: 'doc', id: 'extension/kandji',         label: 'macOS' },
          ],
        },
        {
          type: 'category',
          label: 'ManageEngine Endpoint Central',
          collapsed: false,
          items: [
            { type: 'doc', id: 'extension/manageengine-msi', label: 'Windows (MSI)' },
          ],
        },
        {
          type: 'category',
          label: 'Manual',
          collapsed: false,
          items: [
            { type: 'doc', id: 'extension/macos-manual',   label: 'macOS' },
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      collapsed: false,
      items: [
        { type: 'doc', id: 'extension/validate-installation', label: 'Validate Installation' },
        { type: 'doc', id: 'extension/troubleshooting',       label: 'Troubleshooting' },
      ],
    },
  ],
};

module.exports = sidebars;
