import { describe, expect, test } from "bun:test";
import { render, screen } from "@testing-library/react";
import React from "react";

// Minimal sample to illustrate RTL usage with Bun's test runner.
const Greeting = ({ name }: { name: string }) => <h1>Hello, {name}!</h1>;

describe("Greeting", () => {
  test("renders a heading with the provided name", () => {
    render(<Greeting name="NetAuto" />);

    expect(
      screen.getByRole("heading", { name: /hello, netauto/i })
    ).toBeTruthy();
  });
});
