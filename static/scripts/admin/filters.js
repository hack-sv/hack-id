// Filter and Sort Functionality

// Sort table
function sortTable(column, direction) {
    const tbody = document.querySelector('#usersTable tbody');
    const rows = Array.from(tbody.querySelectorAll('.user-row'));
    
    // Update sort button states
    document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    rows.sort((a, b) => {
        const aVal = getCellValue(a, column);
        const bVal = getCellValue(b, column);
        
        if (column === 'dob' || column === 'id') {
            const aNum = column === 'id' ? parseInt(aVal) || 0 : new Date(aVal === 'N/A' ? '1900-01-01' : aVal);
            const bNum = column === 'id' ? parseInt(bVal) || 0 : new Date(bVal === 'N/A' ? '1900-01-01' : bVal);
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        const comparison = aVal.localeCompare(bVal);
        return direction === 'asc' ? comparison : -comparison;
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// Initialize filters
function initializeFilters() {
    // Pronouns
    const pronounsSet = new Set();
    allRows.forEach(row => {
        const pronouns = row.dataset.pronouns;
        if (pronouns && pronouns !== 'N/A' && pronouns.trim()) {
            pronounsSet.add(pronouns);
        }
    });
    
    const pronounsContainer = document.getElementById('pronouns-checkboxes');
    pronounsSet.forEach(pronoun => {
        const checkbox = createFilterCheckbox(pronoun, 'pronouns');
        pronounsContainer.appendChild(checkbox);
    });
    
    // Events
    const eventsContainer = document.getElementById('events-checkboxes');
    Object.keys(eventsData).forEach(eventKey => {
        const checkbox = createFilterCheckbox(eventsData[eventKey].name, 'events');
        eventsContainer.appendChild(checkbox);
    });
}

// Create filter checkbox
function createFilterCheckbox(value, filterType) {
    const div = document.createElement('div');
    div.className = 'filter-checkbox';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = value;
    checkbox.onchange = () => applyCheckboxFilter(filterType);
    
    const label = document.createElement('label');
    label.textContent = value;
    
    div.appendChild(checkbox);
    div.appendChild(label);
    
    return div;
}

// Apply checkbox filter
function applyCheckboxFilter(filterType) {
    const container = document.getElementById(`${filterType}-checkboxes`);
    const checkedValues = Array.from(container.querySelectorAll('input:checked')).map(cb => cb.value);
    
    if (checkedValues.length === 0) {
        delete columnFilters[filterType + '_checkbox'];
    } else {
        columnFilters[filterType + '_checkbox'] = checkedValues;
    }
    
    let visibleCount = 0;
    allRows.forEach(row => {
        let show = true;
        
        if (checkedValues.length > 0) {
            if (filterType === 'pronouns') {
                show = checkedValues.includes(row.dataset.pronouns);
            } else if (filterType === 'events') {
                const userEvents = row.dataset.events.split(',');
                show = checkedValues.some(event => userEvents.includes(event.toLowerCase()));
            }
        }
        
        row.style.display = show ? '' : 'none';
        if (show) visibleCount++;
    });
    
    updateCount(visibleCount);
}
