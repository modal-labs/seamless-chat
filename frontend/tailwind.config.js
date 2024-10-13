/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
		extend: {
			fontFamily: {
				mabry: ['mabry']
			},
			colors: {
				mint: '#f1fffa',
				tea: '#ccfccb',
				celadon: '#96e6b3',
				fern: '#568259',
				space: '#464e47'
			}
		}
	},
  plugins: [],
}

