/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}", // Scan all your React files for Tailwind classes
    "./public/index.html", // Include your HTML files
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
