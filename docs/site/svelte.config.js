import adapter from "@sveltejs/adapter-static";

const isDev = process.argv.includes("dev");

export default {
  kit: {
    adapter: adapter({ pages: "build", assets: "build", fallback: "404.html" }),
    paths: {
      base: isDev ? "" : (process.env.BASE_PATH ?? ""),
    },
  },
};
