import { Window } from "happy-dom";

// Create a minimal DOM for React Testing Library when running under bun:test.
const windowInstance = new Window();

// Use type assertions to satisfy TypeScript while providing DOM globals
// These @ts-expect-error comments are necessary because happy-dom provides
// partial implementations that don't fully match browser types
// @ts-expect-error - happy-dom provides a partial Window implementation
globalThis.window = windowInstance;
// @ts-expect-error - happy-dom provides a partial Document implementation
globalThis.document = windowInstance.document;
// @ts-expect-error - happy-dom provides a partial Navigator implementation
globalThis.navigator = windowInstance.navigator;
// @ts-expect-error - happy-dom provides a partial HTMLElement implementation
globalThis.HTMLElement = windowInstance.HTMLElement;
// @ts-expect-error - happy-dom provides a partial CustomEvent implementation
globalThis.CustomEvent = windowInstance.CustomEvent;
// @ts-expect-error - happy-dom provides a partial Element implementation
globalThis.Element = windowInstance.Element;
// @ts-expect-error - happy-dom provides a partial MutationObserver implementation
globalThis.MutationObserver = windowInstance.MutationObserver;
