---
name: DTA AutoLive Design System
description: Impeccable Refine – Titanium Chassis 9:16 Preview Bezel & Dual-Theme UI
colors:
  primary: "#00F2FE"
  primary-hover: "#38E1FF"
  primary-gradient: "linear-gradient(135deg, #00F2FE 0%, #7928CA 100%)"
  secondary: "#7928CA"
  secondary-gradient: "linear-gradient(135deg, #7928CA 0%, #FF0080 100%)"
  accent-danger: "#FF1E56"
  accent-danger-hover: "#FF4D6D"
  accent-danger-gradient: "linear-gradient(135deg, #FF1E56 0%, #FF4D6D 100%)"
  accent-success: "#00FF87"
  accent-warning: "#FFB800"
  surface-bg: "#090D16"
  surface-sidebar: "rgba(11, 17, 30, 0.85)"
  surface-topbar: "rgba(11, 17, 30, 0.90)"
  surface-card: "rgba(15, 23, 42, 0.85)"
  surface-card-elevated: "rgba(20, 31, 54, 0.90)"
  surface-card-active: "rgba(27, 42, 74, 0.95)"
  border-soft: "rgba(0, 242, 254, 0.18)"
  border-default: "#1E2D4A"
  border-accent: "rgba(0, 242, 254, 0.40)"
  text-primary: "#F8FAFC"
  text-secondary: "#94A3B8"
  text-tertiary: "#64748B"
  text-disabled: "#475569"
typography:
  display:
    fontFamily: "'Be Vietnam Pro', sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "'Be Vietnam Pro', sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "'Be Vietnam Pro', sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "'Be Vietnam Pro', sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.4
  code:
    fontFamily: "'JetBrains Mono', monospace"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.6
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
  xl: "18px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#090D16"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-danger:
    backgroundColor: "{colors.accent-danger}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  card-panel:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "16px"
  status-chip:
    backgroundColor: "rgba(0, 255, 135, 0.14)"
    textColor: "{colors.accent-success}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
  preview-chassis:
    backgroundColor: "#F8FAFC"
    border: "2px solid rgba(203, 213, 225, 0.6)"
    borderRadius: "16px"
    boxShadow: "0 10px 40px -4px rgba(15, 23, 42, 0.12)"
    innerVideoRadius: "12px"
---

# Design System – DTA AutoLive Console (Titanium Chassis Bezel Edition)

## Overview

DTA AutoLive áp dụng ngôn ngữ thiết kế **Titanium Chassis Bezel & Obsidian Glassmorphism** đạt chuẩn cao cấp:
- **Khung Bezel Màn Hình 9:16 (Titanium Bezel Chassis):**
  * Viền Bezel mỏng mượt: `border: 2px solid rgba(203, 213, 225, 0.6)` (Titanium xám nhạt).
  * Bo góc sâu: `border-radius: 16px`.
  * Nền container: Silver Mist (`#F8FAFC`) ôm trọn khối video đen.
  * Chiều sâu & chuyển tiếp: Drop shadow mềm `box-shadow: 0 10px 40px -4px rgba(15, 23, 42, 0.12)`.
  * Khối video đen bên trong: `border-radius: 12px`, nằm lọt gọn gàng như thiết bị màn hình studio vật lý.
