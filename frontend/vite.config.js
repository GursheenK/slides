import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

import { webserver_port } from '../../../sites/common_site_config.json'

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [frappeui(), vue()],
	server: {
		port: 8080,
		proxy: getProxyOptions(),
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	build: {
		outDir: `../${path.basename(path.resolve('..'))}/public/frontend`,
		emptyOutDir: true,
		target: 'es2015',
	},
	optimizeDeps: {
		include: ['frappe-ui > feather-icons', 'showdown', 'engine.io-client'],
	},
})

function getProxyOptions() {
	const port = webserver_port || 8000
	return {
		'^/(app|login|api|assets|files|private)': {
			target: `http://127.0.0.1:${port}`,
			ws: true,
			router: function (req) {
				const site_name = req.headers.host.split(':')[0]
				console.log(`Proxying ${req.url} to ${site_name}:${port}`)
				return `http://${site_name}:${port}`
			},
		},
	}
}
