import { J as m$1 } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { r, z as ze, i as h } from './src3-Q7Y3eLw7.js';
import { c as spread_props, d as attr_class, e as escape_html, i as attr } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './server-BNss68ln.js';
import './html-CfyvkLET.js';

function o(o,s){o.component(o=>{let{$$slots:c,$$events:l,...u}=s,d=new m$1(u);d.props.value??=0,d.props.value;let f$1=!d.shared.interactive;r(o,{visible:d.shared.visible,elem_id:d.shared.elem_id,elem_classes:d.shared.elem_classes,padding:d.shared.container,allow_overflow:false,scale:d.shared.scale,min_width:d.shared.min_width,children:e=>{f(e,spread_props([{autoscroll:d.shared.autoscroll,i18n:d.i18n},d.shared.loading_status,{show_validation_error:false,on_clear_status:()=>{d.dispatch(`clear_status`,d.shared.loading_status);}}])),e.push(`<!----> <label${attr_class(`block svelte-16ty2ow`,void 0,{container:d.shared.container})}>`),d.shared.show_label&&d.props.buttons&&d.props.buttons.length>0?(e.push(`<!--[-->`),ze(e,{buttons:d.props.buttons,on_custom_button_click:e=>{d.dispatch(`custom_button_click`,{id:e});}})):e.push(`<!--[!-->`),e.push(`<!--]--> `),h(e,{show_label:d.shared.show_label,info:d.props.info,children:e=>{e.push(`<!---->${escape_html(d.shared.label||`Number`)} `),d.shared.loading_status?.validation_error?(e.push(`<!--[-->`),e.push(`<div class="validation-error svelte-16ty2ow">${escape_html(d.shared.loading_status?.validation_error)}</div>`)):e.push(`<!--[!-->`),e.push(`<!--]-->`);},$$slots:{default:true}}),e.push(`<!----> <input${attr(`aria-label`,d.shared.label||`Number`)} type="number"${attr(`value`,d.props.value)}${attr(`min`,d.props.minimum)}${attr(`max`,d.props.maximum)}${attr(`step`,d.props.step)}${attr(`placeholder`,d.props.placeholder)}${attr(`disabled`,f$1,true)}${attr_class(`svelte-16ty2ow`,void 0,{"validation-error":d.shared.loading_status?.validation_error})}/></label>`);},$$slots:{default:true}});});}

export { o as default };
//# sourceMappingURL=Index48-D-R55Jy5.js.map
