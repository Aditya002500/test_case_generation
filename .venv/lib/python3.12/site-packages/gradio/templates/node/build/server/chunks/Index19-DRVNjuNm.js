import { J as m$1 } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { i as h, r as r$1 } from './src3-Q7Y3eLw7.js';
export { default as BaseExample } from './Example10-94VJjAz8.js';
import { r } from './tinycolor-D-8uQpkZ.js';
import { i as attr, f as attr_style, h as bind_props, c as spread_props, e as escape_html } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './server-BNss68ln.js';
import './html-CfyvkLET.js';

function c(e,t){return r(e).toHexString()}function l(e,t){e.component(e=>{let{value:n=void 0,label:i,info:a,disabled:l,show_label:u,on_input:d=()=>{},on_release:f=()=>{},on_submit:p=()=>{},on_blur:m=()=>{},on_focus:h$1=()=>{}}=t;c(n),h(e,{show_label:u,info:a,children:e=>{e.push(`<!---->${escape_html(i)}`);},$$slots:{default:true}}),e.push(`<!----> <div><button class="dialog-button svelte-nbn1m9"${attr(`aria-label`,i)}${attr(`disabled`,l,true)}${attr_style(``,{background:n})}></button> `),e.push(`<!--[!-->`),e.push(`<!--]--></div>`),bind_props(t,{value:n});});}function u(r,i){r.component(r=>{let{$$slots:a,$$events:o,...c}=i,u=new m$1(c,{value:`#000000`});u.props.value;let d=u.shared.label||u.i18n(`color_picker.color_picker`),f$1=true,p;function m(e){r$1(e,{visible:u.shared.visible,elem_id:u.shared.elem_id,elem_classes:u.shared.elem_classes,container:u.shared.container,scale:u.shared.scale,min_width:u.shared.min_width,children:e=>{f(e,spread_props([{autoscroll:u.shared.autoscroll,i18n:u.i18n},u.shared.loading_status,{on_clear_status:()=>u.dispatch(`clear_status`,u.shared.loading_status)}])),e.push(`<!----> `),l(e,{label:d,info:u.props.info,show_label:u.shared.show_label,disabled:!u.shared.interactive,on_input:()=>u.dispatch(`input`),on_release:()=>u.dispatch(`release`,u.props.value),on_submit:()=>u.dispatch(`submit`),on_blur:()=>u.dispatch(`blur`),on_focus:()=>u.dispatch(`focus`),get value(){return u.props.value},set value(e){u.props.value=e,f$1=false;}}),e.push(`<!---->`);},$$slots:{default:true}});}do f$1=true,p=r.copy(),m(p);while(!f$1);r.subsume(p);});}

export { l as BaseColorPicker, u as default };
//# sourceMappingURL=Index19-DRVNjuNm.js.map
