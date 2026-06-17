import nextVitals from "eslint-config-next/core-web-vitals.js";

const nextConfig = Array.isArray(nextVitals) ? nextVitals : [nextVitals];

const eslintConfig = [
  {
    ignores: [".next/**", "out/**", "build/**", "next-env.d.ts"],
  },
];

export default eslintConfig;