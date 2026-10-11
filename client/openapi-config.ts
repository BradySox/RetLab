import { ConfigFile } from "@rtk-query/codegen-openapi";

const config: ConfigFile = {
  // The schema is keyed: see "Regenerating the API stubs" in the README.
  schemaFile: `http://[::1]:16880/openapi.json?token=${
    process.env.RETLAB_AI_TOKEN ?? ""
  }`,
  apiFile: "./src/api/baseApi.ts",
  apiImport: "baseApi",
  outputFile: "./src/api/_liberationApi.ts",
  exportName: "_liberationApi",
  hooks: true,
};

export default config;
