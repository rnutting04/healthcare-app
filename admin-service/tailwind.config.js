/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './admin_app/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'healthcare-blue': '#0066CC',
        'healthcare-light': '#E8F4FD',
      }
    },
  },
  plugins: [],
}