import './style.css';
import * as d3 from 'd3';
import Chart from 'chart.js/auto';

// Global data storage
let vulnData = null;

// Initialize the application
async function init() {
  try {
    console.log('Loading vulnerability data...');
    
    // Load data
    const response = await fetch('/vulnerability-data.json');
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    vulnData = await response.json();
    console.log('Data loaded successfully:', vulnData.overview);
    
    // Setup the UI
    setupTabs();
    renderStats();
    renderEcosystemView();
    renderPackageAnalysis();
    renderProjectExplorer();
    renderCategoryInsights();
    renderDependencyNetwork();
    
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
        <div style="text-align: center; padding: 4rem; color: #ef4444; max-width: 600px; margin: 0 auto;">
          <h2>❌ Error Loading Data</h2>
          <p style="margin: 1rem 0; color: #cbd5e1;">Please make sure the vulnerability-data.json file exists in the public folder.</p>
          <p style="margin: 1rem 0; color: #cbd5e1; font-size: 0.9rem;">Error details: ${error.message}</p>
          <details style="margin-top: 2rem; text-align: left; background: #1e293b; padding: 1rem; border-radius: 8px;">
            <summary style="cursor: pointer; color: #f59e0b;">Troubleshooting Steps</summary>
            <ol style="margin-top: 1rem; color: #cbd5e1; line-height: 1.8;">
              <li>Make sure you've run: <code style="background: #0f172a; padding: 0.2rem 0.5rem; border-radius: 4px;">python3 analyze_vulnerabilities.py</code></li>
              <li>Check that <code style="background: #0f172a; padding: 0.2rem 0.5rem; border-radius: 4px;">public/vulnerability-data.json</code> exists</li>
              <li>Try restarting the dev server: <code style="background: #0f172a; padding: 0.2rem 0.5rem; border-radius: 4px;">npm run dev</code></li>
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
    { label: 'Total Projects', value: overview.total_projects, icon: '🚀' },
    { label: 'Vulnerable Projects', value: overview.vulnerable_projects, icon: '⚠️' },
    { label: 'Clean Projects', value: overview.clean_projects, icon: '✅' },
    { label: 'Total Vulnerabilities', value: overview.total_vulnerabilities.toLocaleString(), icon: '🔍' },
    { label: 'Unique Packages', value: overview.unique_packages, icon: '📦' },
    { label: 'Unique CVEs', value: overview.unique_vulns, icon: '🔐' },
  ];
  
  statsGrid.innerHTML = stats.map(stat => `
    <div class="stat-card">
      <span class="stat-value">${stat.icon} ${stat.value}</span>
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
    'Critical': '#922b21',
    'High': '#c0392b',
    'Medium': '#f39c12',
    'Low': '#27ae60',
    'Negligible': '#6b7280'
  };
  
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: severity_distribution.map(s => s.severity),
      datasets: [{
        data: severity_distribution.map(s => s.count),
        backgroundColor: severity_distribution.map(s => colors[s.severity] || '#6b7280'),
        borderWidth: 2,
        borderColor: '#1e293b'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#f1f5f9', font: { size: 12 } }
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
          '#e67e22', '#d35400', '#f39c12', '#16a085',
          '#27ae60', '#3d5a6b', '#c0392b', '#5a7a8e'
        ],
        borderWidth: 2,
        borderColor: '#0f1419'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#f1f5f9', font: { size: 12 } }
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
        backgroundColor: 'rgba(230, 126, 34, 0.8)',
        borderColor: '#e67e22',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#d35400'
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
          ticks: { color: '#cbd5e1' },
          grid: { color: '#475569' }
        },
        y: {
          ticks: { color: '#cbd5e1' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderCategoryHealthChart() {
  const container = document.getElementById('categoryHealthChart');
  const { category_health } = vulnData;
  
  container.innerHTML = category_health.map(cat => `
    <div class="health-bar-container">
      <div class="health-bar-label">
        <span><strong>${cat.category}</strong> (${cat.total_projects} projects)</span>
        <span>${cat.health_score}% healthy | ${cat.total_vulns} vulns</span>
      </div>
      <div class="health-bar">
        <div class="health-bar-fill" style="width: ${cat.health_score}%">
          ${cat.clean} clean / ${cat.vulnerable} vulnerable
        </div>
      </div>
    </div>
  `).join('');
}

// Package Analysis with Bubble Chart
function renderPackageAnalysis() {
  renderPackageTable();
}

function renderPackageBubbleChart() {
  const container = document.getElementById('packageBubbleChart');
  const { top_packages } = vulnData;
  
  // Get container width, fallback to parent or default
  const width = container.clientWidth || container.parentElement?.clientWidth || 1200;
  const height = 600;
  
  // Clear previous
  container.innerHTML = '';
  
  const svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');
  
  // Scales (define these BEFORE using them in simulation)
  const radiusScale = d3.scaleSqrt()
    .domain([0, d3.max(top_packages, d => d.vulnerabilities)])
    .range([10, 60]);
  
  const colorScale = d3.scaleSequential()
    .domain([0, d3.max(top_packages, d => d.projects_affected)])
    .interpolator(d3.interpolateRgb('#27ae60', '#c0392b'));
  
  // Create simulation (now radiusScale is defined)
  const simulation = d3.forceSimulation(top_packages.slice(0, 40))
    .force('charge', d3.forceManyBody().strength(5))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => radiusScale(d.vulnerabilities) + 2));
  
  // Tooltip
  const tooltip = d3.select('body').append('div')
    .attr('class', 'tooltip')
    .style('position', 'absolute');
  
  // Draw bubbles
  const bubbles = svg.selectAll('circle')
    .data(top_packages.slice(0, 40))
    .enter()
    .append('circle')
    .attr('r', d => radiusScale(d.vulnerabilities))
    .attr('fill', d => colorScale(d.projects_affected))
    .attr('opacity', 0.8)
    .attr('stroke', '#1e293b')
    .attr('stroke-width', 2)
    .on('mouseover', (event, d) => {
      tooltip
        .style('opacity', 1)
        .html(`
          <strong>${d.package}</strong> v${d.version}<br/>
          <strong>Vulnerabilities:</strong> ${d.vulnerabilities}<br/>
          <strong>Projects Affected:</strong> ${d.projects_affected}<br/>
          <strong>Type:</strong> ${d.type}
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px')
        .classed('show', true);
      
      d3.select(event.currentTarget)
        .attr('stroke', '#f59e0b')
        .attr('stroke-width', 3);
    })
    .on('mouseout', (event) => {
      tooltip.classed('show', false);
      d3.select(event.currentTarget)
        .attr('stroke', '#1e293b')
        .attr('stroke-width', 2);
    });
  
  // Add labels for top 10
  const labels = svg.selectAll('text')
    .data(top_packages.slice(0, 10))
    .enter()
    .append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dy', 4)
    .text(d => d.package.length > 12 ? d.package.slice(0, 12) + '...' : d.package);
  
  // Update positions on tick
  simulation.on('tick', () => {
    bubbles
      .attr('cx', d => Math.max(radiusScale(d.vulnerabilities), Math.min(width - radiusScale(d.vulnerabilities), d.x)))
      .attr('cy', d => Math.max(radiusScale(d.vulnerabilities), Math.min(height - radiusScale(d.vulnerabilities), d.y)));
    
    labels
      .attr('x', d => Math.max(radiusScale(d.vulnerabilities), Math.min(width - radiusScale(d.vulnerabilities), d.x)))
      .attr('y', d => Math.max(radiusScale(d.vulnerabilities), Math.min(height - radiusScale(d.vulnerabilities), d.y)));
  });
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
  categoryFilter.innerHTML += categories.map(cat => 
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
      const matchesCategory = !selectedCategory || p.category === selectedCategory;
      const matchesStatus = !selectedStatus || p.status === selectedStatus;
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
    .attr('opacity', 0.7)
    .attr('stroke', '#1e293b')
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
        .attr('stroke', '#f59e0b')
        .attr('stroke-width', 3);
    })
    .on('mouseout', (event) => {
      tooltip.classed('show', false);
      d3.select(event.currentTarget)
        .attr('stroke', '#1e293b')
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
  const vulnerableProjects = projects.filter(p => p.vulnerabilities > 0).slice(0, 20);
  
  container.innerHTML = `
    <div class="project-grid">
      ${vulnerableProjects.map(p => `
        <div class="project-card ${p.repo_url ? 'clickable' : ''}" ${p.repo_url ? `onclick="window.open('${p.repo_url}', '_blank')"` : ''}>
          <h4>${p.project}</h4>
          <div class="meta">
            <span>📂 ${p.category}</span><br/>
            <span>💻 ${p.languages || 'N/A'}</span>
          </div>
          <div class="vuln-count">${p.vulnerabilities} vulnerabilities</div>
          <div style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">
            ${p.details.unique_packages} unique packages affected
          </div>
          ${p.repo_url ? '<div class="repo-link-indicator">🔗 Click to view repository</div>' : ''}
        </div>
      `).join('')}
    </div>
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
        backgroundColor: 'rgba(192, 57, 43, 0.8)',
        borderColor: '#c0392b',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#922b21'
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
          ticks: { color: '#cbd5e1', maxRotation: 45, minRotation: 45 },
          grid: { display: false }
        },
        y: {
          ticks: { color: '#cbd5e1' },
          grid: { color: '#475569' }
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
        backgroundColor: 'rgba(61, 90, 107, 0.8)',
        borderColor: '#3d5a6b',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#2c4050'
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
          ticks: { color: '#cbd5e1', maxRotation: 45, minRotation: 45 },
          grid: { display: false }
        },
        y: {
          ticks: { color: '#cbd5e1' },
          grid: { color: '#475569' }
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

// Dependency Network
function renderDependencyNetwork() {
  renderNetworkGraph();
  renderVulnTable();
}

function renderNetworkGraph() {
  const container = document.getElementById('networkGraph');
  const { dependency_network } = vulnData;
  
  const width = container.clientWidth || container.parentElement?.clientWidth || 1200;
  const height = 700;
  
  container.innerHTML = '';
  
  const topDeps = dependency_network.slice(0, 30);
  
  const svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');
  
  // Create a force simulation
  const simulation = d3.forceSimulation(topDeps)
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => Math.sqrt(d.risk_score) / 2 + 20));
  
  const colorScale = d3.scaleSequential()
    .domain([0, d3.max(topDeps, d => d.risk_score)])
    .interpolator(d3.interpolateRgb('#16a085', '#c0392b'));
  
  const radiusScale = d3.scaleSqrt()
    .domain([0, d3.max(topDeps, d => d.risk_score)])
    .range([15, 50]);
  
  const tooltip = d3.select('body').select('.tooltip').empty() 
    ? d3.select('body').append('div').attr('class', 'tooltip')
    : d3.select('body').select('.tooltip');
  
  const nodes = svg.selectAll('circle')
    .data(topDeps)
    .enter()
    .append('circle')
    .attr('class', 'node')
    .attr('r', d => radiusScale(d.risk_score))
    .attr('fill', d => colorScale(d.risk_score))
    .attr('stroke', '#1e293b')
    .attr('stroke-width', 2)
    .on('mouseover', (event, d) => {
      tooltip
        .html(`
          <strong>${d.package}</strong><br/>
          <strong>Version:</strong> ${d.version}<br/>
          <strong>Type:</strong> ${d.type}<br/>
          <strong>Vulnerabilities:</strong> ${d.vulnerabilities}<br/>
          <strong>Projects Affected:</strong> ${d.projects_affected}<br/>
          <strong>Risk Score:</strong> ${d.risk_score}
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px')
        .classed('show', true);
    })
    .on('mouseout', () => {
      tooltip.classed('show', false);
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));
  
  const labels = svg.selectAll('text')
    .data(topDeps)
    .enter()
    .append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .text(d => d.package.length > 10 ? d.package.slice(0, 10) + '...' : d.package);
  
  simulation.on('tick', () => {
    nodes
      .attr('cx', d => Math.max(radiusScale(d.risk_score), Math.min(width - radiusScale(d.risk_score), d.x)))
      .attr('cy', d => Math.max(radiusScale(d.risk_score), Math.min(height - radiusScale(d.risk_score), d.y)));
    
    labels
      .attr('x', d => Math.max(radiusScale(d.risk_score), Math.min(width - radiusScale(d.risk_score), d.x)))
      .attr('y', d => Math.max(radiusScale(d.risk_score), Math.min(height - radiusScale(d.risk_score), d.y)) + radiusScale(d.risk_score) + 15);
  });
  
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }
  
  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }
  
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }
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
      background: rgba(15, 23, 42, 0.95);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      z-index: 9999;
      color: #f1f5f9;
    `;
    overlay.innerHTML = `
      <div class="spinner" style="width: 60px; height: 60px; border: 4px solid #475569; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
      <h2 style="margin-top: 2rem;">Loading Security Dashboard...</h2>
      <p style="color: #cbd5e1; margin-top: 0.5rem;">Analyzing 375 energy sector projects</p>
    `;
    document.body.appendChild(overlay);
  } else if (!show && overlay) {
    overlay.remove();
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    showLoading(true);
    init();
  });
} else {
  showLoading(true);
  init();
}

