import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs/promises'

const buildTimestamp = Date.now().toString()

const emitServiceWorker = () => ({
	name: 'slides-service-worker',
	apply: 'build',
	async writeBundle() {
		const swSourcePath = path.resolve(__dirname, 'src/service-worker.js')
		const swOutputPath = path.resolve(__dirname, '../slides/www/service-worker.js')
		const source = await fs.readFile(swSourcePath, 'utf8')
		const stamped = source.replace(/__BUILD_TIMESTAMP__/g, buildTimestamp)

		await fs.mkdir(path.dirname(swOutputPath), { recursive: true })
		await fs.writeFile(swOutputPath, stamped)
	},
})

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [
		frappeui({
			frappeProxy: true,
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: '../slides/www/slides.html',
				outDir: '../slides/public/frontend',
				target: 'es2015',
			},
		}),
		vue(),
		emitServiceWorker(),
	],
	server: {
		allowedHosts: true,
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
			'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
		},
	},
	optimizeDeps: {
		include: ['feather-icons', 'tailwind.config.js', 'lowlight', 'interactjs'],
	},
})
