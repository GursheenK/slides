import frappeUIPreset from 'frappe-ui/tailwind'

const scrollbarPlugin = require('./tailwindPlugins')

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
		extend: {},
	},
	plugins: [scrollbarPlugin],
}
