import React from "react";

type Props = { children: React.ReactNode };
type State = { hasError: boolean; error: Error | null };

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError && this.state.error) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background text-foreground">
          <h1 className="text-xl font-semibold text-destructive mb-2">Something went wrong</h1>
          <p className="text-sm text-muted-foreground mb-4 max-w-md text-center">
            This page failed to load. Try refreshing. If it keeps happening, check the browser console for details.
          </p>
          <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-w-full max-h-40 text-left">
            {this.state.error.message}
          </pre>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium"
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
