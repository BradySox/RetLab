import { API_KEY_HEADERS, HTTP_URL } from "./backend";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export const baseApi = createApi({
  baseQuery: fetchBaseQuery({
    baseUrl: HTTP_URL,
    prepareHeaders: (headers) => {
      Object.entries(API_KEY_HEADERS).forEach(([name, value]) =>
        headers.set(name, value),
      );
      return headers;
    },
  }),
  endpoints: () => ({}),
});
