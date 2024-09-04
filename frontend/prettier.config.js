module.exports = {
	semi: false,
	singleQuote: true,
	useTabs: true,
	printWidth: 100,
	plugins: [require.resolve('prettier-plugin-tailwindcss')],
	tailwindConfig: './tailwind.config.js',
}
