const mobileBreakpoint = 768; // Bootstrap's breakpoint for medium screens
// const mobileBreakpoint = 576; // Bootstrap's breakpoint for small screens

document.addEventListener('DOMContentLoaded', function() {
    
    
    // Set focus on the quick input field when page loads
    const quickInput = document.getElementById('quick-input');
    const classificationForm = document.getElementById('classification-form');
    
    // Only focus if not on a mobile device
    not_mobile = window.innerWidth > mobileBreakpoint;
    // not_mobile = !/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    if (not_mobile) {
        quickInput.focus();
    }
    
    // Process the quick input field
    quickInput.addEventListener('input', function(e) {
        const inputText = e.target.value.toLowerCase();
        
        // Clear the input field of non-relevant characters
        let cleanedInput = '';
        for (const char of inputText) {
            if (['-', '0', '1', '2', 'r', 'a', 'c', 'm'].includes(char)) {
                cleanedInput += char;
            }
        }
        
        if (cleanedInput !== inputText) {
            e.target.value = cleanedInput;
        }
        
        // Parse the input string into LSB class and morphology
        parseInput(cleanedInput);
        
        // Process contrast toggle
        if (cleanedInput.includes('c')) {
            document.getElementById('contrast-btn').click();
            // Remove the 'c' after processing
            e.target.value = cleanedInput.replace('c', '');
        }
    });
    
    function parseInput(input) {
        // Reset all checkboxes
        document.querySelectorAll('.lsb-radio, .morph-radio').forEach(radio => {
            radio.checked = false;
        });
        document.getElementById('valid_redshift').checked = false;
        document.getElementById('awesome_flag').checked = false;
        
        // Extract LSB class (first digit/character)
        let lsbClass = null;
        let morphClass = null;
        
        // First pass: identify LSB class (first relevant character)
        for (let i = 0; i < input.length; i++) {
            const char = input[i];
            if (['-', '0', '1'].includes(char) && lsbClass === null) {
                lsbClass = char;
                // If it's a dash and the next character is a digit, this is "-1"
                if (char === '-' && i+1 < input.length && input[i+1] === '1') {
                    lsbClass = '-1';
                    i++; // Skip the next character as we've processed it
                }
                continue;
            }
        }
        
        // Second pass: identify morphology (next relevant character after LSB class)
        let foundLsb = false;
        for (let i = 0; i < input.length; i++) {
            const char = input[i];
            
            // Skip until we've passed the LSB class characters
            if (!foundLsb) {
                if (char === '-' && i+1 < input.length && input[i+1] === '1') {
                    foundLsb = true;
                    i++; // Skip the next character
                } else if (['-', '0', '1'].includes(char)) {
                    foundLsb = true;
                }
                continue;
            }
            
            // Now look for the morphology class
            if (['-', '0', '1', '2'].includes(char) && morphClass === null) {
                morphClass = char;
                // If it's a dash and the next character is a digit, this is "-1"
                if (char === '-' && i+1 < input.length && input[i+1] === '1') {
                    morphClass = '-1';
                    i++; // Skip the next character
                }
                continue;
            }
        }
        
        // Third pass: check for flags
        const hasRedshift = input.includes('r');
        const hasAwesome = input.includes('a');
        
        // Apply the LSB class
        if (lsbClass === '-' || lsbClass === '-1') {
            document.getElementById('lsb-failed').checked = true;
        } else if (lsbClass === '0') {
            document.getElementById('lsb-no').checked = true;
        } else if (lsbClass === '1') {
            document.getElementById('lsb-yes').checked = true;
        }
        
        // Apply the morphology
        if (morphClass === '-' || morphClass === '-1') {
            document.getElementById('morph-featureless').checked = true;
        } else if (morphClass === '0') {
            document.getElementById('morph-notsure').checked = true;
        } else if (morphClass === '1') {
            document.getElementById('morph-ltg').checked = true;
        } else if (morphClass === '2') {
            document.getElementById('morph-etg').checked = true;
        }
        
        // Apply flags
        document.getElementById('valid_redshift').checked = hasRedshift;
        document.getElementById('awesome_flag').checked = hasAwesome;
    }
    
    // Handle form submission on Enter key and validate form
    quickInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            validateAndSubmitForm();
        }
    });

    // Form validation function
    function validateAndSubmitForm() {
        const lsbSelected = document.querySelector('input[name="lsb_class"]:checked');
        const morphSelected = document.querySelector('input[name="morphology"]:checked');
        const lsbCard = document.getElementById('lsb-classification-card');
        const morphCard = document.getElementById('morphology-card');
        
        // Reset any previous highlights
        lsbCard.classList.remove('border-danger', 'bg-danger-subtle');
        morphCard.classList.remove('border-danger', 'bg-danger-subtle');
        
        let isValid = true;
        
        if (!lsbSelected) {
            lsbCard.classList.add('border-danger', 'bg-danger-subtle');
            isValid = false;
        }
        
        if (lsbSelected && lsbSelected.value !== "-1" && !morphSelected) {
            morphCard.classList.add('border-danger', 'bg-danger-subtle');
            isValid = false;
        }
        
        if (isValid) {
            document.getElementById('classification-form').submit();
        }
    }

    // Prevent default form submission and use our validation
    classificationForm.addEventListener('submit', function(e) {
        e.preventDefault();
        validateAndSubmitForm();
    });
    
    // Update quick input field when radio buttons are clicked
    document.querySelectorAll('.lsb-radio, .morph-radio').forEach(radio => {
        radio.addEventListener('change', updateQuickInputFromForm);
    });
    
    document.getElementById('valid_redshift').addEventListener('change', function() {
        updateQuickInputFromForm();
    });
    
    document.getElementById('awesome_flag').addEventListener('change', function() {
        updateQuickInputFromForm();
    });
    
    function updateQuickInputFromForm() {
        let inputValue = '';
        
        // Get LSB class
        const lsbSelected = document.querySelector('input[name="lsb_class"]:checked');
        if (lsbSelected) {
            if (lsbSelected.value === "-1") {
                inputValue += '-';
            } else {
                inputValue += lsbSelected.value;
            }
        }
        
        // Get morphology
        const morphSelected = document.querySelector('input[name="morphology"]:checked');
        if (morphSelected) {
            if (morphSelected.value === "-1") {
                inputValue += '-';
            } else {
                inputValue += morphSelected.value;
            }
        }
        
        // Add flags
        if (document.getElementById('valid_redshift').checked) {
            inputValue += 'r';
        }
        
        if (document.getElementById('awesome_flag').checked) {
            inputValue += 'a';
        }
        
        // Update the quick input field
        document.getElementById('quick-input').value = inputValue;
    }

    updateQuickInputFromForm();
    
    // Contrast button: cycle through server-generated PNGs and update vmax display
    const vmaxPercentiles    = [99.0, 99.5, 99.9, 99.95, 80.0, 90.0,];
    const vmaxRawPercentiles = [99.7, 99.7, 99.9, 99.95, 90.0, 99.0,];
    let contrastIndex = 0;
    const galaxyId = document.querySelector('input[name="galaxy_id"]').value;

    document.getElementById('contrast-btn').addEventListener('click', () => {
    // advance index
    contrastIndex = (contrastIndex + 1) % vmaxPercentiles.length;

    document.querySelectorAll('.galaxy-image[data-base-name]').forEach(img => {
        const base = img.dataset.baseName;
        const v  = vmaxPercentiles[contrastIndex];
        const vr = vmaxRawPercentiles[contrastIndex];
        // update image src
        img.src = `/static/galaxy_images/${galaxyId}/${getImageFilename(base, v, vr)}`;
        // update vmax-info text
        const small = document.querySelector(`.vmax-info[data-target-image="${base}"]`);
        if (small) {
            // Decide on 1 or 2 decimal places: one place if decimal*10 is (nearly) an integer, else two places
            const decimal = Math.abs(v % 1);
            const isOneDecimal = Math.abs(decimal * 10 - Math.round(decimal * 10)) < 0.001;
            const needed_decimal_places = isOneDecimal ? 1 : 2;

            if (['masked_r_band','galfit_model','residual'].includes(base)) {
                small.textContent = `(${v.toFixed(needed_decimal_places)})`;
            } else if (base === 'raw_r_band') {
                // for raw_r_band, check vr's decimals similarly
                const decRaw = Math.abs(vr % 1);
                const isOneDecRaw = Math.abs(decRaw * 10 - Math.round(decRaw * 10)) < 0.001;
                const placesRaw = isOneDecRaw ? 1 : 2;
                small.textContent = `(${vr.toFixed(placesRaw)})`;
            } else {
                small.textContent = '';
            }
        }
    });
    });

    function slugify(value) {
        // ensure one decimal place, replace '.'→'p', '-'→'m'
        // Format to 1 decimal place normally, 2 places if needed for precision
        const formatted = Number(value).toFixed(
            Math.abs(value % 1) < 0.05 ? 1 : 2
        );
        return formatted.replace(/-/g, 'm').replace(/\./g, 'p');
    }

    function getImageFilename(baseName, vmax, vmaxRaw) {
    if (['masked_r_band','galfit_model','residual'].includes(baseName)) {
        return `${baseName}_vmax${slugify(vmax)}.png`;
    }
    if (baseName === 'raw_r_band') {
        return `${baseName}_vmax${slugify(vmaxRaw)}.png`;
    }
    return `${baseName}.png`;
    }

    const mainContentContainer = document.getElementById('main-content-container');
    const classificationFormRow = document.getElementById('classification-form-row');
    const formContainer = document.getElementById('classification-form-container');
    const formContainerAfterImages = document.getElementById('classification-form-container-after-images');
 
    // const imagesContainer = document.getElementById('galaxy-images-container');

    const textDiv       = document.getElementById('text-inputs-container');
    const nonImpDiv     = document.getElementById('non-important-click-inputs-container');
    // const importantDiv  = document.getElementById('important-click-inputs-container');
    const galaxySectionHeaderContainer = document.getElementById('galaxy-classification-header-container');

    
    let prevIsMobile = null;

    function reorder() {
        const isMobile = window.innerWidth < mobileBreakpoint;
        // only proceed if breakpoint really changed
        if (isMobile === prevIsMobile) return;
        prevIsMobile = isMobile;

        // preserve focus
        const activeEl = document.activeElement;

        if (isMobile) {
            formContainerAfterImages.appendChild(textDiv);
            formContainerAfterImages.appendChild(nonImpDiv);
            formContainerAfterImages.appendChild(galaxySectionHeaderContainer);
        } else {
            formContainer.appendChild(textDiv);
            formContainer.appendChild(nonImpDiv);
            mainContentContainer.insertBefore(galaxySectionHeaderContainer, classificationForm);
        }

        // restore focus if needed
        if (activeEl && typeof activeEl.focus === 'function') {
            activeEl.focus();
        }
    }

    window.addEventListener('resize', reorder);
    reorder();



    // Function to handle responsive button layout
    function handleButtonLayout() {
        const buttonContainer = document.getElementById('submit-buttons-container');
        const buttons = buttonContainer.querySelectorAll('.btn');
        
        if (window.innerWidth < 1280 && window.innerWidth >= 768) {
            // Two rows layout for medium screens
            buttonContainer.classList.remove('btn-group', 'w-100', 'mb-4');
            buttonContainer.classList.add('compact-button-grid');
            
            // Wrap each pair of buttons in a div
            for (let i = 0; i < buttons.length; i += 2) {
                const btn1 = buttons[i];
                const btn2 = buttons[i+1];
                
                if (!btn1.parentElement.classList.contains('col-6')) {
                    const rowDiv = document.createElement('div');
                    rowDiv.className = 'compact-row';
                    
                    const col1 = document.createElement('div');
                    col1.className = 'col-6 px-1';
                    const col2 = document.createElement('div');
                    col2.className = 'col-6 px-1';
                    
                    buttonContainer.appendChild(rowDiv);
                    rowDiv.appendChild(col1);
                    rowDiv.appendChild(col2);
                    
                    col1.appendChild(btn1);
                    if (btn2) col2.appendChild(btn2);
                    
                    btn1.classList.add('w-100');
                    if (btn2) btn2.classList.add('w-100');
                    btn1.classList.remove('btn-group-item');
                    if (btn2) btn2.classList.remove('btn-group-item');
                }
            }
        } else {
            // One row layout for other screen sizes
            buttonContainer.classList.add('btn-group', 'w-100', 'mb-4');
            buttonContainer.classList.remove('compact-button-grid');
            
            buttons.forEach(btn => {
                if (btn.parentElement.classList.contains('col-6')) {
                    buttonContainer.appendChild(btn);
                }
                btn.classList.remove('w-100');
            });
            
            // Remove any row divs created for the two-row layout
            const rows = buttonContainer.querySelectorAll('.compact-row');
            rows.forEach(row => row.remove());
        }
    }
    
    // Run initially and on window resize
    window.addEventListener('load', handleButtonLayout);
    window.addEventListener('resize', handleButtonLayout);

    // Image card reordering in mobile view
    // Store the original order of image cards for restoration when switching back to desktop
    let originalImageCards = [];
    let originalFirstRowCount = 0;
    
    function captureOriginalOrder() {
        const imagesContainer = document.getElementById('galaxy-images-container');
        const rows = imagesContainer.querySelectorAll('.row');
        
        // Store original first row count
        if (rows[0]) {
            originalFirstRowCount = rows[0].querySelectorAll('.col-md-4').length;
        }
        
        // Capture all image cards in their original order
        originalImageCards = Array.from(imagesContainer.querySelectorAll('.col-md-4'));
    }
    
    function reorderGalaxyImages() {
        const imagesContainer = document.getElementById('galaxy-images-container');
        const rows = imagesContainer.querySelectorAll('.row');
        const isMobile = window.innerWidth < mobileBreakpoint;
        
        // Only proceed if we have rows and images to work with
        if (!rows || rows.length < 2) return;
        
        if (isMobile) {
            // Define the desired order for base-name attributes
            const desiredOrder = ['aplpy', 'lupton', 'masked_r_band', 'residual', 'raw_r_band', 'galfit_model'];
            
            // Get all image cards
            const imageCards = Array.from(imagesContainer.querySelectorAll('.col-md-4'));
            
            // Sort the cards based on the desired order
            imageCards.sort((a, b) => {
                const aBaseName = a.querySelector('.galaxy-image').dataset.baseName;
                const bBaseName = b.querySelector('.galaxy-image').dataset.baseName;
                
                return desiredOrder.indexOf(aBaseName) - desiredOrder.indexOf(bBaseName);
            });
            
            // Clear the rows
            rows.forEach(row => {
                row.innerHTML = '';
            });
            
            // Distribute the sorted cards
            imageCards.forEach((card, index) => {
                // First 3 cards go to first row, rest to second row
                const targetRow = index < 3 ? rows[0] : rows[1];
                targetRow.appendChild(card);
            });
        } else {
            // Restore original order on desktop view
            if (originalImageCards.length > 0) {
                // Clear the rows
                rows.forEach(row => {
                    row.innerHTML = '';
                });
                
                // Redistribute cards according to original order
                originalImageCards.forEach((card, index) => {
                    // Use the originally saved row distribution
                    const targetRow = index < originalFirstRowCount ? rows[0] : rows[1];
                    targetRow.appendChild(card.cloneNode(true));
                });
            }
        }
    }
    
    // Capture original order once when page loads
    window.addEventListener('DOMContentLoaded', captureOriginalOrder);
    
    // Run the reordering function on page load and window resize
    window.addEventListener('load', reorderGalaxyImages);
    window.addEventListener('resize', reorderGalaxyImages);

});
