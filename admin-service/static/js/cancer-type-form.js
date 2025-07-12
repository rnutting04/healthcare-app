// Cancer Type Form - Dynamic form handling

function toggleFormFields() {
    const selectedType = document.querySelector('input[name="entry_type"]:checked').value;
    const typeFields = document.getElementById('type-fields');
    const subtypeFields = document.getElementById('subtype-fields');
    
    // Update selected styling
    document.querySelectorAll('input[name="entry_type"]').forEach(radio => {
        const label = radio.closest('label');
        if (radio.checked) {
            label.classList.add('radio-selected');
        } else {
            label.classList.remove('radio-selected');
        }
    });
    
    if (selectedType === 'type') {
        typeFields.style.display = 'block';
        subtypeFields.style.display = 'none';
        
        // Update required attributes
        document.getElementById('cancer_type').required = true;
        document.getElementById('parent').required = false;
        document.getElementById('subtype_cancer_type').required = false;
        document.getElementById('subtype_description').required = false;
        
        // Show/hide checkmarks
        document.querySelector('.type-radio-selected').style.display = 'block';
        document.querySelector('.subtype-radio-selected').style.display = 'none';
    } else {
        typeFields.style.display = 'none';
        subtypeFields.style.display = 'block';
        
        // Update required attributes
        document.getElementById('cancer_type').required = false;
        document.getElementById('parent').required = true;
        document.getElementById('subtype_cancer_type').required = true;
        document.getElementById('subtype_description').required = false;
        
        // Show/hide checkmarks
        document.querySelector('.type-radio-selected').style.display = 'none';
        document.querySelector('.subtype-radio-selected').style.display = 'block';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Get action from template context
    const formElement = document.querySelector('form');
    const isEditMode = formElement && formElement.dataset.action === 'edit';
    
    if (!isEditMode) {
        toggleFormFields();
        
        // Add event listeners to all radio buttons
        document.querySelectorAll('input[name="entry_type"]').forEach(radio => {
            radio.addEventListener('change', toggleFormFields);
        });
    } else {
        // In edit mode, show the type fields by default
        const typeFields = document.getElementById('type-fields');
        const subtypeFields = document.getElementById('subtype-fields');
        if (typeFields) typeFields.style.display = 'block';
        if (subtypeFields) subtypeFields.style.display = 'none';
    }
});