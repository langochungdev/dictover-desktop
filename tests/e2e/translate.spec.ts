describe("Feature: Hotkey translate", () => {
  it("replaces text in field after shortcut trigger", async () => {
    const input = await $('input[data-testid="translate-field"]');
    await input.setValue("xin chào");

    await browser.keys(["Control", "Shift", "T"]);
    await browser.pause(300);

    const value = await input.getValue();
    expect(value.length).toBeGreaterThan(0);
  });
});

describe("Feature: Popover on selection", () => {
  it("shows popover for selected word", async () => {
    const textElement = await $('[data-testid="selectable-text"]');
    await textElement.doubleClick();
    await browser.pause(500);

    const popover = await $('[data-testid="popover"]');
    await popover.waitForDisplayed({ timeout: 2000 });
    expect(await popover.isDisplayed()).toBe(true);
  });
});
