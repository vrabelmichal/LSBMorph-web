document.addEventListener('DOMContentLoaded', function() {
    // Set focus on the quick input field when page loads
    const quickInput = document.getElementById('quick-input');
    
    // Only focus if not on a mobile device
    not_mobile = window.innerWidth > 576;
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
    
    // Handle form submission on Enter key
    quickInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            
            // Validate form
            const lsbSelected = document.querySelector('input[name="lsb_class"]:checked');
            const morphSelected = document.querySelector('input[name="morphology"]:checked');
            
            if (!lsbSelected) {
                alert('Please select an LSB classification.');
                return;
            }
            
            if (lsbSelected.value !== "-1" && !morphSelected) {
                alert('Please select a morphology type.');
                return;
            }
            
            // Submit the form
            document.getElementById('classification-form').submit();
        }
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
    
    // // Contrast adjustment
    // document.getElementById('contrast-btn').addEventListener('click', function() {
    //     const images = document.querySelectorAll('.galaxy-image');
    //     images.forEach(img => {
    //         // Cycle through contrast levels by adding/removing classes
    //         if (img.classList.contains('contrast-high')) {
    //             img.classList.remove('contrast-high');
    //             img.classList.add('contrast-extreme');
    //         } else if (img.classList.contains('contrast-extreme')) {
    //             img.classList.remove('contrast-extreme');
    //             // Back to normal
    //         } else {
    //             img.classList.add('contrast-high');
    //         }
    //     });
    // });

    // Contrast button: cycle through server-generated PNGs and update vmax display
    const vmaxPercentiles    = [99.0, 90.0, 99.5, 99.9, 80.0];
    const vmaxRawPercentiles = [99.7, 99.0, 99.5, 99.9, 80.0];
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
        if (['masked_r_band','galfit_model','residual'].includes(base)) {
            small.textContent = `(${v.toFixed(1)})`;
        } else if (base === 'raw_r_band') {
            small.textContent = `(${vr.toFixed(1)})`;
        } else {
            small.textContent = '';
        }
        }
    });
    });

    function slugify(value) {
    // ensure one decimal place, replace '.'→'p', '-'→'m'
    return Number(value).toFixed(1).replace(/-/g, 'm').replace(/\./g, 'p');
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
    const classificationForm = document.getElementById('classification-form');
 
    // const imagesContainer = document.getElementById('galaxy-images-container');

    const textDiv       = document.getElementById('text-inputs-container');
    const nonImpDiv     = document.getElementById('non-important-click-inputs-container');
    // const importantDiv  = document.getElementById('important-click-inputs-container');
    const galaxySectionHeaderContainer = document.getElementById('galaxy-classification-header-container');

    function reorder() {
        // Preserve focus/selection if user is typing
        const hadFocus = document.activeElement === quickInput;
        let start, end;
        if (hadFocus) {
            start = quickInput.selectionStart;
            end   = quickInput.selectionEnd;
        }

        if (window.innerWidth < 576) {
            formContainerAfterImages.appendChild(textDiv);
            formContainerAfterImages.appendChild(nonImpDiv);
            formContainerAfterImages.appendChild(galaxySectionHeaderContainer);

            // // On phone: only the important-clicks stay in the form
            // if (textDiv.parentNode !== imagesContainer)       imagesContainer.appendChild(textDiv);
            // if (nonImpDiv.parentNode !== imagesContainer)     imagesContainer.appendChild(nonImpDiv);
        } else {
            // // On desktop: move them back before the important-clicks
            // if (textDiv.parentNode !== form)   form.insertBefore(textDiv, importantDiv);
            // if (nonImpDiv.parentNode !== form) form.insertBefore(nonImpDiv, importantDiv);
            
            formContainer.appendChild(textDiv);
            formContainer.appendChild(nonImpDiv);
            mainContentContainer.insertBefore(galaxySectionHeaderContainer, classificationForm);

        }

        // Restore focus/selection
        if (hadFocus) {
            quickInput.focus();
            quickInput.setSelectionRange(start, end);
        }
    }

    window.addEventListener('resize', reorder);
    reorder();

    // const quickCard   = document.getElementById('quick-input')
    //                         .closest('.card.mb-3');
    // const commentCard = document.getElementById('comments')
    //                         .closest('.form-group.mb-3');


    // const quickCard   = document.getElementById('quick-input-card');
    // const commentCard = document.getElementById('comments-container');
    // const awsomeFlagContainer = document.getElementById('awesome-flag-container');
    // const validRedshiftContainer = document.getElementById('valid-redshift-container');

    // // Columns
    // const formCol   = document.getElementById('classification-form-container');
    // const imagesCol = document.getElementById('galaxy-images-container');

    // function reorder() {
    //     if (window.innerWidth < 576) {
    //         // On phones: append under images
    //         if (quickCard.parentNode !== imagesCol)   imagesCol.appendChild(quickCard);
    //         if (commentCard.parentNode !== imagesCol) imagesCol.appendChild(commentCard);
    //     } else {
    //         // On larger: move back into form
    //         if (quickCard.parentNode !== formCol && quickCard != formCol.firstChild)   formCol.insertBefore(quickCard, formCol.firstChild);
    //         if (commentCard.parentNode !== formCol) {
    //             // insert comment just before the flags section
    //             const flagsSection = formCol.querySelector('#awesome_flag')
    //                                         .closest('.form-check').parentNode;
    //             formCol.insertBefore(commentCard, flagsSection);
    //         }
    //     }
    // }

    // window.addEventListener('resize', reorder);
    // reorder();



});


// document.addEventListener('DOMContentLoaded', function() {
    
//     // Keyboard shortcuts for classification
//     document.addEventListener('keydown', function(event) {
//         // Only process keyboard shortcuts if we're on the classification page
//         if (!document.getElementById('classification-form')) return;
        
//         switch(event.key) {
//             case 'c':
//                 // Change contrast
//                 document.getElementById('contrast-btn').click();
//                 break;
//             case 'r':
//                 // Toggle redshift validity
//                 const redshiftCheckbox = document.getElementById('valid_redshift');
//                 if (redshiftCheckbox) {
//                     redshiftCheckbox.checked = !redshiftCheckbox.checked;
//                 }
//                 break;
//             case 'a':
//                 // Toggle awesome flag
//                 const awesomeCheckbox = document.getElementById('awesome_flag');
//                 if (awesomeCheckbox) {
//                     awesomeCheckbox.checked = !awesomeCheckbox.checked;
//                 }
//                 break;
//             case '1':
//                 // LSB classifications
//                 if (event.ctrlKey) {
//                     document.getElementById('lsb-failed').checked = true;
//                 } else {
//                     document.getElementById('lsb-yes').checked = true;
//                 }
//                 break;
//             case '0':
//                 // Non-LSB
//                 document.getElementById('lsb-no').checked = true;
//                 break;
//             case 'f':
//                 // Featureless morphology
//                 document.getElementById('morph-featureless').checked = true;
//                 break;
//             case 's':
//                 // LTG (Spiral)
//                 document.getElementById('morph-ltg').checked = true;
//                 break;
//             case 'e':
//                 // ETG (Elliptical)
//                 document.getElementById('morph-etg').checked = true;
//                 break;
//             case 'n':
//                 // Next galaxy (submit form)
//                 if (validateForm()) {
//                     document.getElementById('classification-form').submit();
//                 }
//                 break;
//         }
//     });
    
//     // Form validation
//     function validateForm() {
//         const form = document.getElementById('classification-form');
//         if (!form) return true;
        
//         const lsbSelected = form.querySelector('input[name="lsb_class"]:checked');
//         const morphSelected = form.querySelector('input[name="morphology"]:checked');
        
//         if (!lsbSelected) {
//             alert('Please select an LSB classification.');
//             return false;
//         }
        
//         // If it's not "Failed fitting", require morphology
//         if (lsbSelected.value !== "-1" && !morphSelected) {
//             alert('Please select a morphology type.');
//             return false;
//         }
        
//         return true;
//     }
    
//     // Add validation to form submission
//     const form = document.getElementById('classification-form');
//     if (form) {
//         form.addEventListener('submit', function(event) {
//             if (!validateForm()) {
//                 event.preventDefault();
//             }
//         });
//     }
    
//     // Initialize tooltips if any
//     const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
//     if (tooltipTriggerList.length > 0) {
//         tooltipTriggerList.map(function(tooltipTriggerEl) {
//             return new bootstrap.Tooltip(tooltipTriggerEl);
//         });
//     }
// });


