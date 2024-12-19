import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [frappeui(), vue()],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	build: {
		outDir: `../slides/public/frontend`,
		emptyOutDir: true,
		rollupOptions: {
			output: {
				manualChunks: {
					'frappe-ui': ['frappe-ui'],
				},
			},
		},
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
		sourcemap: true,
	},
	optimizeDeps: {
		include: ['feather-icons', 'showdown', 'engine.io-client'],
	},
})
