import { J as m$1, U as h, N as K } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { r, z as ze, g, N } from './src3-Q7Y3eLw7.js';
export { default as BaseExample } from './Example28-73IoZ4SE.js';
import { r as r$1 } from './HTML-Dwvv8ST0.js';
import { c as spread_props, d as attr_class, f as attr_style } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './server-BNss68ln.js';
import './html-CfyvkLET.js';
import 'fs';

function d(c,d){c.component(c=>{let{$$slots:f$1,$$events:p,...m}=d,h$1=m.children,g$1=new m$1(m),_={value:g$1.props.value??``,label:g$1.shared.label,visible:g$1.shared.visible,...g$1.props.props};g$1.props.value;async function v(e){try{let t=await K([e]),r=await g$1.shared.client.upload(t,g$1.shared.root,void 0,g$1.shared.max_file_size??void 0);if(r&&r[0])return {path:r[0].path,url:r[0].url};throw Error(`Upload failed`)}catch(e){throw g$1.dispatch(`error`,e instanceof Error?e.message:String(e)),e}}r(c,{visible:g$1.shared.visible,elem_id:g$1.shared.elem_id,elem_classes:g$1.shared.elem_classes,container:g$1.shared.container,padding:g$1.shared.padding!==false,overflow_behavior:`visible`,children:t=>{g$1.shared.show_label&&g$1.props.buttons&&g$1.props.buttons.length>0?(t.push(`<!--[-->`),ze(t,{buttons:g$1.props.buttons,on_custom_button_click:e=>{g$1.dispatch(`custom_button_click`,{id:e});}})):t.push(`<!--[!-->`),t.push(`<!--]--> `),g$1.shared.show_label?(t.push(`<!--[-->`),g(t,{Icon:N,show_label:g$1.shared.show_label,label:g$1.shared.label,float:true})):t.push(`<!--[!-->`),t.push(`<!--]--> `),f(t,spread_props([{autoscroll:g$1.shared.autoscroll,i18n:g$1.i18n},g$1.shared.loading_status,{variant:`center`,on_clear_status:()=>g$1.dispatch(`clear_status`,g$1.shared.loading_status)}])),t.push(`<!----> <div${attr_class(`html-container svelte-1jts93g`,void 0,{pending:g$1.shared.loading_status?.status===`pending`&&g$1.shared.loading_status?.show_progress!==`hidden`,"label-padding":g$1.shared.show_label??void 0})}${attr_style(``,{"min-height":g$1.props.min_height&&g$1.shared.loading_status?.status!==`pending`?h(g$1.props.min_height):void 0,"max-height":g$1.props.max_height?h(g$1.props.max_height):void 0,"overflow-y":g$1.props.max_height?`auto`:void 0})}><!---->`),r$1(t,{props:_,html_template:g$1.props.html_template,css_template:g$1.props.css_template,js_on_load:g$1.props.js_on_load,elem_classes:g$1.shared.elem_classes,visible:g$1.shared.visible===`hidden`?false:g$1.shared.visible,autoscroll:g$1.shared.autoscroll,apply_default_css:g$1.props.apply_default_css,head:g$1.props.head,component_class_name:g$1.props.component_class_name,upload:v,server:g$1.shared.server,children:e=>{h$1?.(e);}}),t.push(`<!----></div>`);},$$slots:{default:true}});});}

export { r$1 as BaseHTML, d as default };
//# sourceMappingURL=Index37-BNCf2kl4.js.map
