const API_V2 = '/api/v2';

/** An RFC 9457 problem document returned by the API, or a failed request without one. */
export class ApiError extends Error {
    /**
     * @param {number} status HTTP status, `0` when the server could not be reached.
     * @param {{code?: string, title?: string, detail?: string, errors?: Array.<{field: string, detail: string}>}} problem
     */
    constructor(status, problem = {}) {
        super(problem.detail || problem.title || 'Unable to reach the server.');
        this.status = status;
        this.code = problem.code;
        this.errors = problem.errors || [];
    }

    /**
     * Message for a toast, which renders HTML: the detail of the problem and the problem of every invalid field.
     * @return {string}
     */
    get summary() {
        const escape = text => $('<div></div>').text(text).html();
        const fields = this.errors.map(e => `${e.field}: ${e.detail}`);
        return [this.message, ...fields].map(escape).join('<br>');
    }
}

/**
 * Call the v2 API with a JSON body. Resolves with the parsed JSON, or `null` for `204`.
 * An expired session sends the browser to the login page.
 * @param {string} method
 * @param {string} path Path below `/api/v2`.
 * @param {object} [body]
 * @return {Promise.<any>}
 */
const request = async (method, path, body) => {
    const options = { method, headers: { Accept: 'application/json' }, credentials: 'same-origin' };
    if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    } else if (method !== 'GET') {
        options.headers['Content-Type'] = 'application/json';
    }

    let response;
    try {
        response = await fetch(`${API_V2}${path}`, options);
    } catch {
        throw new ApiError(0);
    }

    if (response.status === 204) return null;

    const isJson = /json/.test(response.headers.get('Content-Type') || '');
    const payload = isJson ? await response.json() : {};
    if (response.ok) return payload;

    if (response.status === 401) {
        window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new ApiError(response.status, payload);
};

export const api = {
    get: (path) => request('GET', path),
    post: (path, body) => request('POST', path, body),
    put: (path, body) => request('PUT', path, body),
    patch: (path, body) => request('PATCH', path, body),
    delete: (path) => request('DELETE', path),
};
