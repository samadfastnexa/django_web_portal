/**
 * Organogram Interactive Chart
 * Renders hierarchical organization structure with expand/collapse functionality
 */

(function() {
    'use strict';

    let hierarchyData = [];
    let expandedNodes = new Set();
    let searchTerm = '';

    /**
     * Initialize the organogram on page load
     */
    document.addEventListener('DOMContentLoaded', function() {
        loadHierarchyData();
        setupEventListeners();
        renderOrganogram();
    });

    /**
     * Load hierarchy data from the embedded JSON
     */
    function loadHierarchyData() {
        const dataElement = document.getElementById('hierarchy-data');
        if (dataElement) {
            try {
                hierarchyData = JSON.parse(dataElement.textContent);
                console.log('Loaded hierarchy data:', hierarchyData);
            } catch (error) {
                console.error('Error parsing hierarchy data:', error);
                hierarchyData = [];
            }
        }
    }

    /**
     * Setup event listeners for controls
     */
    function setupEventListeners() {
        // Expand all button
        const expandAllBtn = document.getElementById('expand-all');
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', function() {
                expandAll();
            });
        }

        // Collapse all button
        const collapseAllBtn = document.getElementById('collapse-all');
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', function() {
                collapseAll();
            });
        }

        // Reset view button
        const resetBtn = document.getElementById('reset-view');
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                resetView();
            });
        }

        // Search box
        const searchBox = document.getElementById('search-box');
        if (searchBox) {
            searchBox.addEventListener('input', function(e) {
                searchTerm = e.target.value.toLowerCase();
                renderOrganogram();
            });
        }
    }

    /**
     * Render the complete organogram
     */
    function renderOrganogram() {
        const container = document.getElementById('organogram-chart');
        if (!container) return;

        if (hierarchyData.length === 0) {
            container.innerHTML = '<div class="loading">No hierarchy data available</div>';
            return;
        }

        container.innerHTML = '';
        hierarchyData.forEach(node => {
            container.appendChild(renderNode(node, 0));
        });
    }

    /**
     * Render a single node and its children
     */
    function renderNode(node, level) {
        const nodeWrapper = document.createElement('div');
        nodeWrapper.className = 'org-node';
        nodeWrapper.dataset.nodeId = node.id;

        // Determine node type for styling
        let nodeType = 'node-field';
        if (level === 0) {
            nodeType = 'node-top';
        } else if (level === 1 || level === 2) {
            nodeType = 'node-middle';
        }

        // Create node card
        const nodeCard = document.createElement('div');
        nodeCard.className = `node-card ${nodeType}`;
        
        if (node.children && node.children.length > 0) {
            nodeCard.classList.add('has-children');
        }

        // Check if this node matches search
        const matches = matchesSearch(node);
        if (matches) {
            nodeCard.classList.add('highlighted');
        }

        // Node content
        nodeCard.innerHTML = `
            <div class="node-name">${escapeHtml(node.name)}</div>
            <div class="node-designation">${escapeHtml(node.designation)}</div>
            <div class="node-code">${escapeHtml(node.employee_code)}</div>
            <div class="node-details">
                ${node.email ? `<div>📧 ${escapeHtml(node.email)}</div>` : ''}
                ${node.phone ? `<div>📞 ${escapeHtml(node.phone)}</div>` : ''}
                ${node.companies && node.companies.length > 0 ? `<div>🏢 ${escapeHtml(node.companies.join(', '))}</div>` : ''}
                ${node.territories && node.territories.length > 0 ? `<div>📍 ${node.territories.length} ${node.territories.length === 1 ? 'Territory' : 'Territories'}</div>` : ''}
            </div>
        `;

        // Add expand/collapse button if has children
        if (node.children && node.children.length > 0) {
            const expandBtn = document.createElement('button');
            expandBtn.className = 'node-expand-btn';
            expandBtn.classList.add(expandedNodes.has(node.id) ? 'expanded' : 'collapsed');
            expandBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleNode(node.id);
            });
            nodeCard.appendChild(expandBtn);
        }

        nodeWrapper.appendChild(nodeCard);

        // Render children if expanded
        if (node.children && node.children.length > 0 && (expandedNodes.has(node.id) || searchTerm)) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'org-children visible';
            
            const childLevel = document.createElement('div');
            childLevel.className = 'org-level';
            
            node.children.forEach(child => {
                childLevel.appendChild(renderNode(child, level + 1));
            });
            
            childrenContainer.appendChild(childLevel);
            nodeWrapper.appendChild(childrenContainer);
        }

        return nodeWrapper;
    }

    /**
     * Check if node matches search term
     */
    function matchesSearch(node) {
        if (!searchTerm) return false;

        const searchableText = [
            node.name,
            node.designation,
            node.designation_code,
            node.employee_code,
            node.email,
            node.phone,
            ...(node.companies || []),
            ...(node.regions || []),
            ...(node.zones || []),
            ...(node.territories || [])
        ].join(' ').toLowerCase();

        return searchableText.includes(searchTerm);
    }

    /**
     * Toggle node expansion
     */
    function toggleNode(nodeId) {
        if (expandedNodes.has(nodeId)) {
            expandedNodes.delete(nodeId);
        } else {
            expandedNodes.add(nodeId);
        }
        renderOrganogram();
    }

    /**
     * Expand all nodes
     */
    function expandAll() {
        expandedNodes.clear();
        collectAllNodeIds(hierarchyData);
        renderOrganogram();
    }

    /**
     * Collapse all nodes
     */
    function collapseAll() {
        expandedNodes.clear();
        searchTerm = '';
        const searchBox = document.getElementById('search-box');
        if (searchBox) searchBox.value = '';
        renderOrganogram();
    }

    /**
     * Reset view to initial state
     */
    function resetView() {
        collapseAll();
    }

    /**
     * Collect all node IDs recursively
     */
    function collectAllNodeIds(nodes) {
        nodes.forEach(node => {
            expandedNodes.add(node.id);
            if (node.children && node.children.length > 0) {
                collectAllNodeIds(node.children);
            }
        });
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})();
