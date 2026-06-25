import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { formatUploadedDate } from "./utils";

describe("formatUploadedDate", () => {
  it("keeps year and UTC context for older uploaded timestamps", () => {
    const formatted = formatUploadedDate("2024-02-03T04:05:06.000Z");

    assert.equal(formatted, "2024-02-03 04:05 UTC");
  });
});
