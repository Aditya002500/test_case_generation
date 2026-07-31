const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.CvFBN7S7.js",app:"_app/immutable/entry/app.BWsov1nv.js",imports:["_app/immutable/entry/start.CvFBN7S7.js","_app/immutable/chunks/gr7hp_-X.js","_app/immutable/chunks/CS1Us75e.js","_app/immutable/chunks/CFUdPpKe.js","_app/immutable/entry/app.BWsov1nv.js","_app/immutable/chunks/CS1Us75e.js","_app/immutable/chunks/CFUdPpKe.js","_app/immutable/chunks/BNrXEQcG.js","_app/immutable/chunks/VdUQV0jB.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-CAjO2MfJ.js')),
			__memo(() => import('./chunks/1-BJgcbsJR.js')),
			__memo(() => import('./chunks/2-Errc8o6K.js').then(function (n) { return n.$; }))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/[...catchall]",
				pattern: /^(?:\/([^]*))?\/?$/,
				params: [{"name":"catchall","optional":false,"rest":true,"chained":true}],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
