import './style.css';
import * as d3 from 'd3';
import Chart from 'chart.js/auto';

// Global data storage
let vulnData = null;
let sourceCodeData = null;

// Initialize the application
async function init() {
  try {
    console.log('Loading vulnerability data...');
    
    // Load both data files in parallel
    const [vulnResponse, sourceCodeResponse] = await Promise.all([
      fetch('/vulnerability-data.json'),
      fetch('/sourcecode-vulnerabilities.json')
    ]);
    
    if (!vulnResponse.ok) {
      throw new Error(`HTTP error! status: ${vulnResponse.status}`);
    }
    
    vulnData = await vulnResponse.json();
    console.log('Vulnerability data loaded successfully:', vulnData.overview);
    
    // Load source code data (optional, don't fail if missing)
    if (sourceCodeResponse.ok) {
      sourceCodeData = await sourceCodeResponse.json();
      console.log('Source code data loaded successfully:', sourceCodeData.overview);
    } else {
      console.warn('Source code data not available');
    }
    
    // Setup the UI
    setupTabs();
    renderStats();
    renderEcosystemView();
    renderPackageAnalysis();
    renderProjectExplorer();
    renderCategoryInsights();
    renderDependencyNetwork();
    
    // Render source code analysis if data available
    if (sourceCodeData) {
      renderSourceCodeAnalysis();
    }
    
    // Set last update time
    document.getElementById('lastUpdate').textContent = new Date().toLocaleDateString();
    
    // Hide loading overlay
    showLoading(false);
    
  } catch (error) {
    console.error('Error loading data:', error);
    showLoading(false); // Hide loading overlay
    
      const app = document.getElementById('app');
    if (app) {
      app.innerHTML = `
        <div style="text-align: center; padding: 4rem; color: #C41230; max-width: 600px; margin: 0 auto;">
          <h2>Error Loading Data</h2>
          <p style="margin: 1rem 0; color: #6D6E71;">Please make sure the vulnerability-data.json file exists in the public folder.</p>
          <p style="margin: 1rem 0; color: #6D6E71; font-size: 0.9rem;">Error details: ${error.message}</p>
          <details style="margin-top: 2rem; text-align: left; background: #E0E0E0; padding: 1rem; border-radius: 8px;">
            <summary style="cursor: pointer; color: #C41230;">Troubleshooting Steps</summary>
            <ol style="margin-top: 1rem; color: #000000; line-height: 1.8;">
              <li>Make sure you've run: <code style="background: #FAFAFA; padding: 0.2rem 0.5rem; border-radius: 4px; border: 1px solid #D4D4D4;">python3 analyze_vulnerabilities.py</code></li>
              <li>Check that <code style="background: #FAFAFA; padding: 0.2rem 0.5rem; border-radius: 4px; border: 1px solid #D4D4D4;">public/vulnerability-data.json</code> exists</li>
              <li>Try restarting the dev server: <code style="background: #FAFAFA; padding: 0.2rem 0.5rem; border-radius: 4px; border: 1px solid #D4D4D4;">npm run dev</code></li>
              <li>Check browser console for more details (F12)</li>
            </ol>
          </details>
        </div>
      `;
    }
  }
}

// Setup tab navigation
function setupTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      
      // Update active states
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(targetTab).classList.add('active');
    });
  });
}

// Render overview statistics
function renderStats() {
  const { overview } = vulnData;
  const statsGrid = document.getElementById('statsGrid');
  
  const stats = [
    { label: 'Total Projects', value: overview.total_projects },
    { label: 'Vulnerable Projects', value: overview.vulnerable_projects },
    { label: 'Clean Projects', value: overview.clean_projects },
    { label: 'Total Vulnerabilities', value: overview.total_vulnerabilities.toLocaleString() },
    { label: 'Unique Packages', value: overview.unique_packages },
    { label: 'Unique CVEs', value: overview.unique_vulns },
  ];
  
  statsGrid.innerHTML = stats.map(stat => `
    <div class="stat-card">
      <span class="stat-value">${stat.value}</span>
      <span class="stat-label">${stat.label}</span>
    </div>
  `).join('');
}

// Ecosystem View
function renderEcosystemView() {
  renderSeverityChart();
  renderPackageTypeChart();
  renderLanguageChart();
  renderCategoryHealthChart();
}

function renderSeverityChart() {
  const ctx = document.getElementById('severityChart');
  const { severity_distribution } = vulnData;
  
  const colors = {
    'Critical': '#941120',  // Skibo Red
    'High': '#C41230',      // Carnegie Red
    'Medium': '#FDB515',    // Gold Thread
    'Low': '#009647',       // Green Thread
    'Negligible': '#6D6E71' // Iron Gray
  };
  
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: severity_distribution.map(s => s.severity),
      datasets: [{
        data: severity_distribution.map(s => s.count),
        backgroundColor: severity_distribution.map(s => colors[s.severity] || '#6D6E71'),
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#000000', font: { size: 12, weight: '500' } }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = ((context.raw / total) * 100).toFixed(1);
              return `${context.label}: ${context.raw} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function renderPackageTypeChart() {
  const ctx = document.getElementById('packageTypeChart');
  const { package_types } = vulnData;
  
  new Chart(ctx, {
    type: 'pie',
    data: {
      labels: package_types.map(p => p.type),
      datasets: [{
        data: package_types.map(p => p.count),
        backgroundColor: [
          '#C41230', '#EF3A47', '#007BC0', '#009647',
          '#FDB515', '#6D6E71', '#008F91', '#BCB49E'
        ],
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#000000', font: { size: 12, weight: '500' } }
        }
      }
    }
  });
}

function renderLanguageChart() {
  const ctx = document.getElementById('languageChart');
  const { language_analysis } = vulnData;
  
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: language_analysis.map(l => l.language),
      datasets: [{
        label: 'Vulnerabilities',
        data: language_analysis.map(l => l.vulnerabilities),
        backgroundColor: 'rgba(196, 18, 48, 0.8)',
        borderColor: '#C41230',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#941120'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `${context.raw} vulnerabilities`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { color: '#E0E0E0' }
        },
        y: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderCategoryHealthChart() {
  const container = document.getElementById('categoryHealthChart');
  const { category_health } = vulnData;
  
  // CMU color palette for health bars
  const getHealthColor = (healthScore) => {
    if (healthScore >= 90) return '#009647';  // Green Thread - Excellent
    if (healthScore >= 75) return '#007BC0';  // Highlands Sky - Good
    if (healthScore >= 60) return '#008F91';  // Teal Thread - Fair
    if (healthScore >= 40) return '#FDB515';  // Gold Thread - Warning
    if (healthScore >= 20) return '#EF3A47';  // Scots Rose - Poor
    return '#941120';  // Skibo Red - Critical
  };
  
  container.innerHTML = category_health.map(cat => {
    const barColor = getHealthColor(cat.health_score);
    return `
      <div class="health-bar-container">
        <div class="health-bar-label">
          <span><strong>${cat.category}</strong> (${cat.total_projects} projects)</span>
          <span>${cat.health_score}% healthy | ${cat.total_vulns} vulns</span>
        </div>
        <div class="health-bar">
          <div class="health-bar-fill" style="width: ${cat.health_score}%; background: ${barColor};">
            ${cat.clean} clean / ${cat.vulnerable} vulnerable
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// Package Analysis
function renderPackageAnalysis() {
  renderPackageTable();
}

function renderPackageTable() {
  const container = document.getElementById('packageTable');
  const { top_packages } = vulnData;
  
  container.innerHTML = `
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Package</th>
            <th>Version</th>
            <th>Type</th>
            <th>Vulnerabilities</th>
            <th>Projects Affected</th>
            <th>Risk Score</th>
          </tr>
        </thead>
        <tbody>
          ${top_packages.slice(0, 20).map((pkg, idx) => `
            <tr>
              <td>${idx + 1}</td>
              <td><strong>${pkg.package}</strong></td>
              <td>${pkg.version}</td>
              <td><span class="severity-badge severity-Medium">${pkg.type}</span></td>
              <td>${pkg.vulnerabilities}</td>
              <td>${pkg.projects_affected}</td>
              <td><strong>${(pkg.vulnerabilities * pkg.projects_affected).toFixed(0)}</strong></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// Project Explorer
function renderProjectExplorer() {
  const { project_distribution, category_analysis } = vulnData;
  
  // Populate category filter
  const categoryFilter = document.getElementById('categoryFilter');
  const categories = [...new Set(project_distribution.map(p => p.category))].sort();
  categoryFilter.innerHTML = '<option value="">All Categories</option>' + categories.map(cat => 
    `<option value="${cat}">${cat}</option>`
  ).join('');
  
  // Render initial project list
  renderProjectList(project_distribution);
  
  // Setup filters
  const searchInput = document.getElementById('projectSearch');
  const statusFilter = document.getElementById('statusFilter');
  
  const applyFilters = () => {
    const searchTerm = searchInput.value.toLowerCase();
    const selectedCategory = categoryFilter.value;
    const selectedStatus = statusFilter.value;
    
    const filtered = project_distribution.filter(p => {
      const matchesSearch = p.project.toLowerCase().includes(searchTerm);
      const matchesCategory = selectedCategory === '' || p.category === selectedCategory;
      const matchesStatus = selectedStatus === '' || p.status === selectedStatus;
      return matchesSearch && matchesCategory && matchesStatus;
    });
    
    renderProjectList(filtered);
  };
  
  searchInput.addEventListener('input', applyFilters);
  categoryFilter.addEventListener('change', applyFilters);
  statusFilter.addEventListener('change', applyFilters);
}

function renderProjectBubbleChart(projects) {
  const container = document.getElementById('projectBubbleChart');
  const width = container.clientWidth || container.parentElement?.clientWidth || 1200;
  const height = 600;
  
  container.innerHTML = '';
  
  const vulnerableProjects = projects.filter(p => p.vulnerabilities > 0).slice(0, 50);
  
  if (vulnerableProjects.length === 0) {
    container.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--text-secondary);">No vulnerable projects found with current filters.</p>';
    return;
  }
  
  const svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');
  
  const radiusScale = d3.scaleSqrt()
    .domain([0, d3.max(vulnerableProjects, d => d.vulnerabilities)])
    .range([15, 70]);
  
  const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
  
  const simulation = d3.forceSimulation(vulnerableProjects)
    .force('charge', d3.forceManyBody().strength(10))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => radiusScale(d.vulnerabilities) + 2));
  
  const tooltip = d3.select('body').select('.tooltip').empty() 
    ? d3.select('body').append('div').attr('class', 'tooltip')
    : d3.select('body').select('.tooltip');
  
  const bubbles = svg.selectAll('circle')
    .data(vulnerableProjects)
    .enter()
    .append('circle')
    .attr('r', d => radiusScale(d.vulnerabilities))
    .attr('fill', d => colorScale(d.category))
    .attr('opacity', 0.8)
    .attr('stroke', '#D4D4D4')
    .attr('stroke-width', 2)
    .on('mouseover', (event, d) => {
      tooltip
        .html(`
          <strong>${d.project}</strong><br/>
          <strong>Category:</strong> ${d.category}<br/>
          <strong>Vulnerabilities:</strong> ${d.vulnerabilities}<br/>
          <strong>Unique Packages:</strong> ${d.details.unique_packages}<br/>
          <strong>Status:</strong> ${d.status}
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px')
        .classed('show', true);
      
      d3.select(event.currentTarget)
        .attr('stroke', '#C41230')
        .attr('stroke-width', 3);
    })
    .on('mouseout', (event) => {
      tooltip.classed('show', false);
      d3.select(event.currentTarget)
        .attr('stroke', '#D4D4D4')
        .attr('stroke-width', 2);
    });
  
  simulation.on('tick', () => {
    bubbles
      .attr('cx', d => Math.max(radiusScale(d.vulnerabilities), Math.min(width - radiusScale(d.vulnerabilities), d.x)))
      .attr('cy', d => Math.max(radiusScale(d.vulnerabilities), Math.min(height - radiusScale(d.vulnerabilities), d.y)));
  });
}

function renderProjectList(projects) {
  const container = document.getElementById('projectList');
  const countElement = document.getElementById('projectCount');
  
  // Update the count display
  if (countElement) {
    countElement.textContent = projects.length;
  }
  
  // Show first 50 projects (adjust as needed)
  const displayProjects = projects.slice(0, 50);
  
  if (displayProjects.length === 0) {
    container.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--text-secondary);">No projects match the current filters.</p>';
    return;
  }
  
  container.innerHTML = `
    <div class="project-grid">
      ${displayProjects.map(p => `
        <div class="project-card ${p.repo_url ? 'clickable' : ''}" ${p.repo_url ? `onclick="window.open('${p.repo_url}', '_blank')"` : ''}>
          <h4>${p.project}</h4>
          <div class="meta">
            <span>${p.category}</span><br/>
            <span>${p.languages || 'N/A'}</span>
          </div>
          <div class="vuln-count" style="color: ${p.vulnerabilities > 0 ? 'var(--danger)' : 'var(--success)'};">
            ${p.vulnerabilities} ${p.vulnerabilities === 1 ? 'vulnerability' : 'vulnerabilities'}
          </div>
          <div style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">
            ${p.details.unique_packages > 0 ? `${p.details.unique_packages} unique packages affected` : 'No vulnerable packages'}
          </div>
          ${p.repo_url ? '<div class="repo-link-indicator">Click to view repository →</div>' : ''}
        </div>
      `).join('')}
    </div>
    ${projects.length > 50 ? `<p style="text-align: center; margin-top: 1rem; color: var(--text-secondary); font-size: 0.9rem;">Showing first 50 of ${projects.length} projects</p>` : ''}
  `;
}

// Category Insights
function renderCategoryInsights() {
  renderCategoryVulnChart();
  renderCategoryProjectChart();
  renderCategoryMatrix();
}

function renderCategoryVulnChart() {
  const ctx = document.getElementById('categoryVulnChart');
  const { category_analysis } = vulnData;
  
  const topCategories = category_analysis.slice(0, 10);
  
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: topCategories.map(c => c.category),
      datasets: [{
        label: 'Total Vulnerabilities',
        data: topCategories.map(c => c.vulnerabilities),
        backgroundColor: 'rgba(196, 18, 48, 0.8)',
        borderColor: '#C41230',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#941120'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          ticks: { color: '#000000', maxRotation: 45, minRotation: 45, font: { weight: '500' } },
          grid: { display: false }
        },
        y: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { color: '#E0E0E0' }
        }
      }
    }
  });
}

function renderCategoryProjectChart() {
  const ctx = document.getElementById('categoryProjectChart');
  const { category_analysis } = vulnData;
  
  const topCategories = category_analysis.slice(0, 10);
  
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: topCategories.map(c => c.category),
      datasets: [{
        label: 'Vulnerable Projects',
        data: topCategories.map(c => c.projects),
        backgroundColor: 'rgba(109, 110, 113, 0.8)',
        borderColor: '#6D6E71',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#4A4B4D'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          ticks: { color: '#000000', maxRotation: 45, minRotation: 45, font: { weight: '500' } },
          grid: { display: false }
        },
        y: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { color: '#E0E0E0' }
        }
      }
    }
  });
}

function renderCategoryMatrix() {
  const container = document.getElementById('categoryMatrix');
  const { category_analysis } = vulnData;
  
  container.innerHTML = `
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Total Vulnerabilities</th>
            <th>Affected Projects</th>
            <th>Avg. Vulns per Project</th>
          </tr>
        </thead>
        <tbody>
          ${category_analysis.map(cat => `
            <tr>
              <td><strong>${cat.category}</strong></td>
              <td>${cat.vulnerabilities}</td>
              <td>${cat.projects}</td>
              <td>${cat.avg_vulns_per_project.toFixed(1)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// Dependency Network - table only, no bubble chart
function renderDependencyNetwork() {
  renderVulnTable();
}

function renderVulnTable() {
  const container = document.getElementById('vulnTable');
  const { top_vulnerabilities } = vulnData;
  
  container.innerHTML = `
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Vulnerability ID</th>
            <th>Occurrences</th>
          </tr>
        </thead>
        <tbody>
          ${top_vulnerabilities.slice(0, 20).map((vuln, idx) => `
            <tr>
              <td>${idx + 1}</td>
              <td><a href="https://github.com/advisories/${vuln.vuln_id}" target="_blank" style="color: var(--primary);">${vuln.vuln_id}</a></td>
              <td>${vuln.occurrences}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// Source Code Analysis
function renderSourceCodeAnalysis() {
  if (!sourceCodeData) return;
  
  const { overview, repositories } = sourceCodeData;
  
  // Update counts
  document.getElementById('sourceCodeRepoCount').textContent = overview.total_repositories;
  document.getElementById('sourceCodeIssueCount').textContent = overview.total_issues;
  
  // Render charts
  renderSourceCodeSeverityChart();
  renderSourceCodeCweChart();
  renderSourceCodeIssueTypeChart();
  
  // Populate category filter
  const categoryFilter = document.getElementById('sourceCodeCategoryFilter');
  const categories = [...new Set(repositories.map(r => r.category))].sort();
  categoryFilter.innerHTML = '<option value="">All Categories</option>' + 
    categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
  
  // Render repository list
  renderSourceCodeRepoList(repositories);
  
  // Setup filters
  setupSourceCodeFilters();
}

function renderSourceCodeSeverityChart() {
  const ctx = document.getElementById('sourceCodeSeverityChart');
  const { severity_distribution } = sourceCodeData.overview;
  
  const colors = {
    'HIGH': '#C41230',
    'MEDIUM': '#FDB515',
    'LOW': '#009647'
  };
  
  const labels = Object.keys(severity_distribution);
  const data = Object.values(severity_distribution);
  
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: labels.map(l => colors[l] || '#6D6E71'),
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#000000', font: { size: 12, weight: '500' } }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = ((context.raw / total) * 100).toFixed(1);
              return `${context.label}: ${context.raw} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function renderSourceCodeCweChart() {
  const ctx = document.getElementById('sourceCodeCweChart');
  const { cwe_distribution } = sourceCodeData;
  
  // CWE descriptions for better readability
  const cweDescriptions = {
    'CWE-78': 'OS Command Injection',
    'CWE-89': 'SQL Injection',
    'CWE-400': 'Resource Exhaustion',
    'CWE-502': 'Deserialization',
    'CWE-20': 'Input Validation',
    'CWE-22': 'Path Traversal',
    'CWE-377': 'Insecure Temp File',
    'CWE-327': 'Broken Crypto',
    'CWE-605': 'Command Injection',
    'CWE-80': 'XSS',
    'CWE-732': 'Incorrect Permissions',
    'CWE-295': 'Cert Validation',
    'CWE-94': 'Code Injection',
    'CWE-319': 'Cleartext Transmission'
  };
  
  const entries = Object.entries(cwe_distribution).slice(0, 10);
  const labels = entries.map(([cwe]) => cweDescriptions[cwe] || cwe);
  const data = entries.map(([, count]) => count);
  
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Occurrences',
        data: data,
        backgroundColor: 'rgba(196, 18, 48, 0.8)',
        borderColor: '#C41230',
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { color: '#E0E0E0' }
        },
        y: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderSourceCodeIssueTypeChart() {
  const ctx = document.getElementById('sourceCodeIssueTypeChart');
  const { issue_types } = sourceCodeData;
  
  // Simplify issue type names
  const simplifyIssueName = (name) => {
    const parts = name.split(':');
    return parts.length > 1 ? parts[1].replace(/_/g, ' ') : name;
  };
  
  const entries = Object.entries(issue_types).slice(0, 15);
  const labels = entries.map(([type]) => simplifyIssueName(type));
  const data = entries.map(([, count]) => count);
  
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Occurrences',
        data: data,
        backgroundColor: [
          '#C41230', '#EF3A47', '#007BC0', '#009647', '#FDB515',
          '#6D6E71', '#008F91', '#BCB49E', '#043673', '#941120',
          '#719F94', '#182C4B', '#1F4C4C', '#E4DAC4', '#4A4B4D'
        ],
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          ticks: { 
            color: '#000000', 
            font: { weight: '500', size: 10 },
            maxRotation: 45,
            minRotation: 45
          },
          grid: { display: false }
        },
        y: {
          ticks: { color: '#000000', font: { weight: '500' } },
          grid: { color: '#E0E0E0' }
        }
      }
    }
  });
}

function renderSourceCodeRepoList(repositories) {
  const container = document.getElementById('sourceCodeRepoList');
  
  if (repositories.length === 0) {
    container.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--text-secondary);">No repositories match the current filters.</p>';
    return;
  }
  
  container.innerHTML = `
    <div class="table-container">
      <table class="data-table source-code-table">
        <thead>
          <tr>
            <th>Repository</th>
            <th>Category</th>
            <th>Total Issues</th>
            <th>High</th>
            <th>Medium</th>
            <th>Top CWE</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${repositories.map(repo => {
            const highCount = repo.severity_counts['HIGH'] || 0;
            const mediumCount = repo.severity_counts['MEDIUM'] || 0;
            const topCwe = Object.entries(repo.cwe_counts).sort((a, b) => b[1] - a[1])[0];
            
            return `
              <tr class="repo-row" data-repo="${repo.name}">
                <td>
                  <strong>${repo.name}</strong>
                  ${repo.url ? `<a href="${repo.url}" target="_blank" class="repo-external-link" title="View on GitHub">↗</a>` : ''}
                </td>
                <td><span class="category-badge">${repo.category}</span></td>
                <td><strong>${repo.total_issues}</strong></td>
                <td><span class="severity-badge severity-High">${highCount}</span></td>
                <td><span class="severity-badge severity-Medium">${mediumCount}</span></td>
                <td>${topCwe ? `${topCwe[0]} (${topCwe[1]})` : '-'}</td>
                <td><button class="view-code-btn" data-repo="${repo.name}">View Code</button></td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
  
  // Add click handlers for view code buttons
  container.querySelectorAll('.view-code-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const repoName = btn.dataset.repo;
      showSourceCodeSnippets(repoName);
    });
  });
  
  // Add click handler for rows
  container.querySelectorAll('.repo-row').forEach(row => {
    row.addEventListener('click', () => {
      const repoName = row.dataset.repo;
      showSourceCodeSnippets(repoName);
    });
  });
}

function showSourceCodeSnippets(repoName) {
  const repo = sourceCodeData.repositories.find(r => r.name === repoName);
  if (!repo) return;
  
  const detailCard = document.getElementById('sourceCodeDetailCard');
  const snippetsContainer = document.getElementById('sourceCodeSnippets');
  const selectedRepoName = document.getElementById('selectedRepoName');
  
  selectedRepoName.textContent = `${repo.name} (${repo.total_issues} issues)`;
  detailCard.style.display = 'block';
  
  // Sort issues by severity (HIGH first)
  const sortedIssues = [...repo.issues].sort((a, b) => {
    const order = { 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2 };
    return (order[a.severity] || 3) - (order[b.severity] || 3);
  });
  
  snippetsContainer.innerHTML = `
    <div class="code-snippets-container">
      ${sortedIssues.slice(0, 50).map((issue, idx) => `
        <div class="code-snippet-card">
          <div class="snippet-header">
            <span class="severity-badge severity-${issue.severity === 'HIGH' ? 'High' : 'Medium'}">${issue.severity}</span>
            <span class="cwe-badge">${issue.cwe}</span>
            <span class="confidence-badge">${issue.confidence}</span>
          </div>
          <div class="snippet-issue-id">${issue.issue_id}</div>
          <div class="snippet-description">${issue.description}</div>
          <div class="snippet-location">
            <strong>Location:</strong> ${formatLocation(issue.location)}
          </div>
          <div class="snippet-code">
            <pre><code>${escapeHtml(formatCodeSnippet(issue.code_snippet))}</code></pre>
          </div>
        </div>
      `).join('')}
      ${sortedIssues.length > 50 ? `<p class="more-issues-note">Showing first 50 of ${sortedIssues.length} issues</p>` : ''}
    </div>
  `;
  
  // Scroll to the detail card
  detailCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function formatLocation(location) {
  if (!location) return 'Unknown';
  // Clean up the path - remove temp_repos prefix and normalize slashes
  return location
    .replace(/temp_repos\\repo_\d+\\/g, '')
    .replace(/\\/g, '/')
    .replace(/^\/+/, '');
}

function formatCodeSnippet(snippet) {
  if (!snippet) return 'No code snippet available';
  // Convert line number prefixes to more readable format
  return snippet
    .split('\\n')
    .join('\n')
    .replace(/^(\d+)\t/gm, '$1 | ');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function setupSourceCodeFilters() {
  const searchInput = document.getElementById('sourceCodeSearch');
  const categoryFilter = document.getElementById('sourceCodeCategoryFilter');
  const severityFilter = document.getElementById('sourceCodeSeverityFilter');
  
  const applyFilters = () => {
    const searchTerm = searchInput.value.toLowerCase();
    const selectedCategory = categoryFilter.value;
    const selectedSeverity = severityFilter.value;
    
    const filtered = sourceCodeData.repositories.filter(repo => {
      const matchesSearch = repo.name.toLowerCase().includes(searchTerm);
      const matchesCategory = selectedCategory === '' || repo.category === selectedCategory;
      const matchesSeverity = selectedSeverity === '' || 
        (repo.severity_counts[selectedSeverity] && repo.severity_counts[selectedSeverity] > 0);
      return matchesSearch && matchesCategory && matchesSeverity;
    });
    
    renderSourceCodeRepoList(filtered);
  };
  
  searchInput.addEventListener('input', applyFilters);
  categoryFilter.addEventListener('change', applyFilters);
  severityFilter.addEventListener('change', applyFilters);
}

// Show loading overlay
function showLoading(show = true) {
  let overlay = document.getElementById('loadingOverlay');
  
  if (show && !overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 255, 255, 0.95);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      z-index: 9999;
      color: #000000;
    `;
    overlay.innerHTML = `
      <div class="spinner" style="width: 60px; height: 60px; border: 4px solid #E0E0E0; border-top-color: #C41230; border-radius: 50%; animation: spin 1s linear infinite;"></div>
      <h2 style="margin-top: 2rem;">Loading Security Dashboard...</h2>
      <p style="color: #6D6E71; margin-top: 0.5rem;">Analyzing 375 energy sector projects</p>
    `;
    document.body.appendChild(overlay);
  } else if (!show && overlay) {
    overlay.remove();
  }
}

// Sticky header scroll effect
function handleScroll() {
  const header = document.querySelector('.header');
  const tabs = document.querySelector('.tabs');
  
  if (window.scrollY > 100) {
    tabs.classList.add('scrolled');
  } else {
    tabs.classList.remove('scrolled');
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    showLoading(true);
    init();
    window.addEventListener('scroll', handleScroll);
  });
} else {
  showLoading(true);
  init();
  window.addEventListener('scroll', handleScroll);
}

