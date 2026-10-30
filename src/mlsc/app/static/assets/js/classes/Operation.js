import { api } from './Api.js';
import { events } from './Events.js';

/**
 * Resolve with the final state of an Operation, from its `operation` events or, as a fallback, by polling.
 * @param {{id: string, state: string}} operation
 * @return {Promise.<{id: string, state: string, error: string|null}>}
 */
export const waitForOperation = operation => new Promise((resolve) => {
    let done = false;
    const finish = (result) => {
        if (done || result.id !== operation.id || result.state === 'pending') return;
        done = true;
        clearInterval(timer);
        resolve(result);
    };
    events.on('operation', finish);
    const timer = setInterval(() => api.get(`/operations/${operation.id}`).then(finish).catch(() => {}), 1000);
    finish(operation);
});
