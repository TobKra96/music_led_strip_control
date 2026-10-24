/** Send the browser to the login page, which returns to the current page afterwards. */
export const redirectToLogin = () => {
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
};
