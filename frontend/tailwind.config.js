/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
		extend: {
			fontFamily: {
				mabry: ['mabry']
			},
			colors: {
				primary: '#748465',
				secondary: '#dbd9db',
				tertiary: '#747572',
				neutral: '#e5ebea',
				accent: '#b098a4',
			},
		}
	},
	plugins: [],
};

