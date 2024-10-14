/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
		extend: {
			fontFamily: {
				mabry: ['mabry']
			},
			colors: {
				primary: {
					DEFAULT: '#748465',
				},
				secondary: {
					DEFAULT: '#dbd9db', 
				},
        tertiary: {
          DEFAULT: '#747572',
        },
				neutral: {
					DEFAULT: '#e5ebea', 
				},
				accent: {
					DEFAULT: '#b098a4', 
				},
			}
		}
	},
  plugins: [],
}
