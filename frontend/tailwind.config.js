/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                background: '#0a0a0a',
                surface: '#131313',
                'surface-container-low': '#1c1b1b',
                'surface-container': '#201f1f',
                'surface-container-high': '#2a2a2a',
                'surface-container-highest': '#353534',
                'surface-container-lowest': '#0e0e0e',
                'on-surface': '#e5e2e1',
                'on-surface-variant': '#c6c6c6',
                'outline-variant': '#474747',
                primary: '#ffffff',
                'primary-container': '#d4d4d4',
                'on-primary': '#1a1c1c'
            },
            borderRadius: {
                '2xl': '2rem',
            },
            boxShadow: {
                'crystal': '0 4px 24px rgba(0, 0, 0, 0.08)',
            }
        },
    },
    plugins: [],
}
