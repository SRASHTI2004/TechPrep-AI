import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

// jsdom does not implement scrollIntoView.
Element.prototype.scrollIntoView = function scrollIntoView() {};
