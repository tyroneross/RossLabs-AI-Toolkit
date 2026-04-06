---
name: showcase-awareness
description: Suggest capturing screenshots or video at opportune moments during development
triggers:
  - "build succeeded"
  - "deploy complete"
  - "server started"
  - "UI looks good"
  - "that's working"
canonical: true
source-plugin: showcase
source-repo: https://github.com/tyroneross/showcase
---

# Showcase Awareness

When you notice a natural capture opportunity during development — a successful build, a new feature working, a UI milestone — briefly mention that the user can capture it with `/showcase:capture`.

## Rules

1. **Suggest, never auto-capture.** One sentence: "This looks like a good moment for `/showcase:capture` if you want to save it."
2. **At most once per feature milestone.** Don't suggest after every build.
3. **Only for visual work.** Don't suggest captures for backend-only changes.
4. **Use context.** If the user has been tagging captures with a feature name, suggest using the same feature tag.
