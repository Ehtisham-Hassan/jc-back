import pinecone
from openai import OpenAI
import sys
from typing import List, Dict, Any
import json
import uuid
from datetime import datetime
from backend.core.config import settings

# Initialize Pinecone and OpenAI clients
try:
    pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception as e:
    print(f"Error initializing clients: {e}")
    raise e

# Connect to the index with provided configurations
try:
    index = pc.Index(
        name=settings.PINECONE_INDEX_NAME,
        host=settings.PINECONE_HOST
    )
except Exception as e:
    print(f"Error connecting to index: {e}")
    raise e

def upsert_mapping_data_to_pinecone(ai_response: Dict[str, Any], file_id: str, client_number: str = None) -> Dict[str, Any]:
    """
    Upsert AI agent response data to Pinecone JC index.
    
    Args:
        ai_response: The response from the AI agent containing mapping data
        file_id: The ID of the uploaded file
        client_number: The client number (optional)
    
    Returns:
        Dict containing the result of the upsert operation
    """
    try:
        # Generate a unique ID for this mapping data
        mapping_id = str(uuid.uuid4())
        
        # Prepare the text data for embedding
        # Convert the AI response to a structured text representation
        mapping_text = _prepare_mapping_text(ai_response)
        
        # Generate embedding using OpenAI text-embedding-3-small (512 dimensions)
        response = client.embeddings.create(
            input=mapping_text, 
            model="text-embedding-3-small", 
            dimensions=512
        )
        embedding = response.data[0].embedding
        
        # Verify embedding dimension
        if len(embedding) != 512:
            raise ValueError(f"Embedding dimension {len(embedding)} does not match index dimension 512")
        
        # Prepare metadata
        metadata = {
            "mapping_id": mapping_id,
            "file_id": file_id,
            "client_number": client_number,
            "mapping_data": json.dumps(ai_response),
            "mapping_text": mapping_text,
            "created_at": datetime.now().isoformat(),
            "type": "jc_mapping"
        }
        
        # Prepare vector for upsert
        vector = {
            "id": mapping_id,
            "values": embedding,
            "metadata": metadata
        }
        
        # Upsert to Pinecone
        index.upsert(vectors=[vector], namespace="default")
        
        print(f"✅ Successfully upserted mapping data to Pinecone with ID: {mapping_id}")
        
        return {
            "success": True,
            "mapping_id": mapping_id,
            "message": "Mapping data successfully saved to Pinecone",
            "vector_id": mapping_id
        }
        
    except Exception as e:
        print(f"❌ Error upserting mapping data to Pinecone: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to save mapping data to Pinecone"
        }

def _prepare_mapping_text(ai_response: Dict[str, Any]) -> str:
    """
    Prepare the AI response data as structured text for embedding.
    
    Args:
        ai_response: The response from the AI agent
    
    Returns:
        Structured text representation of the mapping data
    """
    try:
        items = ai_response.get("items", [])
        if not items:
            return "No mapping data available"
        
        item = items[0]  # Get the first item
        mapping_text_parts = []
        
        # Add JC field mappings
        jc_fields = [
            "RetailerStockNumber", "StyleNumber", "VisibleAs", "ParentSKU", "ProductType",
            "SelectedAttributes", "ProductName", "ProductDescription", "CustomAttribute",
            "CustomAttributeLabel", "ConfigurableControlType", "IsConfigurableProduct",
            "ControlDisplayOrder", "Categories", "Collections", "PriceType",
            "WholesaleBasePrice", "MSRP", "MetalType", "MetalColor", "ImagePath", "Gender"
        ]
        
        for jc_field in jc_fields:
            if jc_field in item and jc_field != "other_fields":
                mapping_data = item[jc_field]
                vendor_field = mapping_data.get("vendor_field", "")
                confidence = mapping_data.get("confidence", 0.0)
                if vendor_field:
                    mapping_text_parts.append(f"{jc_field}: {vendor_field} (confidence: {confidence})")
        
        # Add other fields
        other_fields = item.get("other_fields", [])
        for field in other_fields:
            vendor_field = field.get("vendor_field", "")
            confidence = field.get("confidence", 0.0)
            if vendor_field:
                mapping_text_parts.append(f"Other field: {vendor_field} (confidence: {confidence})")
        
        # Join all parts with newlines
        mapping_text = "\n".join(mapping_text_parts)
        
        if not mapping_text.strip():
            mapping_text = "Empty mapping data"
        
        return mapping_text
        
    except Exception as e:
        print(f"Error preparing mapping text: {e}")
        return "Error processing mapping data"

def search_mapping_data(query_text: str, top_k: int = 5, client_number: str = None) -> Dict[str, Any]:
    """
    Search for mapping data in Pinecone index.
    
    Args:
        query_text: The search query
        top_k: Number of results to return
        client_number: Filter by client number (optional)
    
    Returns:
        Dict containing search results
    """
    try:
        # Generate embedding for the query
        query_response = client.embeddings.create(
            input=query_text, 
            model="text-embedding-3-small", 
            dimensions=512
        )
        query_embedding = query_response.data[0].embedding
        
        # Verify query embedding dimension
        if len(query_embedding) != 512:
            raise ValueError(f"Query embedding dimension {len(query_embedding)} does not match index dimension 512")
        
        # Prepare filter if client_number is provided
        filter_dict = {"type": "jc_mapping"}
        if client_number:
            filter_dict["client_number"] = client_number
        
        # Perform relevance search
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace="default",
            filter=filter_dict
        )
        
        # Process results
        processed_results = []
        for match in results["matches"]:
            try:
                mapping_data = json.loads(match["metadata"]["mapping_data"])
                processed_results.append({
                    "id": match["id"],
                    "score": match["score"],
                    "mapping_data": mapping_data,
                    "file_id": match["metadata"]["file_id"],
                    "client_number": match["metadata"]["client_number"],
                    "created_at": match["metadata"]["created_at"]
                })
            except json.JSONDecodeError:
                # Skip results with invalid JSON
                continue
        
        return {
            "success": True,
            "results": processed_results,
            "total_found": len(processed_results)
        }
        
    except Exception as e:
        print(f"❌ Error searching mapping data: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "total_found": 0
        }

def delete_mapping_data(mapping_id: str) -> Dict[str, Any]:
    """
    Delete mapping data from Pinecone index.
    
    Args:
        mapping_id: The ID of the mapping data to delete
    
    Returns:
        Dict containing the result of the delete operation
    """
    try:
        # Delete from Pinecone
        index.delete(ids=[mapping_id], namespace="default")
        
        print(f"✅ Successfully deleted mapping data from Pinecone with ID: {mapping_id}")
        
        return {
            "success": True,
            "message": f"Mapping data with ID {mapping_id} successfully deleted from Pinecone"
        }
        
    except Exception as e:
        print(f"❌ Error deleting mapping data from Pinecone: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete mapping data with ID {mapping_id}"
        }
