interface AppHeaderProps {
  projectName: string
}

// Minimal app header showing the project name. No UI framework — plain elements keep
// deps light. Design systems replace this with their own header component.
export default function AppHeader({ projectName }: AppHeaderProps) {
  return (
    <header
      style={{
        alignItems: 'center',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        padding: '12px 24px'
      }}
    >
      <strong>{projectName}</strong>
    </header>
  )
}
