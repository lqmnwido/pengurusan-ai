import { sveltekit } from '@sveltejs/kit/vite';
import { createLogger, defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

const logger = createLogger('error');

export default defineConfig({
	logLevel: 'error',
	customLogger: {
		...logger,
		warn: () => {},
		warnOnce: () => {}
	},
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	server: {
		watch: {
			ignored: ['**/.venv/**', '**/venv/**']
		}
	},
	build: {
		sourcemap: true,
		rollupOptions: {
			onwarn: () => {}
		}
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
