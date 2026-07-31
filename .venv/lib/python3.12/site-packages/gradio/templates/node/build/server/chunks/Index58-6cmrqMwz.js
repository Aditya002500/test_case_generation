import { J as m$1 } from './2-Errc8o6K.js';
import { r } from './Index7--acCd7ji.js';
import { a as a$1 } from './Index56-BWB9waG6.js';
import { g as getContext, i as attr, d as attr_class, k as stringify, f as attr_style, w as store_get, s as slot, x as unsubscribe_stores } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './statustracker-2iWhsYUd.js';
import './src3-Q7Y3eLw7.js';
import './html-CfyvkLET.js';
import './server-BNss68ln.js';

function a(e,a){e.component(e=>{var o;let{elem_id:s=``,elem_classes:c=[],label:l,id:u,visible:d,interactive:f,order:p,scale:m,component_id:h,onselect:g}=a,{register_tab:_,unregister_tab:v,selected_tab:y,selected_tab_index:b}=getContext(a$1),x=u??h;JSON.stringify({label:l,id:x,elem_id:s,visible:d,interactive:f,scale:m,component_id:h});let S=d!==false&&d!==`hidden`;e.push(`<div${attr(`id`,s)}${attr_class(`tabitem ${stringify(c.join(` `))}`,`svelte-dmtrd3`,{"grow-children":m>=1})} role="tabpanel"${attr_style(``,{display:store_get(o??={},`$selected_tab`,y)===x&&S?`flex`:`none`,"flex-grow":m})}>`),r(e,{scale:m>=1?m:null,children:e=>{e.push(`<!--[-->`),slot(e,a,`default`,{}),e.push(`<!--]-->`);},$$slots:{default:true}}),e.push(`<!----></div>`),o&&unsubscribe_stores(o);});}function o(t,n){t.component(t=>{let{$$slots:r,$$events:o,...s}=n,c=new m$1(s);a(t,{elem_id:c.shared.elem_id,elem_classes:c.shared.elem_classes,label:c.shared.label,visible:c.shared.visible,interactive:c.shared.interactive,id:c.props.id,order:c.props.order,scale:c.shared.scale,component_id:c.props.component_id,onselect:e=>c.dispatch(`select`,e),children:e=>{e.push(`<!--[-->`),slot(e,n,`default`,{}),e.push(`<!--]-->`);},$$slots:{default:true}});});}

export { a as BaseTabItem, o as default };
//# sourceMappingURL=Index58-6cmrqMwz.js.map
