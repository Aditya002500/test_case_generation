import { t } from './Image-Cuxe3CuX.js';
import './2-Errc8o6K.js';
import { d as attr_class, e as escape_html, j as ensure_array_like, i as attr } from './async-Byizi1M7.js';
import { z as zu } from './Video-9WWx6ini.js';

function r(r,i){r.component(r=>{let{value:a={text:``,files:[]},type:o,selected:s=false}=i;r.push(`<div${attr_class(`container svelte-xz0m7l`,void 0,{table:o===`table`,gallery:o===`gallery`,selected:s,border:a})}><p>${escape_html(a.text?a.text:``)}</p> <!--[-->`);let c=ensure_array_like(a.files);for(let i=0,a=c.length;i<a;i++){let a=c[i];a.mime_type&&a.mime_type.includes(`image`)?(r.push(`<!--[-->`),t(r,{src:a.url,alt:``})):(r.push(`<!--[!-->`),a.mime_type&&a.mime_type.includes(`video`)?(r.push(`<!--[-->`),zu(r,{src:a.url,alt:``,loop:true,is_stream:false})):(r.push(`<!--[!-->`),a.mime_type&&a.mime_type.includes(`audio`)?(r.push(`<!--[-->`),r.push(`<audio${attr(`src`,a.url)} controls></audio>`)):(r.push(`<!--[!-->`),r.push(`${escape_html(a.orig_name)}`)),r.push(`<!--]-->`)),r.push(`<!--]-->`)),r.push(`<!--]-->`);}r.push(`<!--]--></div>`);});}

export { r };
//# sourceMappingURL=Example36-A68WIlS8.js.map
