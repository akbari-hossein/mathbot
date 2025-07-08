# Frontend Guidelines

This document outlines the structure and conventions we follow in our frontend codebase.

## 📁 Folder Structure

```
src/
├── components/ # Reusable UI components
├── pages/ # Page-level components
├── hooks/ # Custom React hooks
├── services/ # API calls and data fetching
├── utils/ # Utility functions
├── types/ # TypeScript types/interfaces
├── assets/ # Static files (images, icons)
└── theme/ # Theme settings (if applicable)
```


## 🎨 Styling

- We use TailwindCSS for styling.
- Prefer utility classes or theme tokens over custom CSS.
- Always ensure your UI is responsive.

## 🧱 Components

- All components must be:
  - Reusable
  - Typed with TypeScript
  - Stored in their own folder if they include logic + styles
- Don't duplicate components. Search the codebase before creating new ones.

## 📦 State Management

- Use React’s built-in state and context where possible.
- For global state (if used), follow the structure defined in `store/` (e.g., Zustand, Redux).

## 🛡 TypeScript Rules

- Avoid using `any` unless absolutely necessary.
- Define all props and types in `types/` or near the component.
- Prefer enums and literal types over strings when appropriate.

## 📐 UI Consistency

- Follow design specs from Figma or the shared design system.
- Keep paddings, font sizes, and colors consistent.
- Support dark mode if the app includes it.

## ⚙️ Development Tips

- Use `npm run dev` to start the app locally.
- Use hot-reload to iterate quickly.
- Use `console.log` wisely — remove before production PRs.

---

Let’s keep the codebase clean, consistent, and maintainable. 💪
