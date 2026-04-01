---
name: ATS Form Fill Techniques (Greenhouse, Ashby, and React forms)
description: Greenhouse dropdowns need trusted CDP clicks (not selectOption). Ashby needs trusted CDP events for all fields. Text inputs work with JS injection on Greenhouse.
type: feedback
---

## Greenhouse React-Select Dropdowns — MUST use trusted CDP events

`selectInstance.selectOption()` and `selectProps.onChange()` both update the visual display but **DO NOT pass Greenhouse's form validation**. The form shows "This field is required" on submit even though the dropdown visually shows the selected value.

**Why:** Greenhouse wraps react-select with its own form state management. The onChange callback chain only propagates correctly when triggered by react-select's own event handling (real mousedown on options). Calling selectOption() programmatically from outside React's event loop doesn't trigger the full state propagation through Greenhouse's component tree.

**What works for Greenhouse dropdowns:**
1. **Click dropdown to open → Click option** (2 trusted CDP clicks per dropdown)
2. **Click dropdown to open → Type answer text → Press Enter** (click + type + Enter, fastest)

**What does NOT work:**
- `selectInstance.selectOption(match)` — visual only, validation fails
- `selectProps.onChange(option)` — visual only, validation fails
- `Rs.onChange(option)` — calling Greenhouse's wrapper directly also fails
- Programmatic `dispatchEvent(new MouseEvent('mousedown'))` — untrusted, menu won't open

## Greenhouse Text Fields — JS injection works

Simplify-style dual dispatch (native setter + `__reactProps` handler calls) works for text inputs, textareas, and other non-react-select fields:
```js
const reactKey = Object.keys(el).find(k => /^(__reactProps|__reactEventHandlers)/.test(k));
// fire focus, click, keydown, keypress
// SET VALUE via Simplify pattern:
const ownSetter = Object.getOwnPropertyDescriptor(el, 'value')?.set;
const protoSetter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value')?.set;
if (ownSetter && protoSetter && ownSetter !== protoSetter) protoSetter.call(el, v);
else if (ownSetter) ownSetter.call(el, v);
el.value = v;
el.setAttribute('value', v);
// fire textInput, input, keyup, change, blur
```

## Ashby — ALL fields need trusted CDP events

Ashby checks `event.isTrusted`. Events from `evaluate_script` are always untrusted. Must use MCP `fill` for text fields and MCP `click` for radios/checkboxes/buttons.

## Optimal Fill Pipeline

| ATS | Text fields | Dropdowns | Total calls | Time |
|-----|------------|-----------|-------------|------|
| Greenhouse | JS injection (1 call) | CDP click+type+Enter (3 per dropdown) | ~20 | <1 min |
| Ashby | MCP fill per field (~10) | MCP click per option (~10) | ~20 | ~2 min |
| Lever | JS injection (1 call) | JS injection (1 call) | ~3 | <30s |
