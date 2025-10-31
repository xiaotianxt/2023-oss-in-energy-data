# ⚡ Energy Sector Open Source Security Dashboard

An interactive, comprehensive visualization dashboard for analyzing security vulnerabilities in 375 energy-related open source projects.

## 🎨 Features

### 📊 Multi-Perspective Analysis

1. **Ecosystem View** 🌐
   - Vulnerability distribution by severity
   - Package type breakdown
   - Language vulnerability landscape
   - Category health scores

2. **Package Analysis** 📦
   - Interactive bubble chart showing most vulnerable packages
   - Bubble size = number of vulnerabilities
   - Color intensity = number of projects affected
   - Top 20 risky dependencies table

3. **Project Explorer** 🚀
   - Filterable project visualization
   - Search by name, filter by category and status
   - Interactive bubble chart of vulnerable projects
   - Detailed project cards

4. **Category Insights** 📊
   - Vulnerabilities by energy sector category
   - Project distribution analysis
   - Comprehensive comparison matrix
   - Average vulnerabilities per project

5. **Dependency Network** 🕸️
   - Interactive force-directed graph
   - Risk score visualization (vulnerabilities × projects affected)
   - Draggable nodes for exploration
   - Most common CVEs and GHSAs

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
energy-security-viz/
├── index.html          # Main HTML structure
├── main.js            # JavaScript application logic
├── style.css          # Responsive CSS styles
├── public/
│   └── vulnerability-data.json  # Generated vulnerability data
├── package.json
└── README.md
```

## 🎯 Data Source

The visualization uses data from:
- **Grype** vulnerability scanner
- **Syft** SBOM generator
- 375 energy sector open source projects
- 4,675+ vulnerability records analyzed

## 💡 Visualization Techniques

### Bubble Charts
- **Size**: Represents magnitude (vulnerabilities, projects)
- **Color**: Represents impact or category
- **Position**: Force-directed layout for natural grouping

### Bar Charts
- Category comparisons
- Language analysis
- Project distributions

### Doughnut/Pie Charts
- Severity distributions
- Package type breakdowns

### Health Bars
- Category security health scores
- Clean vs vulnerable project ratios

### Network Graphs
- Dependency relationships
- Risk propagation visualization
- Interactive exploration

## 🎨 Design Principles

### Responsive Design
- Mobile-first approach
- Flexible grid layouts
- Touch-friendly interactions
- Adaptive typography

### Dark Theme
- Easy on the eyes for extended use
- High contrast for accessibility
- Color-coded severity levels
- Professional appearance

### Interactivity
- Hover tooltips for detailed information
- Clickable elements for exploration
- Filterable and searchable data
- Smooth animations and transitions

## 📊 Key Metrics Displayed

- **Total Projects**: 375
- **Vulnerable Projects**: 132 (35.2%)
- **Clean Projects**: 243 (64.8%)
- **Total Vulnerabilities**: 4,675
- **Unique Vulnerable Packages**: 694
- **Unique CVEs**: Various

## 🔍 Understanding the Visualizations

### Risk Score Calculation
```
Risk Score = Vulnerabilities × Projects Affected
```

### Health Score Calculation
```
Health Score = (Clean Projects / Total Projects) × 100
```

### Severity Levels
- 🔴 **Critical**: Immediate action required
- 🟠 **High**: High priority fixes
- 🟡 **Medium**: Medium priority
- 🟢 **Low**: Low priority
- ⚪ **Negligible**: Minimal risk

## 🛠️ Technologies Used

- **Vite**: Fast build tool and dev server
- **D3.js**: Advanced data visualizations
- **Chart.js**: Beautiful charts
- **Vanilla JavaScript**: No framework overhead
- **CSS Grid & Flexbox**: Modern layouts

## 📱 Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🎓 Use Cases

1. **Security Auditing**: Identify high-risk projects and dependencies
2. **Risk Assessment**: Prioritize remediation efforts
3. **Research**: Analyze security trends in energy sector
4. **Education**: Understand vulnerability landscapes
5. **Reporting**: Generate insights for stakeholders

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This visualization project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

- **Grype** by Anchore for vulnerability scanning
- **Syft** by Anchore for SBOM generation
- D3.js and Chart.js communities
- All open source contributors in the energy sector

## 📞 Contact

For questions or feedback about this visualization, please open an issue in the repository.

---

**Built with ❤️ for the Energy Open Source Community**


