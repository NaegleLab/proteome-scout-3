// Sort tab functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sortable list
    const sortableList = document.getElementById('sortableKinaseList');
    if (sortableList) {
        window.sortableKinaseList = new Sortable(sortableList, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            handle: '.drag-handle',
            onEnd: function() {
                if (window.plotActive) {
                    window.updatePlotDynamically();
                }
            }
        });
    }

    // Handle kinase sorting radio buttons
    document.querySelectorAll('input[name="sortKinases"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const manualContainer = document.getElementById('manualKinaseOrderContainer');
            const dendrogramOption = document.getElementById('kinasesDendrogramOption');
            const dendrogramColorContainer = document.getElementById('kinasesDendrogramColorContainer');
            
            // Hide all containers initially
            manualContainer.style.display = 'none';
            dendrogramOption.style.display = 'none';
            dendrogramColorContainer.style.display = 'none';
            
            if (this.value === 'manual') {
                manualContainer.style.display = 'block';
                updateKinaseList();
            } else if (this.value === 'by_clustering') {
                dendrogramOption.style.display = 'block';
                dendrogramColorContainer.style.display = 'block';  // Show color picker when clustering is selected
            }
            
            if (window.plotActive) {
                window.updatePlotDynamically();
            }
        });
    });

    // Handle kinase search
    const searchBox = document.getElementById('kinaseSearchBox');
    if (searchBox) {
        searchBox.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const listItems = document.querySelectorAll('#sortableKinaseList li');
            
            listItems.forEach(item => {
                const kinaseName = item.textContent.toLowerCase();
                item.style.display = kinaseName.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // Function to update the sortable kinase list
    function updateKinaseList() {
        const list = document.getElementById('sortableKinaseList');
        if (!list) return;
        
        list.innerHTML = ''; // Clear existing list
        
        // Determine which kinases to show based on restrict setting
        const restrictCheckbox = document.getElementById('restrictKinases');
        const isRestricted = restrictCheckbox ? restrictCheckbox.checked : false;
        let kinasesToShow = window.availableKinases || [];

        if (isRestricted && window.plotActive) {
            // If restricted and plot is active, get kinases from current log_results
            const logResultsJson = document.getElementById('logResultsJSON')?.value;
            if (logResultsJson) {
                try {
                    const logResultsData = JSON.parse(logResultsJson);
                    const sampleNames = Object.keys(logResultsData);
                    if (sampleNames.length > 0) {
                        const firstSample = logResultsData[sampleNames[0]];
                        if (firstSample && typeof firstSample === 'object') {
                            kinasesToShow = Object.keys(firstSample);
                        }
                    }
                } catch (e) {
                    console.error('Error parsing logResultsJSON in updateKinaseList:', e);
                    kinasesToShow = [];
                }
            } else {
                kinasesToShow = [];
            }
        }
        
        kinasesToShow.forEach(kinase => {
            const li = document.createElement('li');
            li.className = 'sortable-item';
            li.innerHTML = `
                <span class="drag-handle">
                    <i class="bi bi-grip-vertical"></i>
                </span>
                <span class="kinase-name">${kinase}</span>
            `;
            list.appendChild(li);
        });
    }

    // Handle apply order button
    document.getElementById('applyKinaseOrderButton')?.addEventListener('click', function() {
        // Get the current order and store it
        const currentOrder = window.getCurrentKinaseOrder();
        
        // Store the order in the hidden input
        document.getElementById('manualKinaseOrderJSON').value = JSON.stringify(currentOrder);
        
        console.log('Applying new kinase order:', currentOrder); // Debug log
        
        // Update the plot if active
        if (window.plotActive) {
            // Ensure the manual sort radio is still selected
            const manualSortRadio = document.querySelector('input[name="sortKinases"][value="manual"]');
            if (manualSortRadio?.checked) {
                window.updatePlotDynamically({
                    sortKinases: 'manual',
                    manualKinaseOrder: currentOrder
                });
            }
        }
    });

    // Handle sample sorting radio buttons
    document.querySelectorAll('input[name="sortSamples"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const dendrogramOption = document.getElementById('samplesDendrogramOption');
            const dendrogramColorContainer = document.getElementById('samplesDendrogramColorContainer');
            
            dendrogramOption.style.display = this.value === 'by_clustering' ? 'block' : 'none';
            dendrogramColorContainer.style.display = this.value === 'by_clustering' ? 'block' : 'none';
            
            if (window.plotActive) {
                window.updatePlotDynamically();
            }
        });
    });

    // Handle dendrogram color pickers
    const kinasesDendrogramColorPicker = document.getElementById('kinases_dendrogram_color');
    if (kinasesDendrogramColorPicker) {
        ['input', 'change'].forEach(eventType => {
            kinasesDendrogramColorPicker.addEventListener(eventType, function() {
                if (window.plotActive) {
                    window.updatePlotDynamically();
                }
            });
        });
    }

    const samplesDendrogramColorPicker = document.getElementById('samples_dendrogram_color');
    if (samplesDendrogramColorPicker) {
        ['input', 'change'].forEach(eventType => {
            samplesDendrogramColorPicker.addEventListener(eventType, function() {
                if (window.plotActive) {
                    window.updatePlotDynamically();
                }
            });
        });
    }
});

// Get current manual kinase order
window.getCurrentKinaseOrder = function() {
    const list = document.getElementById('sortableKinaseList');
    if (!list) return [];
    
    // Get all visible kinase items (in case some are hidden by search)
    const visibleKinases = Array.from(list.querySelectorAll('.sortable-item'))
        .filter(item => item.style.display !== 'none')
        .map(item => item.querySelector('.kinase-name').textContent);
    
    console.log('Current kinase order:', visibleKinases); // Debug log
    return visibleKinases;
};