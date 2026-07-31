import { K as tick } from './2-Errc8o6K.js';
import './Index17-DuKc1Qzr.js';
import { d } from './Index42-6kHRJJAT.js';
import { h as bind_props, f as attr_style, k as stringify, d as attr_class, j as ensure_array_like, e as escape_html, i as attr } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './statustracker-2iWhsYUd.js';
import './src3-Q7Y3eLw7.js';
import './html-CfyvkLET.js';
import './server-BNss68ln.js';
import './markdown-code-W_S-MH50.js';
import './prism-Xl1_rFr-.js';

function i(i,a){i.component(i=>{let o=a.app,s=a.root,c=350,u=[],d$1=[];(async()=>{o.post_data(`${s}/gradio_api/vibe-starter-queries/`,{}).then(async([e,t])=>{if(t!==200)throw Error(`Error: ${t}`);d$1=e.starter_queries;}).catch(async e=>{console.error(`Failed to fetch starter queries:`,e);});})();let m=async()=>{try{let e=await fetch(`${s}/gradio_api/vibe-code/`,{method:`GET`,headers:{"Content-Type":`application/json`}});e.ok&&(await e.json()).code;}catch(e){console.error(`Failed to fetch code:`,e);}};m();tick().then(()=>void 0);let h=true,g;function _(t){t.push(`<div class="vibe-editor svelte-1s2fnws"${attr_style(`width: ${stringify(c)}px;`)}><button class="resize-handle svelte-1s2fnws" aria-label="Resize sidebar"></button> <div class="tab-header svelte-1s2fnws"><button${attr_class(`tab-button svelte-1s2fnws`,void 0,{active:true})}>Chat</button> <button${attr_class(`tab-button svelte-1s2fnws`,void 0,{active:false})}>Code `),t.push(`<!--[!-->`),t.push(`<!--]--></button></div> <div class="tab-content svelte-1s2fnws">`);{t.push(`<!--[-->`),t.push(`<div class="message-history svelte-1s2fnws"><!--[-->`);let n=ensure_array_like(u);for(let i=0,a=n.length;i<a;i++){let a=n[i];t.push(`<div${attr_class(`message-item svelte-1s2fnws`,void 0,{"bot-message":a.isBot,"user-message":!a.isBot})}><div class="message-content svelte-1s2fnws"><span class="message-text svelte-1s2fnws">`),d(t,{value:a.text,latex_delimiters:[],theme_mode:`system`}),t.push(`<!----></span> `),!a.isBot&&a.hash&&!a.isPending?(t.push(`<!--[-->`),t.push(`<button class="undo-button svelte-1s2fnws" title="Undo this change">Undo</button>`)):t.push(`<!--[!-->`),t.push(`<!--]--></div></div>`);}if(t.push(`<!--]--> `),u.length===0?(t.push(`<!--[-->`),t.push(`<div class="no-messages svelte-1s2fnws">No messages yet</div>`)):t.push(`<!--[!-->`),t.push(`<!--]--> `),u.length===0){t.push(`<!--[-->`),t.push(`<div class="starter-queries-container svelte-1s2fnws"><div class="starter-queries svelte-1s2fnws"><!--[-->`);let e=ensure_array_like(d$1);for(let n=0,i=e.length;n<i;n++){let i=e[n];t.push(`<button class="starter-query-button svelte-1s2fnws">${escape_html(i)}</button>`);}t.push(`<!--]--></div></div>`);}else t.push(`<!--[!-->`);t.push(`<!--]--></div>`);}t.push(`<!--]--></div> <div class="input-section svelte-1s2fnws"><div class="powered-by svelte-1s2fnws">Powered by: <code>gpt-oss</code></div> <textarea placeholder="What can I add or change?" class="prompt-input svelte-1s2fnws">`);let n=escape_html(``);n&&t.push(`${n}`),t.push(`</textarea> <button class="submit-button svelte-1s2fnws"${attr(`disabled`,true,true)}>Send</button></div></div>`);}do h=true,g=i.copy(),_(g);while(!h);i.subsume(g),bind_props(a,{app:o,root:s});});}

export { i as default };
//# sourceMappingURL=Index61-BAnlVGXz.js.map
