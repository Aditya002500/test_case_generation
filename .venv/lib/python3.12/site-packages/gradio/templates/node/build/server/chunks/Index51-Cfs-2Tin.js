import { J as m$1 } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { r, z as ze, i as h } from './src3-Q7Y3eLw7.js';
export { default as BaseExample } from './Example43-TsOX3mxo.js';
import { i as attr, k as stringify, d as attr_class, e as escape_html, h as bind_props, c as spread_props, j as ensure_array_like } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './server-BNss68ln.js';
import './html-CfyvkLET.js';

var s=0;function c(e,t){e.component(e=>{let{selected:n=void 0,display_value:r,internal_value:i,disabled:a,rtl:c,on_input:l}=t,u=n===i;e.push(`<label${attr(`data-testid`,`${stringify(r)}-radio-label`)}${attr_class(`svelte-19qdtil`,void 0,{disabled:a,selected:u,rtl:c})}><input${attr(`disabled`,a,true)} type="radio"${attr(`name`,`radio-${stringify(++s)}`)}${attr(`value`,i)}${attr(`aria-checked`,u)}${attr(`checked`,n===i,true)} class="svelte-19qdtil"/> <span class="svelte-19qdtil">${escape_html(r)}</span></label>`),bind_props(t,{selected:n});});}function l(a,s){a.component(a=>{let{$$slots:l,$$events:u,...d}=s,f$1=new m$1(d),p=!f$1.shared.interactive;f$1.props.value;let m=true,h$1;function g(e){r(e,{visible:f$1.shared.visible,type:`fieldset`,elem_id:f$1.shared.elem_id,elem_classes:f$1.shared.elem_classes,container:f$1.shared.container,scale:f$1.shared.scale,min_width:f$1.shared.min_width,rtl:f$1.props.rtl,children:e=>{f(e,spread_props([{autoscroll:f$1.shared.autoscroll,i18n:f$1.i18n},f$1.shared.loading_status,{on_clear_status:()=>f$1.dispatch(`clear_status`,f$1.shared.loading_status)}])),e.push(`<!----> `),f$1.shared.show_label&&f$1.props.buttons&&f$1.props.buttons.length>0?(e.push(`<!--[-->`),ze(e,{buttons:f$1.props.buttons,on_custom_button_click:e=>{f$1.dispatch(`custom_button_click`,{id:e});}})):e.push(`<!--[!-->`),e.push(`<!--]--> `),h(e,{show_label:f$1.shared.show_label,info:f$1.props.info,children:e=>{e.push(`<!---->${escape_html(f$1.shared.label||f$1.i18n(`radio.radio`))}`);},$$slots:{default:true}}),e.push(`<!----> <div class="wrap svelte-e4x47i"><!--[-->`);let n=ensure_array_like(f$1.props.choices);for(let t=0,r=n.length;t<r;t++){let[r,i]=n[t];c(e,{display_value:f$1.live_i18n(r),internal_value:i,disabled:p,rtl:f$1.props.rtl,on_input:()=>{f$1.dispatch(`input`),f$1.dispatch(`select`,{value:i,index:t});},get selected(){return f$1.props.value},set selected(e){f$1.props.value=e,m=false;}});}e.push(`<!--]--></div>`);},$$slots:{default:true}});}do m=true,h$1=a.copy(),g(h$1);while(!m);a.subsume(h$1);});}

export { c as BaseRadio, l as default };
//# sourceMappingURL=Index51-Cfs-2Tin.js.map
