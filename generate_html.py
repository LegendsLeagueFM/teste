import json
import re
import html

def load_data(parsed_law_file, cross_refs_file):
    """Loads data from JSON files."""
    try:
        with open(parsed_law_file, 'r', encoding='utf-8') as f:
            parsed_law = json.load(f)
    except FileNotFoundError:
        print(f"Error: {parsed_law_file} not found.")
        parsed_law = []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {parsed_law_file}.")
        parsed_law = []

    try:
        with open(cross_refs_file, 'r', encoding='utf-8') as f:
            cross_refs_list = json.load(f)
    except FileNotFoundError:
        print(f"Error: {cross_refs_file} not found.")
        cross_refs_list = []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {cross_refs_file}.")
        cross_refs_list = []

    # Preprocess cross-references for easier lookup
    cross_refs_map = {}
    for ref in cross_refs_list:
        source_id = ref.get("source_id")
        if source_id:
            if source_id not in cross_refs_map:
                cross_refs_map[source_id] = []
            cross_refs_map[source_id].append(ref)
    
    # Sort references by length of source_text (descending) to handle overlapping matches correctly.
    for source_id in cross_refs_map:
        cross_refs_map[source_id].sort(key=lambda r: len(r.get("source_text", "")), reverse=True)
        
    return parsed_law, cross_refs_map

def apply_cross_references(text, element_id, cross_refs_map):
    """Applies cross-reference spans to the text."""
    if not text or element_id not in cross_refs_map:
        return html.escape(text)

    modified_text = text
    references_for_id = cross_refs_map[element_id]

    for ref in references_for_id:
        source_text = ref.get("source_text")
        target_id = ref.get("target_id")
        if source_text and target_id:
            # Escape HTML in source_text for display, and regex special chars for replacement
            escaped_source_text_for_display = html.escape(source_text)
            
            # Create the span tag
            span_tag = f'<span class="cross-ref" data-ref-target="{html.escape(target_id)}">{escaped_source_text_for_display}</span>'
            
            # Replace using regex to handle whole words or specific contexts if necessary,
            # for now, simple string replacement using re.escape for the pattern.
            # This ensures that if source_text has regex characters, they are treated literally.
            # We use a try-except block because re.sub can fail with complex patterns if not careful
            try:
                # Only replace if source_text is actually in modified_text to avoid errors with replacement logic
                if re.search(re.escape(source_text), modified_text):
                     modified_text = re.sub(re.escape(source_text), span_tag, modified_text)
                # If simple string replacement is safer and sufficient:
                # modified_text = modified_text.replace(source_text, span_tag)
            except re.error as e:
                print(f"Regex error while applying cross-reference for '{source_text}' in ID '{element_id}': {e}")
                # Fallback to original text if regex fails for this specific reference
                # Or, potentially, just don't replace this one reference.
                # For now, we'll just print error and continue with potentially un-replaced text for this ref.

    # Final escape for any text not part of a span.
    # This is tricky. If we escape `modified_text` here, we escape our own spans.
    # The text parts should be escaped BEFORE span insertion, or spans handled carefully.
    # Current approach: `source_text` is escaped for display within span.
    # `text` is taken as is and `re.sub` inserts spans.
    # This implies `text` should not contain raw HTML that needs escaping,
    # or if it does, it should be handled when `text` is originally extracted.
    # For this project, assume `text` from JSON is plain text.

    return modified_text # Spans are already built with escaped content.

def get_element_header_text(element):
    """Extracts or constructs header text for elements like Titulo, Capitulo, Artigo."""
    text = element.get('text', '')
    element_type = element.get('type', '')
    element_id = element.get('id', '')

    if element_type == "artigo":
        # For articles, the 'text' is the caput. The header is "Art. Xº"
        # We need to extract this from the ID or text.
        match = re.match(r"Art\.?\s*(\d+[a-zA-Z]*)", text) # Try to get "Art. X" from text
        if match:
            return f"Art. {match.group(1)}" # Art. 1º, Art. 1A, etc.
        elif element_id.startswith("art"): # Fallback to ID
             return f"Art. {element_id[3:]}" # Crude, assumes artXXX format
        return "Artigo" # Generic fallback
    
    # For Titulo, Capitulo, the text itself is often the header.
    # Sometimes it includes more than just "TITULO X", like "TITULO X - DAS DISPOSICOES"
    # The full text is probably fine for the header.
    return html.escape(text.splitlines()[0]) # Use first line of text as header


def build_html_for_element(element, cross_refs_map):
    """Recursively builds HTML for a law element and its children."""
    element_id = element.get('id', '')
    element_type = element.get('type', '')
    # The 'text' for Artigo is its caput. For Titulo/Capitulo, it's their name/description.
    # For Inciso, Paragrafo, Alinea, it's their full content.
    element_text_content = element.get('text', '')
    
    # Apply cross-references to the main text content of the element
    processed_text_content = apply_cross_references(element_text_content, element_id, cross_refs_map)

    children_html = ""
    if element.get('children'):
        for child in element['children']:
            children_html += build_html_for_element(child, cross_refs_map)

    item_class = f"{element_type}-item"
    html_string = f'<div id="{html.escape(element_id)}" class="{item_class}">\n'

    is_collapsible_parent = element_type in ["titulo", "capitulo", "artigo"]

    if element_type == "lei": # Special handling for the root "lei" element
        # The "text" of "lei" is its title, e.g., "LEI Nº 14.133..."
        html_string += f'<h1>{processed_text_content}</h1>\n'
        if children_html:
            html_string += f'<div class="lei-content">{children_html}</div>\n'
    elif is_collapsible_parent:
        header_text = get_element_header_text(element)
        header_tag = {"titulo": "h2", "capitulo": "h3", "artigo": "h4"}.get(element_type, "h5")
        
        html_string += f'<{header_tag} class="{element_type}-header">{header_text}</{header_tag}>\n'
        
        # For Articles, their main text (caput) is displayed before children
        if element_type == "artigo":
            html_string += f'<div class="article-text">{processed_text_content}</div>\n'
            if children_html: # Incisos, Paragrafos, etc.
                html_string += f'<div class="article-children" style="display: none;">{children_html}</div>\n'
        elif children_html: # For Titulo, Capitulo
             html_string += f'<div class="{element_type}-content" style="display: none;">{children_html}</div>\n'
    else: # For non-collapsible children like inciso, paragrafo, alinea
        # Their processed_text_content is their full content.
        html_string += f'<p>{processed_text_content}</p>\n' 
        # These types generally don't have further structural children in the same way,
        # but if they did (e.g. alinea under inciso that itself has children in JSON),
        # the children_html would be appended here.
        if children_html: # Should typically be empty for I, P, A based on common law structure
            html_string += children_html


    html_string += '</div>\n'
    return html_string

def generate_page_html(parsed_law, cross_refs_map):
    """Generates the full HTML page content."""
    body_content = ""
    for top_level_element in parsed_law:
        body_content += build_html_for_element(top_level_element, cross_refs_map)

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lei 14.133/2021 - Nova Lei de Licitações</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    {body_content}
    <script src="script.js"></script>
</body>
</html>"""
    return html_template

def main():
    parsed_law_file = 'parsed_law.json'
    cross_refs_file = 'cross_references.json'
    output_html_file = 'index.html'

    parsed_law, cross_refs_map = load_data(parsed_law_file, cross_refs_file)

    if not parsed_law:
        print("No law data loaded. HTML will be empty or minimal.")
        # Create a minimal HTML to indicate failure or empty content
        page_html = """<!DOCTYPE html><html lang="pt-BR"><head><title>Error</title></head>
                       <body><h1>Error: Could not load law data.</h1></body></html>"""
    else:
        page_html = generate_page_html(parsed_law, cross_refs_map)

    try:
        with open(output_html_file, 'w', encoding='utf-8') as f:
            f.write(page_html)
        print(f"Successfully generated {output_html_file}")
    except IOError:
        print(f"Error: Could not write to {output_html_file}")

if __name__ == '__main__':
    main()
