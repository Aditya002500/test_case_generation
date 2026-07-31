import { m as fallback, d as attr_class, e as escape_html, h as bind_props } from './async-Byizi1M7.js';

function t(t,n){t.component(t=>{let r=n.value,i=n.type,a=fallback(n.selected,false),o=n.choices,s;if(r===null)s=``;else {let e=o.find(e=>e[1]===r);s=e?e[0]:``;}t.push(`<div${attr_class(`svelte-g2dls0`,void 0,{table:i===`table`,gallery:i===`gallery`,selected:a})}>${escape_html(s)}</div>`),bind_props(n,{value:r,type:i,selected:a,choices:o});});}

export { t as default };
//# sourceMappingURL=Example43-TsOX3mxo.js.map
