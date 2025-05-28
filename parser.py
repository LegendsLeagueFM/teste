import json
import re
from bs4 import BeautifulSoup, NavigableString, Tag

# --- Fallback HTML content (used if law_content.html is not found/empty) ---
HTML_CONTENT_FALLBACK = """
<html>
<body>
    <p align="center"><strong>PRESIDÊNCIA DA REPÚBLICA</strong></p>
    <p align="center"><a name="LEI14133"></a><strong>LEI Nº 14.133, DE 1º DE ABRIL DE 2021</strong></p>
    <p align="center"><a name="tituloI">TÍTULO I</a></p>
    <p align="center">DISPOSIÇÕES PRELIMINARES</p>
    <p align="center"><a name="tituloIcapituloI">CAPÍTULO I</a></p>
    <p align="center">DO ÂMBITO DE APLICAÇÃO</p>
    <p><a name="art1"></a>Art. 1º Esta Lei estabelece normas gerais de licitação e contratação para...</p>
    <p><a name="art1i"></a>I - os órgãos dos Poderes Legislativo e Judiciário...</p>
    <p><a name="art1ii"></a>II - os fundos especiais...</p>
    <p><a name="art1§1"></a>§ 1º Não são abrangidas por esta Lei... <a href="#art178">art. 178 desta Lei.</a></p>
    <p><a name="art1§1i"></a>I - (Inciso I do § 1º) Exemplo de inciso de parágrafo.</p>
    <p><a name="art1§1ia"></a>a) (Alínea 'a' do Inciso I do § 1º) Exemplo de alínea de inciso de parágrafo.</p>
    <p><a name="art1§2"></a>§ 2º As contratações realizadas no âmbito...</p>
    <p><a name="art1§3"></a>§ 3º Nas licitações e contratações que envolvam recursos...</p>
    <p><a name="art1§3i"></a>I - condições decorrentes de acordos internacionais...</p> <!-- Should be Inciso I of Art. 1 §3 -->
    <p><a name="art1§3ii"></a>II - normas e procedimentos próprios das agências ou dos organismos, desde que:</p> <!-- Should be Inciso II of Art. 1 §3 -->
    <p><a name="art1§3iia"></a>a) sejam exigidos para a obtenção do empréstimo...</p> <!-- Should be Alínea 'a' of Inciso II of Art. 1 §3 -->
    <p><a name="art1§3iib"></a>b) não conflitem com os princípios básicos...</p>
    <p><a name="art1§3iic"></a>c) sejam indicados no respectivo contrato...</p>
    <p align="center"><a name="tituloIcapituloII">CAPÍTULO II</a></p>
    <p align="center">DOS PRINCÍPIOS</p>
    <p><a name="art2"></a>Art. 2º A Nova Lei de Licitações e Contratos Administrativos rege-se pelos princípios... <a href="#art1">Veja Art. 1</a>.</p>
    <p><a name="art2punico"></a>Parágrafo único. A Administração Pública zelará...</p>
    <p><a name="art3"></a>Art. 3º Este é o artigo 3, sem sub-itens.</p>
    <p align="left" style="text-align:justify;">Este é um parágrafo normal com <a href="#art2">referência ao art. 2</a> e sem 'name'.</p>
</body>
</html>
"""
# --- End of Fallback HTML ---

# Global variable to hold the root of the parsed law structure, used for context in get_element_type
parsed_law_root_for_context = []


def get_element_type_and_text(p_tag, a_tag_name_attr): # Copied from Turn 11
    element_id = a_tag_name_attr
    element_type = "unknown"
    
    # Consolidate text from the p_tag
    pieces = []
    for elem in p_tag.contents:
        if isinstance(elem, NavigableString):
            pieces.append(elem.strip())
        elif isinstance(elem, Tag):
            pieces.append(elem.get_text(separator=" ", strip=True))
    text_content = " ".join(filter(None, pieces))

    if text_content.startswith(element_id + " "):
        text_content = text_content[len(element_id)+1:].strip()

    # Regex patterns for parts of IDs
    art_pattern = r"art\d+[a-z]?"
    par_pattern = r"§\d+[a-z]?" 
    inc_pattern = r"(?:[ivxlcdm]+|inc\d+)"
    ali_pattern = r"[a-z]"

    # Order of these regex checks is crucial
    if re.fullmatch(f"{art_pattern}{par_pattern}{inc_pattern}{ali_pattern}", element_id, re.IGNORECASE):
        element_type = "alinea"
    elif re.fullmatch(f"{art_pattern}{par_pattern}{ali_pattern}", element_id, re.IGNORECASE):
        element_type = "alinea"
    elif re.fullmatch(f"{art_pattern}{inc_pattern}{ali_pattern}", element_id, re.IGNORECASE):
        element_type = "alinea"
    elif re.fullmatch(f"{art_pattern}{par_pattern}{inc_pattern}", element_id, re.IGNORECASE):
        element_type = "inciso"
    elif re.fullmatch(f"{art_pattern}{inc_pattern}", element_id, re.IGNORECASE):
        element_type = "inciso"
    elif re.fullmatch(f"{art_pattern}{par_pattern}", element_id, re.IGNORECASE) or \
         re.fullmatch(f"{art_pattern}punico", element_id, re.IGNORECASE):
        element_type = "paragrafo"
        if "punico" in element_id.lower() and not text_content.lower().startswith("parágrafo único"):
            text_content = "Parágrafo único. " + text_content
    elif re.fullmatch(art_pattern, element_id, re.IGNORECASE):
        element_type = "artigo"
    elif re.match(r"titulo\w+capitulo\w+", element_id, re.IGNORECASE):
        element_type = "capitulo"
    elif re.match(r"titulo\w+", element_id, re.IGNORECASE):
        element_type = "titulo"
    elif element_id.upper().startswith("LEI") and not parsed_law_root_for_context: 
        element_type = "lei"

    return element_type, text_content.strip()


def parse_law(html_content_str): # Copied from Turn 11
    global parsed_law_root_for_context
    parsed_law_root_for_context = [] 
    
    soup = BeautifulSoup(html_content_str, 'html.parser')
    cross_references = []
    
    parent_context = {
        "lei": None, "titulo": None, "capitulo": None, "artigo": None,
        "paragrafo": None, "inciso": None
    }
    last_structural_element_id = None

    all_p_tags = soup.find_all('p')

    for p_tag in all_p_tags:
        a_tag = p_tag.find('a', attrs={'name': True})
        current_element_data = None

        if a_tag and 'name' in a_tag.attrs:
            element_id = a_tag['name']
            # Try to get type and text. If type is unknown, we might still process for links if it's a plain p later
            element_type, text = get_element_type_and_text(p_tag, element_id)

            # Only create a structural element if its type is known
            if element_type != "unknown":
                current_element_data = {
                    "id": element_id, "type": element_type,
                    "text": text, "children": []
                }
                last_structural_element_id = element_id 

                # --- Hierarchy Logic (from Turn 11) ---
                if element_type == "lei":
                    parsed_law_root_for_context.append(current_element_data)
                    parent_context = {k: None for k in parent_context} 
                    parent_context["lei"] = current_element_data
                elif element_type == "titulo":
                    target_list = parent_context["lei"]["children"] if parent_context["lei"] else parsed_law_root_for_context
                    target_list.append(current_element_data)
                    parent_context["titulo"] = current_element_data
                    parent_context["capitulo"] = None; parent_context["artigo"] = None; parent_context["paragrafo"] = None; parent_context["inciso"] = None
                elif element_type == "capitulo":
                    target_list = parent_context["titulo"]["children"] if parent_context["titulo"] else parsed_law_root_for_context 
                    target_list.append(current_element_data)
                    parent_context["capitulo"] = current_element_data
                    parent_context["artigo"] = None; parent_context["paragrafo"] = None; parent_context["inciso"] = None
                elif element_type == "artigo":
                    target_list = None
                    if parent_context["capitulo"]: target_list = parent_context["capitulo"]["children"]
                    elif parent_context["titulo"]: target_list = parent_context["titulo"]["children"]
                    elif parent_context["lei"]: target_list = parent_context["lei"]["children"]
                    else: target_list = parsed_law_root_for_context
                    target_list.append(current_element_data)
                    parent_context["artigo"] = current_element_data
                    parent_context["paragrafo"] = None; parent_context["inciso"] = None
                elif element_type == "paragrafo":
                    if parent_context["artigo"]:
                        parent_context["artigo"]["children"].append(current_element_data)
                        parent_context["paragrafo"] = current_element_data
                        parent_context["inciso"] = None 
                    # else: orphan
                elif element_type == "inciso":
                    parent_for_inciso = parent_context["paragrafo"] or parent_context["artigo"]
                    if parent_for_inciso:
                        parent_for_inciso["children"].append(current_element_data)
                        parent_context["inciso"] = current_element_data 
                    # else: orphan
                elif element_type == "alinea":
                    parent_for_alinea = parent_context["inciso"] or parent_context["paragrafo"]
                    if parent_for_alinea:
                        parent_for_alinea["children"].append(current_element_data)
                    # else: orphan
            # If element_type IS "unknown" but p_tag has a 'name', it's an anchor we don't classify structurally.
            # last_structural_element_id should NOT be updated by these.
            # It will be processed for cross-references using the *previous* last_structural_element_id.

        # --- Cross-Reference Extraction ---
        # This part should run for ALL p_tags that could contain links,
        # regardless of whether they defined a new structural element themselves.
        # source_id_for_ref is the ID of the last known structural element that successfully parsed.
        source_id_for_ref = last_structural_element_id 
        
        if source_id_for_ref: 
            for ref_a_tag in p_tag.find_all('a', href=True):
                href = ref_a_tag['href']
                is_internal_anchor = href.startswith('#') and len(href) > 1
                is_not_self_name_link = not (ref_a_tag.has_attr('name') and ref_a_tag['name'] == href[1:])
                
                if is_internal_anchor and is_not_self_name_link:
                    target_id = href[1:]
                    source_text = ref_a_tag.get_text(separator=' ', strip=True)
                    if target_id: 
                        cross_references.append({
                            "source_id": source_id_for_ref,
                            "source_text": source_text,
                            "target_id": target_id
                        })
    
    return parsed_law_root_for_context, cross_references

def main():
    html_content = ""
    try:
        with open('law_content.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        if not html_content or not html_content.strip(): # Check if file is empty or only whitespace
            print("law_content.html is empty or contains only whitespace, using fallback HTML content.")
            html_content = HTML_CONTENT_FALLBACK
    except FileNotFoundError:
        print("law_content.html not found, using fallback HTML content.")
        html_content = HTML_CONTENT_FALLBACK
    except Exception as e:
        print(f"Error reading law_content.html: {e}. Using fallback HTML content.")
        html_content = HTML_CONTENT_FALLBACK

    if not html_content or not html_content.strip():
        print("Error: HTML content is empty even after fallback. Cannot parse.")
        with open('parsed_law.json', 'w', encoding='utf-8') as f: json.dump([], f, ensure_ascii=False, indent=4)
        with open('cross_references.json', 'w', encoding='utf-8') as f: json.dump([], f, ensure_ascii=False, indent=4)
        return

    global parsed_law_root_for_context
    parsed_law_root_for_context = []

    parsed_law_data, cross_references_data = parse_law(html_content)

    with open('parsed_law.json', 'w', encoding='utf-8') as f:
        json.dump(parsed_law_data, f, ensure_ascii=False, indent=4)
    with open('cross_references.json', 'w', encoding='utf-8') as f:
        json.dump(cross_references_data, f, ensure_ascii=False, indent=4)

    print("Parsing complete. Check 'parsed_law.json' and 'cross_references.json'.")

if __name__ == '__main__':
    main()
