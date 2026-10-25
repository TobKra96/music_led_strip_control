import { afterEach, expect, it, vi } from 'vitest';
import { redirectToLogin } from '../../src/mlsc/app/static/assets/js/classes/Login.js';

afterEach(() => vi.unstubAllGlobals());

it('sends the browser to the login page and returns to the current page afterwards', () => {
    const location = { pathname: '/settings/general', href: '' };
    vi.stubGlobal('window', { location });

    redirectToLogin();

    expect(location.href).toBe('/login?next=%2Fsettings%2Fgeneral');
});
