// Pattern: State. The boundary is either healthy (renders children) or failed
// (renders a fallback) and "Try again" transitions it back.
import React from 'react';
import Alert from './ui/Alert.jsx';
import Button from './ui/Button.jsx';

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
        <section className="page-card" style={{ maxWidth: '640px', margin: '2rem auto', textAlign: 'center', padding: '2rem' }}>
          <h2>Something went wrong loading this view</h2>
          <Alert variant="error" title="Rendering error" className="my-4">
            {this.state.error?.message || 'An unexpected application error occurred while displaying this page.'}
          </Alert>
          <div style={{ marginTop: '1.5rem' }}>
            <Button
              variant="primary"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try again
            </Button>
          </div>
        </section>
      );
    }
    return this.props.children;
  }
}
