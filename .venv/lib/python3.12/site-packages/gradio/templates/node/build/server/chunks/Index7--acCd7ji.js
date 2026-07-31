import { J as m$1 } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { i as attr, d as attr_class, k as stringify, f as attr_style, c as spread_props, s as slot } from './async-Byizi1M7.js';

function r(e,r){e.component(e=>{let{$$slots:i,$$events:a,...o}=r,s=o.scale??null,c=o.min_width??0,l=o.elem_id??``,u=o.elem_classes??[],d=o.visible??true,f$1=o.variant??`default`,p=o.loading_status;o.show_progress,e.push(`<div${attr(`id`,l)}${attr_class(`column ${stringify(u.join(` `))}`,`svelte-siq5d6`,{compact:f$1===`compact`,panel:f$1===`panel`,hide:!d})}${attr_style(``,{"flex-grow":s,"min-width":`calc(min(${stringify(c)}px, 100%))`})}>`),p&&p.show_progress?(e.push(`<!--[-->`),f(e,spread_props([{autoscroll:o.autoscroll??false,i18n:o.i18n??(e=>e)},p,{queue_size:p.queue_size??null,status:p?p.status==`pending`?`generating`:p.status:null}]))):e.push(`<!--[!-->`),e.push(`<!--]--> <!--[-->`),slot(e,r,`default`,{}),e.push(`<!--]--></div>`);});}function i(t,i){t.component(t=>{let{$$slots:a,$$events:o,...s}=i,c=new m$1(s);r(t,spread_props([c.shared,c.props,{children:e=>{e.push(`<!--[-->`),slot(e,i,`default`,{}),e.push(`<!--]-->`);},$$slots:{default:true}}]));});}

export { i, r };
//# sourceMappingURL=Index7--acCd7ji.js.map
