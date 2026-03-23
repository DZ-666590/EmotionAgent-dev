import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-6">
          <div className="max-w-xl w-full p-8 glass-panel rounded-3xl border border-destructive/20 text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-destructive/10 text-destructive flex items-center justify-center rounded-full mb-4">
              <span className="text-2xl">⚠️</span>
            </div>
            <h1 className="text-2xl font-bold text-destructive">哎呀，页面渲染崩溃了</h1>
            <p className="text-muted-foreground">渲染界面时遇到了一些问题，这可能是由于数据格式不匹配引起的。</p>
            <div className="text-left bg-black/50 p-4 rounded-xl overflow-auto text-xs font-mono text-red-400 mt-4 max-h-48 whitespace-pre-wrap">
              {this.state.error?.toString()}
              {'\n'}
              {this.state.error?.stack}
            </div>
            <button 
              onClick={() => window.location.reload()}
              className="mt-6 px-6 py-3 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 transition-colors"
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
