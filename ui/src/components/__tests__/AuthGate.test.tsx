import { render, screen } from '@testing-library/react';
import { AuthGate } from '../AuthGate';
import '@testing-library/jest-dom';
import { beforeEach, describe, it, expect } from 'vitest';

describe('AuthGate', () => {
  beforeEach(() => {
    // Reset any mock/spy if necessary
    sessionStorage.clear();
  });

  it('renders children if authentication is disabled', () => {
    render(
      <AuthGate isEnabled={false} correctPin="0000">
        <div data-testid="protected-content">Protected Content</div>
      </AuthGate>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('renders unlock screen if authentication is enabled and not authenticated', () => {
    render(
      <AuthGate isEnabled={true} correctPin="1234">
        <div data-testid="protected-content">Protected Content</div>
      </AuthGate>
    );

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.getByText('System Locked')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter Access PIN')).toBeInTheDocument();
  });
});
