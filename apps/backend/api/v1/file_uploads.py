"""File upload endpoints for handling user file uploads and processing."""

import uuid
from datetime import date, datetime as dt
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.user_upload import UserUpload
from backend.models.banking_transaction import BankingTransaction
from backend.services.db.postgres_connector import database_service
from backend.services.object_store.minio_connector import get_minio_connector
from backend.services.document_parser.financial_text_extractor import extract_banking_transactions
from backend.services.ai_agent.transaction_analyzer import transaction_analyzer

router = APIRouter()
minio_connector = get_minio_connector()


@router.post("/upload", tags=["File Uploads"])
async def upload_file(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    statement_type: str = Query(default="banking_transaction", regex="^(banking_transaction|receipt|invoice|other)$"),
    expense_month: Optional[int] = Query(default=None, ge=1, le=12),
    expense_year: Optional[int] = Query(default=None),
) -> dict:
    """Upload one or more files and process them to extract banking transactions.
    
    Args:
    files: The files to upload
        current_user: Authenticated user (from Clerk JWT)
        statement_type: Type of statement (banking_transaction, receipt, invoice, other)
        expense_month: Month of the expense (1-12), defaults to current month
        expense_year: Year of the expense, defaults to current year
        
    Returns:
    - Dictionary with upload details and extracted transaction count
    """
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per file

    user_id = current_user.id
    try:
        # Set default expense month/year if not provided
        if expense_month is None:
            expense_month = date.today().month
        if expense_year is None:
            expense_year = date.today().year

        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        results = []
        total_transactions_extracted = 0

        for file in files:
            if file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail=f"Only PDF files are allowed. Got: {file.content_type} for {file.filename}")

            # Read file content and validate size
            file_content = await file.read()
            file_size = len(file_content)
            if file_size > MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=400, detail=f"File size must be less than 10MB. File '{file.filename}' is {file_size} bytes")

            # Generate unique file ID
            file_id = str(uuid.uuid4())

            # Determine file extension and MIME type
            file_extension = Path(file.filename).suffix.lstrip('.') if file.filename else ''
            file_mime_type = file.content_type or "application/octet-stream"

            # Upload file to MinIO
            file_data_io = BytesIO(file_content)
            upload_result = minio_connector.upload_file(
                user_id=user_id,
                document_id=file_id,
                file_data=file_data_io,
                file_name=file.filename or "unknown",
                content_type=file_mime_type,
                file_size=file_size
            )

            # Create user upload record in database
            user_upload = UserUpload(
                file_id=file_id,
                user_id=user_id,
                file_name=file.filename or "unknown",
                file_type=file_extension or "unknown",
                file_size=file_size,
                file_url=upload_result.get("file_url", ""),
                file_mime_type=file_mime_type,
                file_extension=file_extension,
                statement_type=statement_type,
                expense_month=expense_month,
                expense_year=expense_year,
            )
            database_service.create_user_upload(user_upload)

            # Extract transactions if it's a banking transaction statement
            transaction_count = 0
            if statement_type == "banking_transaction":
                try:
                    transactions_data = await extract_banking_transactions(
                        file_path=None,
                        file_content=file_content,
                        file_mime_type=file_mime_type,
                        user_upload_id=file_id
                    )

                    banking_transactions = []
                    for idx, tx_data in enumerate(transactions_data):
                        tx_id = f"{file_id}_{idx}"
                        tx_date = dt.strptime(tx_data['transaction_date'], '%Y-%m-%d').date()

                        banking_tx = BankingTransaction(
                            id=tx_id,
                            user_id=user_id,
                            file_id=file_id,
                            transaction_date=tx_date,
                            transaction_year=tx_data['transaction_year'],
                            transaction_month=tx_data['transaction_month'],
                            transaction_day=tx_data['transaction_day'],
                            description=tx_data['description'],
                            merchant_name=tx_data.get('merchant_name'),
                            amount=Decimal(str(tx_data['amount'])),
                            is_subscription=tx_data.get('is_subscription', False),
                            transaction_type=tx_data['transaction_type'],
                            balance=Decimal(str(tx_data['balance'])) if tx_data.get('balance') else None,
                            reference_number=tx_data.get('reference_number'),
                            transaction_code=tx_data.get('transaction_code'),
                            category=tx_data.get('category'),
                            currency=tx_data.get('currency', 'MYR'),
                        )
                        banking_transactions.append(banking_tx)

                    if banking_transactions:
                        database_service.create_banking_transactions_bulk(banking_transactions)
                        transaction_count = len(banking_transactions)
                        total_transactions_extracted += transaction_count

                        try:
                            transaction_analyzer.analyze(
                                user_id=user_id,
                                file_id=file_id,
                                transactions=banking_transactions,
                            )
                        except Exception as analysis_error:
                            print(f"Error running AI analysis: {str(analysis_error)}")

                except Exception as e:
                    print(f"Error extracting transactions for {file.filename}: {str(e)}")

            results.append({
                "file_id": file_id,
                "file_name": file.filename,
                "file_size": file_size,
                "file_url": upload_result.get("file_url", ""),
                "statement_type": statement_type,
                "transactions_extracted": transaction_count,
                "insights_generated": transaction_count > 0,
            })

        return {
            "files": results,
            "count": len(results),
            "transactions_extracted_total": total_transactions_extracted,
            "insights_generated": total_transactions_extracted > 0,
            "message": "Files uploaded and processed successfully",
        }
        
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", tags=["File Uploads"])
async def list_user_uploads(
    current_user: User = Depends(get_current_user),
    limit: Optional[int] = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="created_at"),
    order_desc: bool = Query(default=True),
) -> dict:
    """List all user uploads with pagination.
    
    Args:
        current_user: Authenticated user (from Clerk JWT)
        limit: Maximum number of results (1-100)
        offset: Number of results to skip
        order_by: Field to order by
        order_desc: Order descending if True, ascending if False
        
    Returns:
    - Dictionary with uploads list and pagination info
    """
    user_id = current_user.id
    uploads = database_service.get_user_uploads(
        user_id=user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_desc=order_desc,
    )
    
    return {
        "uploads": [
            {
                "file_id": upload.file_id,
                "file_name": upload.file_name,
                "file_type": upload.file_type,
                "file_size": upload.file_size,
                "file_url": upload.file_url,
                "statement_type": upload.statement_type,
                "expense_month": upload.expense_month,
                "expense_year": upload.expense_year,
                "created_at": upload.created_at.isoformat() if upload.created_at else None,
            }
            for upload in uploads
        ],
        "count": len(uploads),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{file_id}/download", tags=["File Uploads"])
async def download_user_upload(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download a user upload file.
    
    Args:
        file_id: File ID to download
        current_user: Authenticated user (from Clerk JWT)
        
    Returns:
    - StreamingResponse with file content
    """
    user_id = current_user.id
    # Get user upload to verify ownership
    uploads = database_service.get_user_uploads(user_id=user_id)
    upload = next((u for u in uploads if u.file_id == file_id), None)
    
    if not upload:
        raise HTTPException(status_code=404, detail="File not found or access denied")
    
    try:
        # Download file from MinIO
        file_data_io = minio_connector.download_file(
            user_id=user_id,
            document_id=file_id
        )
        
        # Read bytes from BytesIO
        file_data_io.seek(0)
        file_bytes = file_data_io.read()
        
        # Determine content type
        content_type = upload.file_mime_type or "application/octet-stream"
        
        return StreamingResponse(
            BytesIO(file_bytes),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{upload.file_name}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
