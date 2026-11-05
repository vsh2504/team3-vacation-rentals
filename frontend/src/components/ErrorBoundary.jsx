import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>Something went wrong loading this view.</h2>
          <p role="alert" style={{ color: 'red' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </button>
        </section>
      );
    }
    return this.props.children;
  }
}
