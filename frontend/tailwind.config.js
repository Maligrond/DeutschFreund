/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                'tg-bg': 'var(--tg-theme-bg-color)',
                'tg-text': 'var(--tg-theme-text-color)',
                'tg-hint': 'var(--tg-theme-hint-color)',
                'tg-link': 'var(--tg-theme-link-color)',
                'tg-button': 'var(--tg-theme-button-color)',
                'tg-button-text': 'var(--tg-theme-button-text-color)',
                'tg-secondary': 'var(--tg-theme-secondary-bg-color)',
                'tg-separator': 'var(--tg-theme-section-separator-color)',
            },
            fontSize: {
                'ios-body': ['17px', '22px'],
                'ios-subhead': ['15px', '20px'],
                'ios-footnote': ['13px', '18px'],
                'ios-caption': ['12px', '16px'],
            }
        },
    },
    plugins: [],
}
