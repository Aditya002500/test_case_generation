import { e as escape_html, h as bind_props } from './async-Byizi1M7.js';

function t(t,n){let r=n.title,i=n.x,a=n.y;r?(t.push(`<!--[-->`),t.push(`${escape_html(r)}`)):(t.push(`<!--[!-->`),t.push(`${escape_html(i)} x ${escape_html(a)}`)),t.push(`<!--]-->`),bind_props(n,{title:r,x:i,y:a});}

export { t as default };
//# sourceMappingURL=Example38-I0f_1SJx.js.map
