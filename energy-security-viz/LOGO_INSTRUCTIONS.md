# CMU Logo Instructions

## Where to Get CMU Logos

### Official CMU Brand Center
Visit the official Carnegie Mellon University Brand Center to download approved logos:
- **Main Brand Center**: https://www.cmu.edu/brand/brand-center/index.html
- **Logo Downloads**: https://www.cmu.edu/brand/brand-center/logos-signs.html

### Logo Requirements

According to [CMU's brand guidelines](https://www.cmu.edu/brand/brand-guidelines/visual-identity/colors.html#core), you should use:

1. **CMU Wordmark** or **University Seal**
   - Available in multiple formats (PNG, SVG, EPS)
   - Use the version appropriate for light backgrounds
   - Download from the Brand Center

2. **CMIST Logo** (if applicable)
   - Contact your department or the Communications office
   - Ensure it follows CMU brand guidelines

### How to Add Logos to Your Dashboard

1. **Download the logos** from the CMU Brand Center
2. **Save them** in the `public` folder:
   ```
   energy-security-viz/
   └── public/
       ├── cmu-logo.png
       ├── cmist-logo.png
       └── vulnerability-data.json
   ```

3. **Recommended formats**:
   - PNG with transparent background (preferred)
   - SVG for scalability
   - Height: At least 120px for best quality (will display at 60px)

4. **File naming**:
   - CMU logo: `cmu-logo.png` (or `.svg`)
   - CMIST logo: `cmist-logo.png` (or `.svg`)

### If Using SVG Format

If you prefer SVG logos, update `index.html`:

```html
<img src="/cmu-logo.svg" alt="Carnegie Mellon University" class="header-logo">
<img src="/cmist-logo.svg" alt="CMIST" class="header-logo">
```

### Brand Compliance

- Only use **approved CMU logos** from the official Brand Center
- Do not modify, stretch, or alter logo proportions
- Maintain proper clear space around logos
- Use appropriate version for light/white backgrounds

### Contact for Logo Access

If you need help accessing logos:
- **CMU Communications**: communications@andrew.cmu.edu
- **Brand Questions**: brand@andrew.cmu.edu
- **CMIST-specific logos**: Contact your department administrator

---

## Current Implementation

The dashboard is configured to:
- Display logos at 60px height (45px on mobile)
- Center logos horizontally above the title
- Hide logos gracefully if files are not found (using `onerror`)
- Scale logos on hover for subtle interaction

Once you add the logo files to the `public` folder, they will automatically appear in the header.

