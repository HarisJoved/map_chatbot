from database import neo4j_connection

def fetch_schema():
    # Get node labels and their properties
    node_type_query = "CALL db.schema.nodeTypeProperties()"
    node_types = neo4j_connection.query(node_type_query)
    # Get relationship types
    rel_type_query = "CALL db.relationshipTypes()"
    rel_types = neo4j_connection.query(rel_type_query)
    # Format as a readable string for LLM
    schema_str = "## Database Schema\n\n"
    schema_str += "### Node Types and Properties:\n"
    node_labels = {}
    for nt in node_types:
        label = nt['nodeType']
        prop = nt['propertyName']
        typ = nt['propertyTypes']
        node_labels.setdefault(label, []).append(f"{prop} ({typ})")
    for label, props in node_labels.items():
        schema_str += f"- {label}: {', '.join(props)}\n"
    schema_str += "\n### Relationship Types:\n"
    for rel in rel_types:
        schema_str += f"- {rel['relationshipType']}\n"
    return schema_str 