import { u as ut } from './markdown-code-W_S-MH50.js';
import { m as fallback, d as attr_class, h as bind_props } from './async-Byizi1M7.js';

function n(n,r){let i=r.value,a=r.type,o=fallback(r.selected,false),s=r.sanitize_html,c=r.line_breaks,l=r.latex_delimiters;function u(e,t=60){if(!e)return ``;let n=String(e);return n.length<=t?n:n.slice(0,t)+`...`}n.push(`<div${attr_class(`prose svelte-11ua876`,void 0,{table:a===`table`,gallery:a===`gallery`,selected:o})}>`),ut(n,{message:u(i),latex_delimiters:l,sanitize_html:s,line_breaks:c,chatbot:false}),n.push(`<!----></div>`),bind_props(r,{value:i,type:a,selected:o,sanitize_html:s,line_breaks:c,latex_delimiters:l});}

export { n };
//# sourceMappingURL=Example32-DLioeiXf.js.map
