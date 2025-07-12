// Cancer Types List - Client-side pagination and filtering
let allRows = [];
let filteredRows = [];
let currentPage = 1;
let itemsPerPage = 10;
let sortColumn = null;
let sortDirection = 'asc';

document.addEventListener('DOMContentLoaded', function() {
    // Initialize data
    allRows = Array.from(document.querySelectorAll('.cancer-type-row'));
    
    // Group rows by parent-child relationship
    allRows = organizeByHierarchy(allRows);
    filteredRows = [...allRows];
    
    // Set up event listeners
    document.getElementById('search').addEventListener('input', handleSearch);
    document.getElementById('itemsPerPage').addEventListener('change', handleItemsPerPageChange);
    
    // Initial display
    updateDisplay();
});

function organizeByHierarchy(rows) {
    const organized = [];
    const rowsById = {};
    
    // First, create a map of rows by their ID (extracted from edit link)
    rows.forEach(row => {
        const editLink = row.querySelector('a[href*="/edit"]');
        if (editLink) {
            const match = editLink.href.match(/cancer-types\/(\d+)\/edit/);
            if (match) {
                rowsById[match[1]] = row;
            }
        }
    });
    
    // Separate parents and children
    const parents = [];
    const childrenByParent = {};
    
    rows.forEach(row => {
        const parentId = row.getAttribute('data-parent');
        if (parentId === '0' || parentId === null) {
            parents.push(row);
        } else {
            if (!childrenByParent[parentId]) {
                childrenByParent[parentId] = [];
            }
            childrenByParent[parentId].push(row);
        }
    });
    
    // Sort parents alphabetically
    parents.sort((a, b) => {
        const nameA = a.getAttribute('data-name');
        const nameB = b.getAttribute('data-name');
        return nameA.localeCompare(nameB);
    });
    
    // Build organized list with parents followed by their children
    parents.forEach(parent => {
        organized.push(parent);
        
        // Find the parent's ID
        const editLink = parent.querySelector('a[href*="/edit"]');
        if (editLink) {
            const match = editLink.href.match(/cancer-types\/(\d+)\/edit/);
            if (match) {
                const parentId = match[1];
                const children = childrenByParent[parentId] || [];
                
                // Sort children alphabetically
                children.sort((a, b) => {
                    const nameA = a.getAttribute('data-name');
                    const nameB = b.getAttribute('data-name');
                    return nameA.localeCompare(nameB);
                });
                
                organized.push(...children);
            }
        }
    });
    
    return organized;
}

function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    
    if (searchTerm === '') {
        filteredRows = [...allRows];
    } else {
        filteredRows = allRows.filter(row => {
            const name = row.getAttribute('data-name');
            const description = row.getAttribute('data-description');
            return name.includes(searchTerm) || description.includes(searchTerm);
        });
    }
    
    currentPage = 1;
    updateDisplay();
}

function handleItemsPerPageChange(e) {
    itemsPerPage = parseInt(e.target.value);
    currentPage = 1;
    updateDisplay();
}

function sortTable(column) {
    // Update sort direction
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    
    // Update sort icons
    document.querySelectorAll('.sort-icon').forEach(icon => {
        icon.classList.remove('sort-asc', 'sort-desc');
    });
    const currentIcon = document.querySelector(`.sort-icon[data-column="${column}"]`);
    currentIcon.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
    
    // Sort rows
    filteredRows.sort((a, b) => {
        let valueA, valueB;
        
        if (column === 'name') {
            valueA = a.getAttribute('data-name');
            valueB = b.getAttribute('data-name');
        } else if (column === 'description') {
            valueA = a.getAttribute('data-description');
            valueB = b.getAttribute('data-description');
        }
        
        if (sortDirection === 'asc') {
            return valueA.localeCompare(valueB);
        } else {
            return valueB.localeCompare(valueA);
        }
    });
    
    updateDisplay();
}

function updateDisplay() {
    const tbody = document.getElementById('cancer-types-tbody');
    const emptyRow = document.getElementById('empty-row');
    
    // Clear tbody
    tbody.innerHTML = '';
    
    if (filteredRows.length === 0) {
        if (emptyRow) {
            tbody.appendChild(emptyRow);
        }
        document.getElementById('pagination-container').style.display = 'none';
        updateShowingInfo(0, 0, 0);
        return;
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredRows.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredRows.length);
    
    // Display current page rows
    for (let i = startIndex; i < endIndex; i++) {
        tbody.appendChild(filteredRows[i].cloneNode(true));
    }
    
    // Update pagination controls
    updatePaginationControls(totalPages);
    updateShowingInfo(startIndex + 1, endIndex, filteredRows.length);
    
    // Show/hide pagination container
    document.getElementById('pagination-container').style.display = totalPages > 1 ? 'block' : 'none';
}

function updatePaginationControls(totalPages) {
    // Update prev/next buttons
    document.getElementById('prev-btn').disabled = currentPage === 1;
    document.getElementById('next-btn').disabled = currentPage === totalPages;
    
    // Update page numbers
    const pageNumbersContainer = document.getElementById('page-numbers');
    pageNumbersContainer.innerHTML = '';
    
    // Determine which page numbers to show
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // Add first page and ellipsis if needed
    if (startPage > 1) {
        addPageButton(1);
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'px-2 text-gray-500';
            ellipsis.textContent = '...';
            pageNumbersContainer.appendChild(ellipsis);
        }
    }
    
    // Add page buttons
    for (let i = startPage; i <= endPage; i++) {
        addPageButton(i);
    }
    
    // Add last page and ellipsis if needed
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'px-2 text-gray-500';
            ellipsis.textContent = '...';
            pageNumbersContainer.appendChild(ellipsis);
        }
        addPageButton(totalPages);
    }
}

function addPageButton(pageNum) {
    const pageNumbersContainer = document.getElementById('page-numbers');
    const button = document.createElement('button');
    button.className = 'page-btn';
    if (pageNum === currentPage) {
        button.classList.add('active');
    }
    button.textContent = pageNum;
    button.onclick = () => goToPage(pageNum);
    pageNumbersContainer.appendChild(button);
}

function updateShowingInfo(start, end, total) {
    document.getElementById('showing-start').textContent = start;
    document.getElementById('showing-end').textContent = end;
    document.getElementById('total-items').textContent = total;
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        updateDisplay();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredRows.length / itemsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        updateDisplay();
    }
}

function goToPage(page) {
    currentPage = page;
    updateDisplay();
}

// Make sortTable function available globally for onclick handlers
window.sortTable = sortTable;
window.previousPage = previousPage;
window.nextPage = nextPage;