import { e, n } from './environment-C03H9Pbz.js';
import { p, w } from './client-DJRidqZz.js';
import { e as escape_html, g as getContext } from './async-Byizi1M7.js';
import './internal-B7CRNCtX.js';
import './index-DBqjc0Yf.js';
import './index-FcHinwaE.js';

var s={get error(){return p.error},get status(){return p.status}};w.updated.check;function c(){return getContext(`__request__`)}function l(e){try{return c()}catch{throw Error(`Can only read '${e}' on the server during rendering (not in e.g. \`load\` functions), as it is bound to the current request via component context. This prevents state from leaking between users. For more information, see https://svelte.dev/docs/kit/state-management#avoid-shared-state-on-the-server`)}}var u=e?s:{get error(){return (n?l(`page.error`):c()).page.error},get status(){return (n?l(`page.status`):c()).page.status}};function d(e,t){e.component(e=>{e.push(`<h1>${escape_html(u.status)}</h1> <p>${escape_html(u.error?.message)}</p>`);});}

export { d as default };
//# sourceMappingURL=error.svelte-giX3jcfY.js.map
