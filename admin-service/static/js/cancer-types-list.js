// Cancer Types List - Client-side pagination and filtering
let allRows = [];
let filteredRows = [];
let currentPage = 1;
let itemsPerPage = 10;
let sortColumn = null;
let sortDirection = 'asc';

document.addEventListener('DOMContentLoaded', function() {
    // Initialize data - get rows from both desktop and mobile views
    const desktopRows = Array.from(document.querySelectorAll('#cancer-types-tbody .cancer-type-row'));
    const mobileRows = Array.from(document.querySelectorAll('#cancer-types-mobile .cancer-type-row'));
    
    // Use desktop rows for logic, we'll sync mobile rows later
    allRows = desktopRows.length > 0 ? desktopRows : mobileRows;
    
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
    
    // Sort rows with hierarchy maintained
    if (column === 'name') {
        // Separate parents and children
        const parents = [];
        const childrenByParent = {};
        
        filteredRows.forEach(row => {
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
        
        // Sort parents
        parents.sort((a, b) => {
            const nameA = a.getAttribute('data-name');
            const nameB = b.getAttribute('data-name');
            
            if (sortDirection === 'asc') {
                return nameA.localeCompare(nameB);
            } else {
                return nameB.localeCompare(nameA);
            }
        });
        
        // Rebuild filteredRows with sorted hierarchy
        filteredRows = [];
        parents.forEach(parent => {
            filteredRows.push(parent);
            
            // Find the parent's ID and add its children
            const editLink = parent.querySelector('a[href*="/edit"]');
            if (editLink) {
                const match = editLink.href.match(/cancer-types\/(\d+)\/edit/);
                if (match) {
                    const parentId = match[1];
                    const children = childrenByParent[parentId] || [];
                    
                    // Sort children
                    children.sort((a, b) => {
                        const nameA = a.getAttribute('data-name');
                        const nameB = b.getAttribute('data-name');
                        
                        if (sortDirection === 'asc') {
                            return nameA.localeCompare(nameB);
                        } else {
                            return nameB.localeCompare(nameA);
                        }
                    });
                    
                    filteredRows.push(...children);
                }
            }
        });
    }
    
    updateDisplay();
}

function updateDisplay() {
    const tbody = document.getElementById('cancer-types-tbody');
    const mobileContainer = document.getElementById('cancer-types-mobile');
    const emptyRow = document.getElementById('empty-row');
    
    // Clear both desktop and mobile containers
    if (tbody) tbody.innerHTML = '';
    if (mobileContainer) mobileContainer.innerHTML = '';
    
    if (filteredRows.length === 0) {
        // Show empty message
        const emptyMessage = '<tr id="empty-row"><td colspan="4" class="px-6 py-4 text-center text-gray-500">No cancer types found. <a href="/admin/cancer-types/create" class="text-blue-600 hover:text-blue-900">Add the first one</a>.</td></tr>';
        const emptyMobileMessage = '<div class="p-4 text-center text-gray-500">No cancer types found. <a href="/admin/cancer-types/create" class="text-blue-600 hover:text-blue-900">Add the first one</a>.</div>';
        
        if (tbody) tbody.innerHTML = emptyMessage;
        if (mobileContainer) mobileContainer.innerHTML = emptyMobileMessage;
        
        document.getElementById('pagination-container').style.display = 'none';
        updateShowingInfo(0, 0, 0);
        return;
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredRows.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredRows.length);
    
    // Display current page rows for both desktop and mobile
    for (let i = startIndex; i < endIndex; i++) {
        if (tbody) {
            tbody.appendChild(filteredRows[i].cloneNode(true));
        }
        if (mobileContainer) {
            // Clone the row and convert it to mobile format
            const desktopRow = filteredRows[i];
            const mobileRow = createMobileRow(desktopRow);
            if (mobileRow) {
                mobileContainer.appendChild(mobileRow);
            }
        }
    }
    
    // Update pagination controls
    updatePaginationControls(totalPages);
    updateShowingInfo(startIndex + 1, endIndex, filteredRows.length);
    
    // Show/hide pagination container
    document.getElementById('pagination-container').style.display = totalPages > 1 ? 'block' : 'none';
}

function createMobileRow(desktopRow) {
    // Extract data from desktop row
    const name = desktopRow.getAttribute('data-name');
    const description = desktopRow.getAttribute('data-description');
    const parent = desktopRow.getAttribute('data-parent');
    
    const nameCell = desktopRow.querySelector('td:first-child .text-sm');
    const descriptionCell = desktopRow.querySelector('td:nth-child(2) .text-sm');
    const subtypesCell = desktopRow.querySelector('td:nth-child(3) .text-sm');
    const editLink = desktopRow.querySelector('a[href*="/edit"]');
    const deleteForm = desktopRow.querySelector('form[action*="/delete"]');
    
    if (!nameCell || !editLink || !deleteForm) return null;
    
    // Extract ID from edit link
    const idMatch = editLink.href.match(/cancer-types\/(\d+)\/edit/);
    if (!idMatch) return null;
    const id = idMatch[1];
    
    // Extract actual text content
    const cancerTypeName = nameCell.textContent.trim().replace('↳', '').trim();
    const cancerDescription = descriptionCell ? descriptionCell.textContent.trim() : '';
    const subtypesText = subtypesCell ? subtypesCell.textContent.trim() : '0 subtypes';
    
    // Create mobile row HTML
    const mobileDiv = document.createElement('div');
    mobileDiv.className = 'p-4 hover:bg-gray-50 cancer-type-row';
    mobileDiv.setAttribute('data-name', name);
    mobileDiv.setAttribute('data-description', description);
    mobileDiv.setAttribute('data-parent', parent);
    
    mobileDiv.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div class="flex-1">
                <h3 class="text-sm font-medium text-gray-900">
                    ${parent !== '0' && parent !== null ? '<span class="text-gray-600">↳</span> ' : ''}${cancerTypeName}
                </h3>
                <p class="text-sm text-gray-600 mt-1">${cancerDescription.length > 100 ? cancerDescription.substring(0, 100) + '...' : cancerDescription}</p>
                <p class="text-xs text-gray-500 mt-1">${subtypesText}</p>
            </div>
        </div>
        <div class="flex space-x-3 text-sm">
            <a href="/admin/cancer-types/${id}/edit" class="text-blue-600 hover:text-blue-900">Edit</a>
            <form method="POST" action="/admin/cancer-types/${id}/delete" class="inline" onsubmit="return confirm('Are you sure you want to delete this cancer type?');">
                <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
                <button type="submit" class="text-red-600 hover:text-red-900">Delete</button>
            </form>
        </div>
    `;
    
    return mobileDiv;
}

function getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
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