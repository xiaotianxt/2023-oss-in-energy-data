# 🚀 Quick Start Guide

## ⚡ View the Dashboard NOW!

```bash
cd energy-security-viz
npm run dev
```

Then open: **http://localhost:5173**

---

## 🎯 What You'll See

### Five Interactive Tabs:

1. **🌐 Ecosystem View** - Overall security landscape
2. **📦 Package Analysis** - Interactive bubble chart of vulnerable packages  
3. **🚀 Project Explorer** - Search and filter projects
4. **📊 Category Insights** - Energy sector comparisons
5. **🕸️ Dependency Network** - Risk propagation visualization

---

## 💡 Tips for Best Experience

### Bubble Charts
- **Hover** over bubbles to see details
- **Size** = vulnerability count
- **Color** = impact/category

### Filters
- Use search bar in Project Explorer
- Filter by category, status
- Results update instantly!

### Network Graph
- **Drag** nodes to rearrange
- **Click** CVE links to see details
- **Hover** for package info

---

## 📊 Key Stats You'll Find

- **375** total projects analyzed
- **132** vulnerable projects (35.2%)
- **4,675** total vulnerabilities
- **694** unique vulnerable packages

---

## 🔧 Troubleshooting

### Charts Not Visible?
1. **Hard refresh**: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. **Check browser console**: Press F12
3. **Restart dev server**: Stop with Ctrl+C, run `npm run dev` again

### Data Not Loading?
1. Ensure `public/vulnerability-data.json` exists
2. Run: `python3 analyze_vulnerabilities.py`
3. Check file size: `ls -lh energy-security-viz/public/`

---

## 🚢 Deploy to Production

```bash
# Build
npm run build

# Preview
npm run preview

# Deploy /dist folder to:
# - Netlify
# - Vercel
# - GitHub Pages
# - Any static hosting
```

---

## 📱 Mobile Friendly

The dashboard works great on:
- Desktop computers
- Tablets
- Mobile phones

All visualizations are responsive!

---

## 🎨 What Makes It Cool

✨ **Interactive** - Hover, click, drag, filter  
✨ **Beautiful** - Dark theme, smooth animations  
✨ **Responsive** - Works on all screen sizes  
✨ **Fast** - Built with Vite for speed  
✨ **Insightful** - 5 different analytical perspectives  

---

**Enjoy exploring the Energy Sector Security Dashboard!** 🎉

*Questions? Check VISUALIZATION_GUIDE.md for detailed documentation.*


