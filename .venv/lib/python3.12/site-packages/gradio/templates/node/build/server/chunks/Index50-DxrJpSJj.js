import { J as m$1 } from './2-Errc8o6K.js';
import { f } from './statustracker-2iWhsYUd.js';
import { r, g, z as ze, B as Be, a2 as me } from './src3-Q7Y3eLw7.js';
import { n } from './Plot2-CpntDyAj.js';
import { c as spread_props } from './async-Byizi1M7.js';
import './environment-C03H9Pbz.js';
import './chunk-TIJk1bZ5.js';
import 'node:module';
import './index-FcHinwaE.js';
import './server-BNss68ln.js';
import './html-CfyvkLET.js';

function l(l,u){l.component(l=>{let{$$slots:d,$$events:f$1,...p}=u,m=new m$1(p),h=false,g$1=true,_;function v(e){r(e,{padding:false,elem_id:m.shared.elem_id,elem_classes:m.shared.elem_classes,visible:m.shared.visible,container:m.shared.container,scale:m.shared.scale,min_width:m.shared.min_width,allow_overflow:false,get fullscreen(){return h},set fullscreen(e){h=e,g$1=false;},children:e=>{g(e,{show_label:m.shared.show_label,label:m.shared.label||m.i18n(`plot.plot`),Icon:me}),e.push(`<!----> `),m.props.buttons&&m.props.buttons.length>0||m.props.show_fullscreen_button?(e.push(`<!--[-->`),ze(e,{buttons:m.props.buttons??[],on_custom_button_click:e=>{m.dispatch(`custom_button_click`,{id:e});},children:e=>{m.props.show_fullscreen_button?(e.push(`<!--[-->`),Be(e,{fullscreen:h,onclick:e=>{h=e;}})):e.push(`<!--[!-->`),e.push(`<!--]-->`);}})):e.push(`<!--[!-->`),e.push(`<!--]--> `),f(e,spread_props([{autoscroll:m.shared.autoscroll,i18n:m.i18n},m.shared.loading_status,{on_clear_status:()=>m.dispatch(`clear_status`,m.shared.loading_status)}])),e.push(`<!----> `),n(e,{value:m.props.value,theme_mode:m.shared.theme_mode,show_label:m.shared.show_label,caption:m.props.caption,bokeh_version:m.props.bokeh_version,show_actions_button:m.props.show_actions_button,_selectable:m.props._selectable,x_lim:m.props.x_lim,show_fullscreen_button:m.props.show_fullscreen_button,on_change:()=>m.dispatch(`change`),onselect:e=>m.dispatch(`select`,e)}),e.push(`<!---->`);},$$slots:{default:true}});}do g$1=true,_=l.copy(),v(_);while(!g$1);l.subsume(_);});}

export { n as BasePlot, l as default };
//# sourceMappingURL=Index50-DxrJpSJj.js.map
