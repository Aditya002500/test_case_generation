import { J as m$1, K as tick } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { r } from './src3-Q7Y3eLw7.js';
import { r as r$1 } from './Index7--acCd7ji.js';
import { c as spread_props, d as attr_class, e as escape_html, f as attr_style, s as slot, h as bind_props } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './server-BNss68ln.js';
import './html-CfyvkLET.js';

function o(e,t){e.component(e=>{let{open:n=true,label:r=``,onexpand:i,oncollapse:o}=t;e.push(`<button${attr_class(`label-wrap svelte-e5lyqv`,void 0,{open:n})}><span class="svelte-e5lyqv">${escape_html(r)}</span> <span class="icon svelte-e5lyqv"${attr_style(``,{transform:n?`rotate(0)`:`rotate(90deg)`})}>▼</span></button> <div data-testid="accordion-content"${attr_style(``,{display:n?`block`:`none`})}><!--[-->`),slot(e,t,`default`,{}),e.push(`<!--]--></div>`),bind_props(t,{open:n});});}function s(s,c){s.component(s=>{let{$$slots:l,$$events:u,...d}=c;let f$1 = class f extends m$1{set_data(e){let t=this.props.open;super.set_data(e),`open`in e&&e.open!==t&&(e.open?(this.dispatch(`expand`),tick().then(()=>this.dispatch(`gradio_expand`))):this.dispatch(`collapse`)),this.shared.loading_status.status=`complete`;}};let p=new f$1(d),m=p.shared.label||``,h=[...p.shared.elem_classes||[],`gr-accordion`],g=p.shared.visible===true?true:`hidden`;r(s,{elem_id:p.shared.elem_id,elem_classes:h,visible:g,children:e=>{p.shared.loading_status?(e.push(`<!--[-->`),f(e,spread_props([{autoscroll:p.shared.autoscroll,i18n:p.i18n},p.shared.loading_status]))):e.push(`<!--[!-->`),e.push(`<!--]--> `),o(e,{label:m,open:p.props.open,onexpand:()=>{p.dispatch(`expand`),p.dispatch(`gradio_expand`);},oncollapse:()=>p.dispatch(`collapse`),children:e=>{r$1(e,{children:e=>{e.push(`<!--[-->`),slot(e,c,`default`,{}),e.push(`<!--]-->`);},$$slots:{default:true}});},$$slots:{default:true}}),e.push(`<!---->`);},$$slots:{default:true}});});}

export { s as default };
//# sourceMappingURL=Index9-uLTPvQYm.js.map
