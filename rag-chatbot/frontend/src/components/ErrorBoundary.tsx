import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo)
    this.setState({ errorInfo })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "2rem",
            fontFamily: "sans-serif",
            background: "#0a0a0a",
            color: "#f5f5f5",
          }}
        >
          <div
            style={{
              maxWidth: 600,
              width: "100%",
              background: "#141414",
              border: "1px solid #2a2a2a",
              borderRadius: 12,
              padding: "2rem",
            }}
          >
            <h1 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: "#ef4444" }}>
              Something went wrong
            </h1>
            <p style={{ fontSize: 13, color: "#a3a3a3", marginBottom: 16 }}>
              A render error occurred. Refresh the page to try again.
            </p>
            <pre
              style={{
                background: "#0a0a0a",
                border: "1px solid #2a2a2a",
                borderRadius: 8,
                padding: "1rem",
                fontSize: 12,
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                color: "#fca5a5",
                marginBottom: 16,
              }}
            >
              {this.state.error?.toString()}
              {"\n\n"}
              {this.state.errorInfo?.componentStack}
            </pre>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: "#f5f5f5",
                color: "#0a0a0a",
                border: "none",
                borderRadius: 6,
                padding: "8px 16px",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Reload page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
