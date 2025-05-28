document.addEventListener('DOMContentLoaded', function() {

    // --- Collapsible Sections ---
    const collapsibleHeaders = document.querySelectorAll('.title-header, .chapter-header, .article-header');

    collapsibleHeaders.forEach(header => {
        header.addEventListener('click', function() {
            // Toggle 'expanded' class on the header itself for potential CSS styling (e.g., +/- icon)
            this.classList.toggle('expanded');

            // Find the content to toggle.
            // Assuming the content div is the next sibling OR a specific class within the parent.
            let contentElement = null;
            const parentItem = this.parentElement; // e.g., .title-item, .chapter-item, .article-item

            if (parentItem) {
                if (this.classList.contains('title-header')) {
                    contentElement = parentItem.querySelector('.title-content');
                } else if (this.classList.contains('chapter-header')) {
                    contentElement = parentItem.querySelector('.chapter-content');
                } else if (this.classList.contains('article-header')) {
                    contentElement = parentItem.querySelector('.article-children');
                }
            }
            
            if (contentElement) {
                if (contentElement.style.display === 'none' || contentElement.style.display === '') {
                    contentElement.style.display = 'block';
                } else {
                    contentElement.style.display = 'none';
                }
            }
        });

        // Add a simple visual cue like a cursor pointer to headers
        header.style.cursor = 'pointer';
    });

    // --- Tooltip Functionality for Cross-References ---
    const crossRefSpans = document.querySelectorAll('.cross-ref');
    let activeTooltip = null; // To keep track of the currently displayed tooltip

    crossRefSpans.forEach(span => {
        span.addEventListener('mouseover', function(event) {
            // Remove any existing tooltip first
            if (activeTooltip) {
                activeTooltip.remove();
                activeTooltip = null;
            }

            const targetId = this.dataset.refTarget;
            if (!targetId) return;

            const targetElement = document.getElementById(targetId);
            let tooltipText = `Referência para '${targetId}' não encontrada.`; // Default error message

            if (targetElement) {
                // Try to get more specific text content
                if (targetElement.classList.contains('article-item')) {
                    const articleTextDiv = targetElement.querySelector('.article-text');
                    if (articleTextDiv) {
                        tooltipText = articleTextDiv.textContent || articleTextDiv.innerText;
                    } else {
                        tooltipText = targetElement.textContent || targetElement.innerText; // Fallback
                    }
                } else if (targetElement.classList.contains('inciso-item') ||
                           targetElement.classList.contains('paragrafo-item') ||
                           targetElement.classList.contains('alinea-item')) {
                     // For these, the main text is usually within the first <p> tag or directly
                     const pElement = targetElement.querySelector('p');
                     if (pElement) {
                        tooltipText = pElement.textContent || pElement.innerText;
                     } else {
                        tooltipText = targetElement.textContent || targetElement.innerText;
                     }
                } else { // For Titulo, Capitulo, or other types
                    // Attempt to get a header text or the main text content
                    const header = targetElement.querySelector('.title-header, .chapter-header, .article-header');
                    if (header) {
                        tooltipText = header.textContent || header.innerText;
                    } else {
                        // Fallback to the element's own text if no specific part found
                        tooltipText = targetElement.textContent || targetElement.innerText;
                    }
                }
                // Limit tooltip length
                if (tooltipText.length > 300) {
                    tooltipText = tooltipText.substring(0, 297) + "...";
                }
            }
            
            // Create tooltip element
            activeTooltip = document.createElement('div');
            activeTooltip.id = 'ref-tooltip'; // Assign an ID for potential styling or direct removal
            activeTooltip.className = 'ref-tooltip-active'; // Class for styling
            activeTooltip.innerHTML = tooltipText.trim().replace(/\n\s*\n/g, '<br>'); // Clean up and convert newlines

            // Positioning the tooltip
            // Position near the cursor, but avoid going off-screen (basic implementation)
            let top = event.pageY + 15;
            let left = event.pageX + 10;

            // Append to body to ensure it's on top of other elements
            document.body.appendChild(activeTooltip);
            
            // Adjust if tooltip goes off-screen (simple adjustment)
            if (left + activeTooltip.offsetWidth > window.innerWidth) {
                left = window.innerWidth - activeTooltip.offsetWidth - 10;
            }
            if (top + activeTooltip.offsetHeight > window.innerHeight) {
                top = event.pageY - activeTooltip.offsetHeight - 15;
            }

            activeTooltip.style.left = left + 'px';
            activeTooltip.style.top = top + 'px';
            activeTooltip.style.display = 'block'; // Make it visible

        });

        span.addEventListener('mouseout', function() {
            if (activeTooltip) {
                activeTooltip.remove();
                activeTooltip = null;
            }
        });
    });

});
