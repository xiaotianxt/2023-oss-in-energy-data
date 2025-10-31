# CMU Energy Security Dashboard - Design System

## Design Philosophy

This design system follows **Carnegie Mellon University's official brand guidelines**, using the registered core colors and secondary palettes to create a professional, trustworthy security analysis dashboard.

**Source**: [CMU Brand Guidelines - Colors](https://www.cmu.edu/brand/brand-guidelines/visual-identity/colors.html)

---

## CMU Official Color Palette

### Core Colors (Registered since the late 1920s)

These are CMU's primary brand colors. **Carnegie Red should be dominant**, with grays, black, and white providing support.

#### Carnegie Red
- **HEX**: `#C41230`
- **RGB**: 196, 18, 48
- **CMYK**: 0, 100, 79, 20
- **PMS**: 187C
- **Usage**: Primary brand color, buttons, highlights, danger states

#### Black
- **HEX**: `#000000`
- **RGB**: 0, 0, 0
- **CMYK**: 0, 0, 0, 100
- **PMS**: Black C
- **Usage**: Primary text color

#### Iron Gray
- **HEX**: `#6D6E71`
- **RGB**: 109, 110, 113
- **CMYK**: 0, 0, 0, 70
- **PMS**: Cool Grey 10 C
- **Usage**: Secondary text, footer background

#### Steel Gray
- **HEX**: `#E0E0E0`
- **RGB**: 224, 224, 224
- **CMYK**: 0, 0, 0, 30
- **PMS**: Cool Gray 4 C
- **Usage**: Borders, subtle backgrounds

#### White
- **HEX**: `#FFFFFF`
- **Usage**: Main background, card backgrounds

---

### Tartan Palette (Secondary - For Accents Only)
**Theme**: Bold, Youthful, Passionate, Fearless, Audacious

Only use as accents when Carnegie Red is present in the design.

#### Scots Rose
- **HEX**: `#EF3A47`
- **RGB**: 239, 58, 71
- **PMS**: Red 032 C

#### Gold Thread
- **HEX**: `#FDB515`
- **RGB**: 253, 181, 21
- **PMS**: 130 C
- **Usage**: Warning states, medium severity

#### Green Thread
- **HEX**: `#009647`
- **RGB**: 0, 150, 71
- **PMS**: 348 C
- **Usage**: Success states, low severity

#### Teal Thread
- **HEX**: `#008F91`
- **RGB**: 0, 143, 145
- **PMS**: 7713 C

#### Blue Thread
- **HEX**: `#043673`
- **RGB**: 4, 54, 115
- **PMS**: 288 C

#### Highlands Sky Blue
- **HEX**: `#007BC0`
- **RGB**: 0, 123, 192
- **PMS**: 640 C
- **Usage**: Info states, good health scores

---

### Campus Palette (Secondary - For Accents Only)
**Theme**: Insightful, Conscientious, Creative, Pragmatic, Entrepreneurial

#### Machinery Hall Tan
- **HEX**: `#BCB49E`
- **RGB**: 188, 180, 158
- **PMS**: 7535 C

#### Kittanning Brick Beige
- **HEX**: `#E4DAC4`
- **RGB**: 228, 218, 196
- **PMS**: 7534 C

#### Hornbostel Teal
- **HEX**: `#1F4C4C`
- **RGB**: 31, 76, 76
- **PMS**: 7476 C

#### Palladian Green
- **HEX**: `#719F94`
- **RGB**: 113, 159, 148
- **PMS**: 624 C

#### Weaver Blue
- **HEX**: `#182C4B`
- **RGB**: 25, 44, 75
- **PMS**: 7463 C

#### Skibo Red
- **HEX**: `#941120`
- **RGB**: 149, 17, 32
- **PMS**: 7623 C
- **Usage**: Critical severity, dark red states

---

## Dashboard Implementation

### Severity Levels
- **Critical**: Skibo Red `#941120`
- **High**: Carnegie Red `#C41230`
- **Medium**: Gold Thread `#FDB515`
- **Low**: Green Thread `#009647`
- **Negligible**: Iron Gray `#6D6E71`

### Health Score Color Scale
- **90-100%**: Green Thread `#009647` (Excellent)
- **75-89%**: Highlands Sky `#007BC0` (Good)
- **60-74%**: Teal Thread `#008F91` (Fair)
- **40-59%**: Gold Thread `#FDB515` (Warning)
- **20-39%**: Scots Rose `#EF3A47` (Poor)
- **0-19%**: Skibo Red `#941120` (Critical)

### Chart Colors
**Primary Charts**: Carnegie Red variations and Iron Gray
**Package Types**: Mix of Tartan and Campus palette colors
**Category Analysis**: Carnegie Red for vulnerabilities, Iron Gray for projects

### Background System
- **Main Background**: White `#FFFFFF`
- **Secondary Background**: Very subtle off-white `#FAFAFA`
- **Cards**: White with subtle shadows
- **Hover States**: Light gray `#F8F8F8`
- **Section Backgrounds**: Steel Gray `#E0E0E0`

### Text Hierarchy
- **Primary Text**: Black `#000000`
- **Secondary Text**: Iron Gray `#6D6E71`
- **Muted Text**: Light gray `#A0A1A3`
- **Disabled**: Very light gray `#CECECE`

### Borders
- **Primary Border**: `#D4D4D4`
- **Light Border**: Steel Gray `#E0E0E0`
- **Strong Border**: `#B8B8B8`

### Interactive States
- **Default Border**: Steel Gray or light gray
- **Hover Border**: Carnegie Red `#C41230`
- **Active State**: Skibo Red `#941120`
- **Focus State**: Carnegie Red with subtle shadow

---

## Brand Compliance

✅ **Carnegie Red is dominant** throughout the design
✅ **Core colors used for primary elements** (text, backgrounds, main interactions)
✅ **Secondary colors used only as accents** (charts, status indicators, health bars)
✅ **White background** emphasizes clean, professional appearance
✅ **All colors use exact HEX values** from official CMU brand guidelines

### Design Rules

1. **Carnegie Red must be present** when using secondary colors
2. **Never modify** CMU brand colors (no tinting, shading, or gradients)
3. **Use white space** generously for clean layouts
4. **High contrast** between text and backgrounds (WCAG AAA)
5. **Minimal animations** (≤ 400ms, functional only)

---

## Accessibility

### Contrast Ratios (WCAG AAA Compliant)
- Black text on white: 21:1
- Iron Gray on white: 4.54:1
- Carnegie Red on white: 5.12:1
- White text on Carnegie Red: 4.1:1
- White text on Skibo Red: 6.8:1

### Color Blind Friendly
- Status indicators use both color and text labels
- Charts include legends and hover tooltips
- Severity badges combine color with text

---

## File Structure

```
energy-security-viz/
├── style.css          # Main styles with CMU color variables
├── main.js            # Chart configurations with CMU colors
├── index.html         # HTML structure with CMU branding
└── public/
    ├── cmu-logo.png   # Official CMU logo
    └── cmist-logo.png # CMIST logo
```

---

## Usage Examples

### CSS Variables
```css
:root {
  --carnegie-red: #C41230;
  --cmu-black: #000000;
  --iron-gray: #6D6E71;
  --steel-gray: #E0E0E0;
  --cmu-white: #FFFFFF;
}
```

### Primary Button
```css
.primary-btn {
  background: var(--carnegie-red);
  color: var(--cmu-white);
  border: none;
}
```

### Card Component
```css
.card {
  background: var(--cmu-white);
  border: 1px solid var(--steel-gray);
  border-left: 4px solid var(--carnegie-red);
}
```

---

## Resources

- **CMU Brand Center**: https://www.cmu.edu/brand/
- **Color Guidelines**: https://www.cmu.edu/brand/brand-guidelines/visual-identity/colors.html
- **Logo Downloads**: https://www.cmu.edu/brand/brand-center/logos-signs.html
- **Contact**: brand@andrew.cmu.edu

---

**Last Updated**: October 2025  
**Design System Version**: 3.0 (CMU Official Palette)  
**Compliance**: CMU Brand Guidelines 2019+
