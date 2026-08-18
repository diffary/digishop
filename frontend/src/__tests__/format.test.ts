import { expect, test } from "vitest";

import { formatPrice } from "../lib/format";

test("formatPrice форматирует центы в доллары", () => {
  expect(formatPrice(1999)).toBe("$19.99");
  expect(formatPrice(500)).toBe("$5.00");
});
