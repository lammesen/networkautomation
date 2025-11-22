import { Window } from "happy-dom";

// Create a minimal DOM for React Testing Library when running under bun:test.
const windowInstance = new Window();

globalThis.window = windowInstance as unknown as Window & typeof globalThis;
globalThis.document = windowInstance.document;
globalThis.navigator = windowInstance.navigator;
globalThis.HTMLElement = windowInstance.HTMLElement as unknown as typeof HTMLElement;
globalThis.CustomEvent = windowInstance.CustomEvent as unknown as typeof CustomEvent;
