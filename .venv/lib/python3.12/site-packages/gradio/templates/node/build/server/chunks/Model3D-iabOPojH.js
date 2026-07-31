import { g, z as ze, o as oe, v, C as Ce, a as R } from './src3-Q7Y3eLw7.js';
import { i as attr } from './async-Byizi1M7.js';

function s(s,c){s.component(s=>{let{value:l,display_mode:u=`solid`,clear_color:d=[0,0,0,0],label:f=``,show_label:p,i18n:m,zoom_speed:h=1,pan_speed:g$1=1,camera_position:_=[null,null,null],has_change_history:v$1=false}=c;g(s,{show_label:p,Icon:oe,label:f||m(`3D_model.3d_model`)}),s.push(`<!----> `),l?(s.push(`<!--[-->`),s.push(`<div class="model3D svelte-pnaihf" data-testid="model3d">`),ze(s,{children:e=>{e.push(`<!--[-->`),v(e,{Icon:Ce,label:`Undo`,onclick:()=>void 0,disabled:!v$1}),e.push(`<!--]--> <a${attr(`href`,l.url)}${attr(`target`,window.__is_colab__?`_blank`:null)}${attr(`download`,window.__is_colab__?null:l.orig_name||l.path)} data-testid="model3d-download-link">`),v(e,{Icon:R,label:m(`common.download`)}),e.push(`<!----></a>`);}}),s.push(`<!----> `),s.push(`<!--[!-->`),s.push(`<!---->`),s.push(`<!---->`),s.push(`<!--]--></div>`)):s.push(`<!--[!-->`),s.push(`<!--]-->`);});}

export { s };
//# sourceMappingURL=Model3D-iabOPojH.js.map
