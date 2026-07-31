import { m as fallback, d as attr_class, e as escape_html, h as bind_props } from './async-Byizi1M7.js';

function t(t,n){t.component(t=>{let r=n.value,i=n.type,a=fallback(n.selected,false),o=n.choices,s=r.map(e=>o.find(t=>t[1]===e)?.[0]).filter(e=>e!==void 0).join(`, `);t.push(`<div${attr_class(`svelte-25nhtv`,void 0,{table:i===`table`,gallery:i===`gallery`,selected:a})}>${escape_html(s)}</div>`),bind_props(n,{value:r,type:i,selected:a,choices:o});});}

export { t as default };
//# sourceMappingURL=Example6-DlI7_QEN.js.map
