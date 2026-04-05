import { render, screen } from '@testing-library/react';
import { AuthGate } from '../AuthGate';
import '@testing-library/jest-dom';
import { beforeEach, describe, it, expect, vi } from 'vitest';

describe('AuthGate', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        clear: vi.fn()
      },
      writable: true
    });
    vi.stubEnv('VITE_DASHBOARD_PIN', '');
  });

  it('renders children if authentication is disabled', () => {
    render(
      <AuthGate>
        <div data-testid="protected-content">Protected Content</div>
      </AuthGate>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('renders unlock screen if authentication is enabled and not authenticated', () => {
    vi.stubEnv('VITE_DASHBOARD_PIN', '1234');
    render(
      <AuthGate>
        <div data-testid="protected-content">Protected Content</div>
      </AuthGate>
    );

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.getByText('SECURE ACCESS')).toBeInTheDocument();
  });
});
