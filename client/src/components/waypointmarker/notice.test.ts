/**
 * A refused route edit carries its reason in the 409's `detail`; anything else
 * falls back to a plain sentence rather than an empty popup.
 */
import { refusal } from "./notice";

it("reads the server's reason", () => {
  const error = { status: 409, data: { detail: "The plan flies straight." } };
  expect(refusal(error, "fallback")).toBe("The plan flies straight.");
});

it("falls back when the request never reached the server", () => {
  expect(refusal({ status: "FETCH_ERROR", error: "offline" }, "fallback")).toBe(
    "fallback",
  );
});

it("falls back when there is nothing at all", () => {
  expect(refusal(null, "fallback")).toBe("fallback");
});
