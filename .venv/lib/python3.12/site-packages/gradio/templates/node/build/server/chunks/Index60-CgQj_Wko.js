import { J as m$1 } from './2-Errc8o6K.js';
import { r as r$1 } from './Index5-Cg1Km9LQ.js';
import { i as attr, k as stringify, e as escape_html } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './Image-Cuxe3CuX.js';

function r(e,r){e.component(e=>{let{elem_id:i=``,elem_classes:a=[],visible:o=true,label:s,value:c,file_count:l,file_types:u=[],root:d,size:f=`lg`,icon:p=null,scale:m=null,min_width:h=void 0,variant:g=`secondary`,disabled:_=false,max_file_size:v=null,upload:y,onclick:b,onchange:x,onupload:S,onerror:C,children:w}=r,T=u==null?null:u.map(e=>e.startsWith(`.`)?e:e+`/*`).join(`, `);function E(){b?.(),(void 0).click();}e.push(`<input class="hide svelte-94gmgt"${attr(`accept`,T)} type="file"${attr(`multiple`,l===`multiple`||void 0,true)}${attr(`webkitdirectory`,l===`directory`||void 0,true)}${attr(`mozdirectory`,l===`directory`||void 0)}${attr(`data-testid`,`${stringify(s)}-upload-button`)}/> `),r$1(e,{size:f,variant:g,elem_id:i,elem_classes:a,visible:o,onclick:E,scale:m,min_width:h,disabled:_,children:e=>{p?(e.push(`<!--[-->`),e.push(`<img class="button-icon svelte-94gmgt"${attr(`src`,p.url)}${attr(`alt`,`${c} icon`)}/>`)):e.push(`<!--[!-->`),e.push(`<!--]--> `),w?(e.push(`<!--[-->`),w(e),e.push(`<!---->`)):e.push(`<!--[!-->`),e.push(`<!--]-->`);}}),e.push(`<!---->`);});}function i(t,i){t.component(t=>{let{$$slots:a,$$events:o,...s}=i,c=new m$1(s),l=c.props.value;async function u(e,t){c.props.value=e,c.dispatch(t);}let d=!c.shared.interactive;r(t,{elem_id:c.shared.elem_id,elem_classes:c.shared.elem_classes,visible:c.shared.visible,file_count:c.props.file_count,file_types:c.props.file_types,size:c.props.size,scale:c.shared.scale,icon:c.props.icon,min_width:c.shared.min_width,root:c.shared.root,value:l,disabled:d,variant:c.props.variant,label:c.shared.label,max_file_size:c.shared.max_file_size,onclick:()=>c.dispatch(`click`),onchange:e=>u(e,`change`),onupload:e=>u(e,`upload`),onerror:e=>{c.dispatch(`error`,e);},upload:(...e)=>c.shared.client.upload(...e),children:e=>{e.push(`<!---->${escape_html(c.shared.label??``)}`);}});});}

export { r as BaseUploadButton, i as default };
//# sourceMappingURL=Index60-CgQj_Wko.js.map
