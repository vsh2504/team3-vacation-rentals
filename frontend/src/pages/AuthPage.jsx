// Frontend — Owner: Ranadhir Reddy Rikkala
// Feature: Identity, Platform & Admin Control — register/login page.
// Refined with role-aware messaging, validation, loading states, and accessible session handling (Step 3.1).
import React, { useState } from 'react';
import { api } from '../api/client.js';
import Alert from '../components/ui/Alert.jsx';
import Button from '../components/ui/Button.jsx';
import Badge from '../components/ui/Badge.jsx';
import { validateAuth } from '../validation/auth.js';

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('CUSTOMER'); // 'CUSTOMER' | 'HOST'
  const [fieldErrors, setFieldErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [apiSuccess, setApiSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  function validate() {
    const errs = validateAuth({ mode, email, password, fullName, role });
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setApiError('');
    setApiSuccess('');

    if (!validate()) {
      return;
    }

    setIsLoading(true);
    try {
      if (mode === 'register') {
        await api.register({
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          role,
        });
        setApiSuccess(`Account created as ${role}. Logging you in…`);
      }

      const data = await api.login({
        email: email.trim(),
        password,
      });

      onAuth(data.access_token, data.user);
    } catch (err) {
      setApiError(err.message || 'Authentication request failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  }

  function handleModeChange(newMode) {
    setMode(newMode);
    setApiError('');
    setApiSuccess('');
    setFieldErrors({});
  }

  function fillDemoAdmin() {
    setMode('login');
    setEmail('admin@staynest.local');
    setPassword('admin12345');
    setFieldErrors({});
    setApiError('');
    setApiSuccess('Demo administrator credentials filled. Click "Log in to StayNest" to proceed.');
  }

  function fillDemoHost() {
    setMode('register');
    setRole('HOST');
    setEmail('host_demo@staynest.local');
    setFullName('Demo Host');
    setPassword('password123');
    setFieldErrors({});
    setApiError('');
  }

  function fillDemoCustomer() {
    setMode('register');
    setRole('CUSTOMER');
    setEmail('customer_demo@staynest.local');
    setFullName('Demo Customer');
    setPassword('password123');
    setFieldErrors({});
    setApiError('');
  }

  return (
    <section className="auth-container">
      <h2>{mode === 'login' ? 'Sign in to StayNest' : 'Create your StayNest account'}</h2>

      {/* Segmented Mode Switcher (Requirement 8.4) */}
      <div className="auth-tabs" role="tablist" aria-label="Authentication mode selection">
        <button
          type="button"
          role="tab"
          id="tab-login"
          aria-selected={mode === 'login'}
          aria-controls="auth-form-panel"
          className={`auth-tab-btn ${mode === 'login' ? 'is-active' : ''}`}
          onClick={() => handleModeChange('login')}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          id="tab-register"
          aria-selected={mode === 'register'}
          aria-controls="auth-form-panel"
          className={`auth-tab-btn ${mode === 'register' ? 'is-active' : ''}`}
          onClick={() => handleModeChange('register')}
        >
          Create account
        </button>
      </div>

      {/* Accessible feedback panels (Requirements 8.3, 8.4) */}
      {apiError && (
        <Alert
          variant="error"
          title="Authentication error"
          onDismiss={() => setApiError('')}
        >
          {apiError}
        </Alert>
      )}

      {apiSuccess && (
        <Alert
          variant="success"
          title="Success"
          onDismiss={() => setApiSuccess('')}
        >
          {apiSuccess}
        </Alert>
      )}

      <form
        id="auth-form-panel"
        role="tabpanel"
        aria-labelledby={mode === 'login' ? 'tab-login' : 'tab-register'}
        onSubmit={handleSubmit}
        noValidate
      >
        {mode === 'register' && (
          <>
            <div className="field-group">
              <label htmlFor="reg-fullname">
                Full name <span aria-hidden="true">*</span>
              </label>
              <input
                id="reg-fullname"
                type="text"
                autoComplete="name"
                required
                value={fullName}
                onChange={(e) => {
                  setFullName(e.target.value);
                  if (fieldErrors.fullName) setFieldErrors({ ...fieldErrors, fullName: null });
                }}
                aria-invalid={Boolean(fieldErrors.fullName)}
                aria-describedby={fieldErrors.fullName ? 'fullname-error' : undefined}
                disabled={isLoading}
              />
              {fieldErrors.fullName && (
                <span id="fullname-error" className="field-error" role="alert">
                  {fieldErrors.fullName}
                </span>
              )}
            </div>

            {/* Role-aware picker (Requirement 2.1) */}
            <fieldset className="field-group" style={{ border: 'none', padding: 0 }}>
              <legend>
                <label>
                  Select account role <span aria-hidden="true">*</span>
                </label>
              </legend>
              <div className="role-picker" role="radiogroup" aria-label="Account role">
                <div
                  className={`role-card ${role === 'CUSTOMER' ? 'is-selected' : ''}`}
                  onClick={() => setRole('CUSTOMER')}
                  role="radio"
                  aria-checked={role === 'CUSTOMER'}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === ' ' || e.key === 'Enter') {
                      e.preventDefault();
                      setRole('CUSTOMER');
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <strong>Customer</strong>
                    <Badge variant="neutral">Guest</Badge>
                  </div>
                  <p>Book stays and leave reviews.</p>
                </div>

                <div
                  className={`role-card ${role === 'HOST' ? 'is-selected' : ''}`}
                  onClick={() => setRole('HOST')}
                  role="radio"
                  aria-checked={role === 'HOST'}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === ' ' || e.key === 'Enter') {
                      e.preventDefault();
                      setRole('HOST');
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <strong>Host</strong>
                    <Badge variant="primary">Host</Badge>
                  </div>
                  <p>List your properties and see their bookings.</p>
                </div>
              </div>
              {fieldErrors.role && (
                <span className="field-error" role="alert">
                  {fieldErrors.role}
                </span>
              )}
            </fieldset>
          </>
        )}

        <div className="field-group">
          <label htmlFor="auth-email">
            Email address <span aria-hidden="true">*</span>
          </label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (fieldErrors.email) setFieldErrors({ ...fieldErrors, email: null });
            }}
            placeholder="you@example.com"
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'email-error' : undefined}
            disabled={isLoading}
          />
          {fieldErrors.email && (
            <span id="email-error" className="field-error" role="alert">
              {fieldErrors.email}
            </span>
          )}
        </div>

        <div className="field-group">
          <label htmlFor="auth-password">
            Password <span aria-hidden="true">*</span>
          </label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
            minLength={8}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password) setFieldErrors({ ...fieldErrors, password: null });
            }}
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby="password-hint"
            disabled={isLoading}
          />
          <span id="password-hint" className="field-hint">
            Minimum 8 characters.
          </span>
          {fieldErrors.password && (
            <span id="password-error" className="field-error" role="alert">
              {fieldErrors.password}
            </span>
          )}
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="btn-block"
            isLoading={isLoading}
            loadingText={mode === 'login' ? 'Signing in…' : 'Creating account…'}
          >
            {mode === 'login' ? 'Log in to StayNest' : 'Create account & Sign in'}
          </Button>

          <Button
            type="button"
            variant="ghost"
            onClick={() => handleModeChange(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login'
              ? "Don't have an account? Create one"
              : 'Already have an account? Sign in'}
          </Button>
        </div>
      </form>

      {/* Demo Credentials Helper (Requirement 2.4) */}
      <aside className="demo-credentials-card" aria-label="Demo credentials helper">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <strong>Demo credentials</strong>
          <Badge variant="accent">Demo only</Badge>
        </div>
        <p style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
          Quick sign-in for testing:
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={fillDemoAdmin}
            title="Fill admin credentials (admin@staynest.local)"
          >
            Fill Demo Admin
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={fillDemoHost}
            title="Pre-fill new host registration"
          >
            Prefill Demo Host
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={fillDemoCustomer}
            title="Pre-fill new customer registration"
          >
            Prefill Demo Customer
          </Button>
        </div>
      </aside>
    </section>
  );
}
