from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from sqlalchemy.orm import Session
from typing import Any, List
import uuid
import os
import json
import pandas as pd
from pydantic import BaseModel

from backend.core.database import get_db
from backend.models.mapping import Mapping
from backend.api.endpoint.db import upsert_mapping_data_to_pinecone, search_mapping_data, delete_mapping_data

router = APIRouter()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_result_with_watch_data(final_output: dict, file_id: str) -> None:
    """
    Generate result.csv from final_output and enrich it using data from user_file_path.csv
    where vendor_field matches watch column headers. Ensures row alignment.
    """
    try:
        print("final_output: ", final_output)

        _, extension = os.path.splitext(file_id)
        file_output = str(uuid.uuid4()) + extension

        print("file_output: ", file_output)

        result_path = os.path.join("uploads", file_output) 
        user_file_path = os.path.join("uploads", file_id) 
        print("user_file_path: ", user_file_path)
        # ---- Step 1: Build initial result DataFrame from final_output ----
        item = final_output["items"][0]
        column_data = {}
        print("item: ", item)
        # JC fields
        for jc_field, mapping in item.items():
            if jc_field == "other_fields":
                continue
            vendor_field = mapping.get("vendor_field", "")
            column_data[jc_field] = [vendor_field]  # header row
        print("column_data: ", column_data)
        # Other fields
        other_fields = item.get("other_fields", [])
        for field in other_fields:
            vendor_field = field.get("vendor_field", "").strip()
            if vendor_field:
                column_data[vendor_field] = [vendor_field]
        print("column_data: ", column_data)
        # Base DataFrame with headers and first row (vendor fields)
        result_df = pd.DataFrame(column_data)
        vendor_field_map = {col: result_df.iloc[0][col].strip() for col in result_df.columns}

        # ---- Step 2: Load user_file_path ----
        if not os.path.exists(user_file_path):
            raise FileNotFoundError(f"user_file_path not found at {user_file_path}")
        
        # Determine file type and read accordingly
        if user_file_path.lower().endswith('.csv'):
            try:
                # Try reading with default settings first
                watch_df = pd.read_csv(user_file_path)
            except Exception as csv_error:
                print(f"Error reading CSV with default settings: {csv_error}")
                # Try with different encoding and separator
                try:
                    watch_df = pd.read_csv(user_file_path, encoding='utf-8', sep=',')
                except Exception as csv_error2:
                    print(f"Error reading CSV with utf-8 encoding: {csv_error2}")
                    # Try with latin-1 encoding
                    watch_df = pd.read_csv(user_file_path, encoding='latin-1', sep=',')
        elif user_file_path.lower().endswith(('.xlsx', '.xls')):
            watch_df = pd.read_excel(user_file_path)
        else:
            raise ValueError(f"Unsupported file type: {user_file_path}")
        print("watch_df: ", watch_df)
        # Extract all values from userfile
        watch_headers = watch_df.columns
        max_data_len = max(len(watch_df[col].dropna()) - 1 for col in watch_headers if len(watch_df[col]) > 1)
        print("max_data_len: ", max_data_len)
        # Initialize aligned data storage
        aligned_data = {}

        for result_col in result_df.columns:
            matched_watch_col = next((col for col in watch_headers if vendor_field_map[result_col] == col.strip()), None)
            if matched_watch_col:
                # Take all values except the header
                values = watch_df[matched_watch_col].tolist()[1:]
                # Pad if shorter than max
                if len(values) < max_data_len:
                    values += [''] * (max_data_len - len(values))
                aligned_data[result_col] = [vendor_field_map[result_col]] + values
                print(f"✅ Matched: {matched_watch_col} → {result_col}")
            else:
                # Fill with blanks if not matched
                aligned_data[result_col] = [vendor_field_map[result_col]] + [''] * max_data_len

        # ---- Step 3: Finalize and Save ----
        final_df = pd.DataFrame(aligned_data)
        
        # Save the file based on the extension
        if result_path.lower().endswith('.csv'):
            final_df.to_csv(result_path, index=False)
        elif result_path.lower().endswith(('.xlsx', '.xls')):
            final_df.to_excel(result_path, index=False)
        else:
            # Default to Excel if unknown extension
            final_df.to_excel(result_path, index=False)
            
        print(f"✅ Final result saved at: {result_path}")
        
        # Convert DataFrame to 2D array (list of lists)
        # Get headers as first row
        headers = list(final_df.columns)
        data_2d = [headers]  # First row contains headers
        
        # Add data rows
        for _, row in final_df.iterrows():
            data_row = []
            for col in headers:
                value = row[col]
                # Convert NaN to empty string and ensure all values are strings
                if pd.isna(value):
                    data_row.append("")
                else:
                    data_row.append(str(value))
            data_2d.append(data_row)
        
        print(f"✅ Generated 2D array with {len(data_2d)} rows and {len(headers)} columns")
        
        # Return both the data and metadata
        return {
            "data": data_2d,
            "headers": headers,
            "total_rows": len(data_2d),
            "total_columns": len(headers),
            "file_path": result_path
        }

    except Exception as e:
        print(f"❌ Error in generate_result_with_watch_data: {e}")
        raise e

# ============================================================================
# MAPPING ENDPOINTS
# ============================================================================

@router.post("/mapping/ai-suggested")
async def generate_ai_suggested_mappings(
    file_id: str,
    client_number: str = Form(None, description="Client number for the mapping"),
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Generate AI-suggested field mappings using OpenAI and Pinecone.
    """
    print("generate_ai_suggested_mappings" ,file_id)

    # 1. Get the file record from DB
    try:
        print("file_id: ", file_id)
        file_path = os.path.join("uploads", file_id)
        print("file_path: ", file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        # Determine file type and read accordingly
        if file_id.lower().endswith('.csv'):
            try:
                # Try reading with default settings first
                df = pd.read_csv(file_path)
            except Exception as csv_error:
                print(f"Error reading CSV with default settings: {csv_error}")
                # Try with different encoding and separator
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', sep=',')
                except Exception as csv_error2:
                    print(f"Error reading CSV with utf-8 encoding: {csv_error2}")
                    # Try with latin-1 encoding
                    df = pd.read_csv(file_path, encoding='latin-1', sep=',')
        elif file_id.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_id}")
            
        vendor_headers = list(df.columns)
        print("vendor_headers: ", vendor_headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # 3. Define the fixed JC headers
    target_headers = [
        "RetailerStockNumber", "StyleNumber", "VisibleAs", "ParentSKU", "ProductType",
        "SelectedAttributes", "ProductName", "ProductDescription", "CustomAttribute",
        "CustomAttributeLabel", "ConfigurableControlType", "IsConfigurableProduct",
        "ControlDisplayOrder", "Categories", "Collections", "PriceType",
        "WholesaleBasePrice", "MSRP", "MetalType", "MetalColor", "ImagePath", "Gender"
    ]
    print("target_headers: ", target_headers)
    
    # load agent
    try:
        from agents import Agent, Runner
        from pydantic import BaseModel
        from typing import List
        print("Successfully imported openai_agents")
    except ImportError as e:
        print(f"Error importing openai_agents: {e}")
        raise HTTPException(
            status_code=500, 
            detail="AI agents module not available. Please install openai-agents package."
        )
    
    class FieldMapping(BaseModel):
        vendor_field: str
        confidence: float

    print("FieldMapping class defined successfully")

    class MappingItem(BaseModel):
        RetailerStockNumber: FieldMapping
        StyleNumber: FieldMapping
        VisibleAs: FieldMapping
        ParentSKU: FieldMapping
        ProductType: FieldMapping
        SelectedAttributes: FieldMapping
        ProductName: FieldMapping
        ProductDescription: FieldMapping
        CustomAttribute: FieldMapping
        CustomAttributeLabel: FieldMapping
        ConfigurableControlType: FieldMapping
        IsConfigurableProduct: FieldMapping
        ControlDisplayOrder: FieldMapping
        Categories: FieldMapping
        Collections: FieldMapping
        PriceType: FieldMapping
        WholesaleBasePrice: FieldMapping
        MSRP: FieldMapping
        MetalType: FieldMapping
        MetalColor: FieldMapping
        ImagePath: FieldMapping
        Gender: FieldMapping
        other_fields: List[FieldMapping]

    class OutputModel(BaseModel):
        items: List[MappingItem]
    print("vendor_headers: ", vendor_headers)
    agent = Agent(
        name="Header Mapper",
        instructions=(
            "You are an expert in mapping vendor file headers to a fixed JC format. "
            "Given a list of vendor headers and a list of target JC headers, "
            "suggest the best mapping between them. "
            "Return a list of objects with 'vendor_field', 'jc_field', and a confidence score between 0 and 1. "
            "If a vendor header does not match any JC header, leave 'jc_field' as null."
        ),
        
        output_type=OutputModel
    )
    print("agent: ", agent)
    prompt = (
        f"Vendor headers: {vendor_headers}\n"
        f"JC headers: {target_headers}\n"
        "Map each vendor header to the most appropriate JC header. "
        "Return only a JSON list of objects with 'vendor_field', 'jc_field', and 'confidence'."
    )
    response = await Runner.run(agent, prompt)
    print("response final output :", response.final_output)
    print("response  :", response)
    
    # Save AI response to Pinecone
    try:
        pinecone_result = upsert_mapping_data_to_pinecone(
            ai_response=response.final_output.dict(),
            file_id=file_id,
            client_number=client_number
        )
        print("Pinecone upsert result:", pinecone_result)
    except Exception as e:
        print(f"Warning: Failed to save to Pinecone: {e}")
        pinecone_result = {"success": False, "error": str(e)}
    
    try:
         file_name_output = generate_result_with_watch_data(response.final_output.dict(), file_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}. Raw response: {response}")
    
    return {
        "file_id": file_name_output,
        "message": "AI suggested mappings generated successfully",
        "response": response.final_output,
        "pinecone_saved": pinecone_result.get("success", False),
        "pinecone_id": pinecone_result.get("mapping_id") if pinecone_result.get("success") else None,
        "pinecone_message": pinecone_result.get("message", "Failed to save to Pinecone")
    }


@router.get("/mapping/history/{client_number}")
def get_mapping_history(
    client_number: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Retrieve last 10 mappings for a client.
    """
    mappings = db.query(Mapping).filter(
        Mapping.client_number == client_number
    ).order_by(
        Mapping.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "client_number": client_number,
        "mappings": [
            {
                "mapping_id": str(mapping.mapping_id),
                "vendor_field": mapping.vendor_field,
                "jc_field": mapping.jc_field,
                "confidence": mapping.confidence,
                "mapping_type": mapping.mapping_type,
                "created_at": mapping.created_at
            }
            for mapping in mappings
        ],
        "total": len(mappings)
    }


@router.post("/mapping/save")
async def save_mappings(
    file_id: str = Form(...),
    mappings: str = Form(...),  # JSON string of mappings
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Save AI or manual mappings.
    """
    try:
        file_uuid = uuid.UUID(file_id)
        mappings_data = json.loads(mappings)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data format: {str(e)}"
        )
    
    saved_mappings = []
    for mapping_data in mappings_data:
        mapping = Mapping(
            file_id=file_uuid,
            client_number=mapping_data.get("client_number"),
            vendor_field=mapping_data["vendor_field"],
            jc_field=mapping_data["jc_field"],
            confidence=mapping_data.get("confidence"),
            mapping_type=mapping_data.get("mapping_type", "manual")
        )
        db.add(mapping)
        saved_mappings.append(mapping)
    
    db.commit()
    
    # Optionally save to Pinecone as well
    pinecone_result = None
    try:
        # Create a simplified AI response format for manual mappings
        manual_mapping_data = {
            "items": [{
                "mapping_type": "manual",
                "mappings": mappings_data
            }]
        }
        
        pinecone_result = upsert_mapping_data_to_pinecone(
            ai_response=manual_mapping_data,
            file_id=file_id,
            client_number=mappings_data[0].get("client_number") if mappings_data else None
        )
        print("Pinecone upsert result for manual mappings:", pinecone_result)
    except Exception as e:
        print(f"Warning: Failed to save manual mappings to Pinecone: {e}")
        pinecone_result = {"success": False, "error": str(e)}
    
    return {
        "file_id": file_id,
        "saved_count": len(saved_mappings),
        "message": "Mappings saved successfully",
        "pinecone_saved": pinecone_result.get("success", False) if pinecone_result else False,
        "pinecone_id": pinecone_result.get("mapping_id") if pinecone_result and pinecone_result.get("success") else None,
        "pinecone_message": pinecone_result.get("message", "Failed to save to Pinecone") if pinecone_result else "Not attempted"
    }


@router.delete("/mapping/{client_number}")
def delete_mappings(
    client_number: str,
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete specific mappings for a client.
    """
    deleted_count = db.query(Mapping).filter(
        Mapping.client_number == client_number
    ).delete()
    
    db.commit()
    
    return {
        "client_number": client_number,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} mappings"
    }

# ============================================================================
# PRODUCT CONFIGURATION ENDPOINTS
# ============================================================================

@router.post("/product/configure")
async def configure_products(
    file_id: str = Form(...),
    configuration_fields: str = Form(...),  # JSON string of fields to group by
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Generate configurable product trees (parent-child SKUs).
    """
    try:
        file_uuid = uuid.UUID(file_id)
        config_fields = json.loads(configuration_fields)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data format: {str(e)}"
        )
    
    # TODO: Implement product configuration logic
    # This is a placeholder implementation
    
    mock_products = [
        {
            "parent_sku": "PROD-001",
            "child_skus": ["PROD-001-001", "PROD-001-002"],
            "configuration_fields": ["MetalType", "MetalColor"],
            "variant_count": 2
        }
    ]
    
    return {
        "file_id": file_id,
        "configured_products": mock_products,
        "message": "Products configured successfully"
    }

# ============================================================================
# PINECONE SEARCH ENDPOINTS
# ============================================================================

@router.get("/mapping/search")
def search_mappings_in_pinecone(
    query: str = Query(..., description="Search query for mapping data"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results to return"),
    client_number: str = Query(None, description="Filter by client number")
) -> Any:
    """
    Search for mapping data in Pinecone index.
    """
    try:
        search_result = search_mapping_data(
            query_text=query,
            top_k=top_k,
            client_number=client_number
        )
        
        if search_result["success"]:
            return {
                "success": True,
                "query": query,
                "results": search_result["results"],
                "total_found": search_result["total_found"],
                "message": f"Found {search_result['total_found']} matching mappings"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Search failed: {search_result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching mappings: {str(e)}"
        )


@router.delete("/mapping/pinecone/{mapping_id}")
def delete_mapping_from_pinecone(
    mapping_id: str,
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete mapping data from Pinecone index.
    """
    try:
        delete_result = delete_mapping_data(mapping_id=mapping_id)
        
        if delete_result["success"]:
            return {
                "success": True,
                "mapping_id": mapping_id,
                "message": delete_result["message"]
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Delete failed: {delete_result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting mapping: {str(e)}"
        )
