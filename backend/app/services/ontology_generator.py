"""
Ontology generation service
API 1: analyze text content and generate entity and relationship type definitions suitable for social simulation.
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


# translated text
ONTOLOGY_SYSTEM_PROMPT = """You are a professional knowledge-graph ontology design expert. Your task is to analyze the given text content and simulation requirement, then design entity types and relationship types suitable for a **social media public-opinion simulation**.

**Important: You must output valid JSON data only. Do not output anything else.**

## Core Task Background

We are building a **social media public-opinion simulation system**. In this system:
- Each entity is an account or actor that can speak, interact, and spread information on social media
- Entities influence, repost, comment on, and respond to each other
- We need to simulate how all parties react to a public-opinion event and how information propagates

Therefore, **entities must be real-world actors that can plausibly speak and interact on social media**.

**Allowed examples**:
- Specific individuals, including public figures, parties involved, opinion leaders, experts, scholars, and ordinary people
- Companies and enterprises, including official accounts
- Organizations such as universities, associations, NGOs, and unions
- Government departments and regulators
- Media organizations such as newspapers, TV stations, self-media, and websites
- Social media platforms themselves
- Representatives of specific groups, such as alumni associations, fan groups, and rights-protection groups

**Not allowed**:
- Abstract concepts such as "public opinion", "emotion", or "trend"
- Topics such as "academic integrity" or "education reform"
- Viewpoints or attitudes such as "supporters" or "opponents"

## Output Format

Output JSON with this structure:

```json
{
    "entity_types": [
        {
            "name": "Entity type name (English, PascalCase)",
            "description": "Short description (English, at most 100 characters)",
            "attributes": [
                {
                    "name": "attribute_name (English, snake_case)",
                    "type": "text",
                    "description": "Attribute description"
                }
            ],
            "examples": ["example entity 1", "example entity 2"]
        }
    ],
    "edge_types": [
        {
            "name": "Relationship type name (English, UPPER_SNAKE_CASE)",
            "description": "Short description (English, at most 100 characters)",
            "source_targets": [
                {"source": "Source entity type", "target": "Target entity type"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief analysis summary of the text content (English)"
}
```

## Design Guidelines (Extremely Important)

### 1. Entity Type Design - Strict Requirements

**Count requirement: exactly 10 entity types**

**Hierarchy requirement (must include both specific and fallback types)**:

Your 10 entity types must include this hierarchy:

A. **Fallback types (required, place as the last 2 items)**:
   - `Person`: fallback type for any natural person. Use this when a person does not fit a more specific person type.
   - `Organization`: fallback type for any organization. Use this when an organization does not fit a more specific organization type.

B. **Specific types (8, designed from the text content)**:
   - Design more specific types for the main roles appearing in the text
   - For example, if the text involves an academic incident, use types like `Student`, `Professor`, `University`
   - For example, if the text involves a business incident, use types like `Company`, `CEO`, `Employee`

**Why fallback types are required**:
- The text may mention many kinds of people, such as primary/secondary school teachers, passersby, or certain netizens
- If no specific type matches them, they should be classified as `Person`
- Likewise, small organizations and temporary groups should be classified as `Organization`

**Specific type design principles**:
- Identify frequent or key role types in the text
- Each specific type should have clear boundaries and avoid overlap
- The description must clearly explain how the type differs from the fallback type

### 2. Relationship Type Design

- Count: 6-10 types
- Relationships should reflect real connections in social media interactions
- Ensure source_targets cover the entity types you define

### 3. Attribute Design

- Each entity type should have 1-3 key attributes
- **Note**: attribute names cannot use `name`, `uuid`, `group_id`, `created_at`, or `summary`; these are reserved system words
- Recommended names: `full_name`, `title`, `role`, `position`, `location`, `description`, etc.

## Entity Type Reference

**Specific person types**:
- Student: student
- Professor: professor or scholar
- Journalist: journalist
- Celebrity: celebrity or influencer
- Executive: executive
- Official: government official
- Lawyer: lawyer
- Doctor: doctor

**Fallback person type**:
- Person: any natural person not covered by the specific types above

**Specific organization types**:
- University: higher-education institution
- Company: company or enterprise
- GovernmentAgency: government agency
- MediaOutlet: media organization
- Hospital: hospital
- School: primary or secondary school
- NGO: non-governmental organization

**Fallback organization type**:
- Organization: any organization not covered by the specific types above

## Relationship Type Reference

- WORKS_FOR: works for
- STUDIES_AT: studies at
- AFFILIATED_WITH: affiliated with
- REPRESENTS: represents
- REGULATES: regulates
- REPORTS_ON: reports on
- COMMENTS_ON: comments on
- RESPONDS_TO: responds to
- SUPPORTS: supports
- OPPOSES: opposes
- COLLABORATES_WITH: collaborates with
- COMPETES_WITH: competes with
"""


class OntologyGenerator:
    """
    translated text
    translated text，translated text
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        translated text
        
        Args:
            document_texts: translated text
            simulation_requirement: translated text
            additional_context: translated text
            
        Returns:
            translated text（entity_types, edge_typestranslated text）
        """
        # translated text
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # translated textLLM
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        # translated text
        result = self._validate_and_process(result)
        
        return result
    
    # translated text LLM translated text（5translated text）
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """translated text"""
        
        # translated text
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # translated text5translated text，translated text（translated textLLMtranslated text，translated text）
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(translated text{original_length}translated text，translated text{self.MAX_TEXT_LENGTH_FOR_LLM}translated text)..."
        
        message = f"""## translated text

{simulation_requirement}

## translated text

{combined_text}
"""
        
        if additional_context:
            message += f"""
## translated text

{additional_context}
"""
        
        message += """
translated text，translated text。

**translated text**：
1. translated text10translated text
2. translated text2translated text：Person（translated text）translated text Organization（translated text）
3. translated text8translated text
4. translated text，translated text
5. translated text name、uuid、group_id translated text，translated text full_name、org_name translated text
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """translated text"""
        
        # translated text
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # translated text
        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # translated textdescriptiontranslated text100translated text
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # translated text
        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API translated text：translated text 10 translated text，translated text 10 translated text
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10
        
        # translated text
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }
        
        # translated text
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names
        
        # translated text
        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)
        
        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            
            # translated text 10 translated text，translated text
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                # translated text
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                # translated text（translated text）
                result["entity_types"] = result["entity_types"][:-to_remove]
            
            # translated text
            result["entity_types"].extend(fallbacks_to_add)
        
        # translated text（translated text）
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        translated textPythontranslated text（translated textontology.py）
        
        Args:
            ontology: translated text
            
        Returns:
            Pythontranslated text
        """
        code_lines = [
            '"""',
            'translated text',
            'translated textMiroFishtranslated text，translated text',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== translated text ==============',
            '',
        ]
        
        # translated text
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== translated text ==============')
        code_lines.append('')
        
        # translated text
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # translated textPascalCasetranslated text
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # translated text
        code_lines.append('# ============== translated text ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # translated textsource_targetstranslated text
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)

