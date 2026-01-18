"""
Financial Text Extractor for parsing banking statements and financial documents.

This module extracts structured banking transaction data from various document formats
(PDF, Excel, etc.) and returns data matching the statement_banking_transaction schema.

**NOTE:** Clearning needed to remove PyPDF2 dependency. Should just feed PDFs/Documents to OpenAI.
"""

import io
import os
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Literal

from openai import OpenAI, AsyncOpenAI

import pandas as pd

# Try to import settings, with fallback for when running as script
try:
    from backend.config import settings
    from backend.schemas.transaction_category import FinancialTransactionCategory
except ImportError:
    # If running as script, add parent directory to path
    import sys
    from pathlib import Path
    # File is at: apps/backend/services/document_parser/financial_text_extractor.py
    # Need to add apps/ to path so backend can be imported
    apps_dir = Path(__file__).parent.parent.parent.parent  # Go up to apps/
    if str(apps_dir) not in sys.path:
        sys.path.insert(0, str(apps_dir))
    from backend.config import settings
    from backend.schemas.transaction_category import FinancialTransactionCategory


class FinancialTextExtractor:
    """Extracts structured banking transaction data from financial documents."""
    
    def __init__(self):
        """Initialize the extractor with OpenAI client."""
        # Use settings if available, otherwise fall back to environment variable
        api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or config")
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)
    
    async def extract_from_file(
        self,
        file_path: str | Path | None = None,
        file_content: bytes | None = None,
        file_mime_type: str | None = None,
        user_upload_id: str | None = None,
        backend: Literal["pypdf2", "openai"] = "openai",
    ) -> List[Dict[str, Any]]:
        """
        Extract banking transactions from a file.
        
        Args:
            file_path: Path to the file (or filename if file_content provided)
            file_content: Optional file content as bytes
            file_mime_type: MIME type of the file (e.g., 'application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            user_upload_id: Optional user upload ID to associate with transactions
            backend: Backend to use for extraction. Either "pypdf2" or "openai". For "openai", the text extraction is done by OpenAI. For "pypdf2", the text extraction is done by pypdf2.
        Returns:
            List of transaction dictionaries matching the statement_banking_transaction schema
        """
        # Determine file type
        if file_mime_type:
            mime_type = file_mime_type
        elif file_content is None:
            mime_type = self._get_mime_type_from_path(file_path)
        else:
            mime_type = self._get_mime_type_from_path(file_path)
        
        if backend == "pypdf2":
            # Extract text/data from file
            if 'pdf' in mime_type.lower():
                text_content = self._extract_from_pdf(file_path, file_content)
            elif 'excel' in mime_type.lower() or 'spreadsheet' in mime_type.lower() or \
                file_path.suffix.lower() in ['.xlsx', '.xls'] if isinstance(file_path, Path) else \
                str(file_path).lower().endswith(('.xlsx', '.xls')):
                text_content = self._extract_from_excel(file_path, file_content)
            else:
                # Try to extract as text
                text_content = self._extract_as_text(file_path, file_content)
            
            # Use OpenAI to extract structured data
            transactions = await self._extract_structured_data_using_pypdf2(text_content, user_upload_id)
        else:
            # Use OpenAI to extract structured data
            transactions = await self._extract_structured_data_using_openai(file_path, file_content, mime_type, user_upload_id=user_upload_id)
        return transactions
    
    def _get_mime_type_from_path(self, file_path: str | Path) -> str:
        """Infer MIME type from file extension."""
        path = Path(file_path) if isinstance(file_path, str) else file_path
        suffix = path.suffix.lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
        }
        
        return mime_types.get(suffix, 'application/octet-stream')
    
    def _extract_from_pdf(self, file_path: str | Path, file_content: bytes | None = None) -> str:
        """
        Extract text content from PDF file.
        
        Note: This is a basic implementation. For production, consider using
        pdfplumber or PyMuPDF for better extraction.
        """
        try:
            # Try using pdfplumber first (better for tables)
            import pdfplumber
            text_parts = []
            
            if file_content:
                pdf_file = io.BytesIO(file_content)
            else:
                pdf_file = open(file_path, 'rb')
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    # Extract text
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                    
                    # Try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            # Convert table to text representation
                            table_text = '\n'.join([' | '.join(str(cell) if cell else '' for cell in row) for row in table])
                            text_parts.append(table_text)
            
            if not isinstance(file_content, bytes):
                pdf_file.close()
            
            return '\n\n'.join(text_parts)
        except ImportError:
            # Fallback to PyPDF2 if pdfplumber not available
            try:
                import PyPDF2
                text_parts = []
                
                if file_content:
                    pdf_file = io.BytesIO(file_content)
                else:
                    pdf_file = open(file_path, 'rb')
                
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                if not isinstance(file_content, bytes):
                    pdf_file.close()
                
                return '\n\n'.join(text_parts)
            except ImportError:
                raise ImportError(
                    "PDF extraction requires either 'pdfplumber' or 'PyPDF2'. "
                    "Install with: pip install pdfplumber or pip install PyPDF2"
                )
    
    def _extract_from_excel(self, file_path: str | Path, file_content: bytes | None = None) -> str:
        """Extract text content from Excel file."""
        try:
            if file_content:
                excel_file = io.BytesIO(file_content)
            else:
                excel_file = file_path
            
            # Read all sheets
            excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
            
            text_parts = []
            for sheet_name, df in excel_data.items():
                text_parts.append(f"Sheet: {sheet_name}")
                text_parts.append(df.to_string())
                text_parts.append("")  # Empty line between sheets
            
            return '\n'.join(text_parts)
        except ImportError:
            raise ImportError(
                "Excel extraction requires 'openpyxl'. Install with: pip install openpyxl"
            )
        except Exception as e:
            # Fallback: try reading as CSV or basic text
            try:
                if file_content:
                    text = file_content.decode('utf-8', errors='ignore')
                else:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                return text
            except Exception:
                raise ValueError(f"Failed to extract from Excel file: {str(e)}")
    
    def _extract_as_text(self, file_path: str | Path, file_content: bytes | None = None) -> str:
        """Extract text from plain text files."""
        if file_content:
            return file_content.decode('utf-8', errors='ignore')
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    
    async def _extract_structured_data_using_pypdf2(
        self, 
        text_content: str, 
        user_upload_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Uses pypdf2 to extract text from the file and then uses OpenAI to extract structured banking transaction data from text.
        
        Returns a list of transaction dictionaries matching the schema.
        """
        # Get valid category values from enum
        valid_categories = [cat.value for cat in FinancialTransactionCategory]
        categories_list = ", ".join([f"'{cat}'" for cat in valid_categories])
        
        system_prompt = f"""You are a Malaysian financial data extraction expert specializing in Malaysian bank statements.
        Extract all banking transactions from the provided text and return them as a JSON array.

        For each transaction, extract the following fields:
        - transaction_date: Date in YYYY-MM-DD format
        - description: Full transaction description
        - merchant_name: Extracted merchant/vendor name (if available)
        - amount: Transaction amount as a decimal number (always positive)
        - transaction_type: Either 'debit' (money going out) or 'credit' (money coming in)
        - balance: Account balance after transaction (if available)
        - reference_number: Transaction reference number (if available)
        - transaction_code: Bank transaction code (if available)
        - category: Transaction category - MUST be one of the following valid values: {categories_list}. Use 'other' if the transaction doesn't fit any specific category.
        - currency: Currency code (default to 'MYR' for Malaysian Ringgit)
        - is_subscription: Whether the transaction is a subscription/membership (likely to recur monthly) e.g., Netflix, Spotify, Apple Music, gym membership, etc.

        Important rules:
        1. Parse dates in various formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc.) and convert to YYYY-MM-DD
        2. Amounts should always be positive numbers
        3. Determine transaction_type based on context:
        - Debit: Payments, purchases, withdrawals, transfers out
        - Credit: Deposits, salary, refunds, transfers in
        4. Extract merchant_name from description when possible
        5. Use merchant_name and description to determine the category if possible.
        6. If balance is not provided, set to null
        7. If any optional field is not available, set to null
        8. Category field MUST use one of the valid category values listed above. Map common transaction types as follows:
        - Income/salary/deposits → 'income'
        - Transfers or TRANSFER FROM A/C → 'cash_transfer'
        - Rent/mortgage/housing → 'housing'
        - Petrol/taxi/public transport/car payments/Grab/Gojek → 'transportation'
        - Restaurants/cafes/food delivery/makan → 'food_and_dining_out'
        - Movies/games/events/hobbies/GSC/TGV → 'entertainment'
        - Medical/dental/pharmacy → 'healthcare'
        - School/tuition/books/courses/SPM/STPM/sekolah → 'education'
        - Electricity/water/internet/phone bills → 'utilities'
        - Investments/savings/stocks/ETFs/Unit Trusts/KLCI/Pacific Trustees/ASB/Amanah Saham → 'investments_and_savings'
        - Technology/electronics/gadgets/Apple/Samsung/Google/Microsoft/smartphone → 'technology_and_electronics'
        - Supermarket/grocery stores/pasar → 'groceries'
        - Gym/sports/fitness/club memberships → 'sport_and_activity'
        - Anything else → 'other'

        Return ONLY valid JSON array, no additional text or markdown formatting."""

        user_prompt = f"""Extract all banking transactions from the following text:

        {text_content}

        Return a JSON object with a "transactions" key containing an array of transaction objects with the fields specified above."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-4-turbo-preview" for better structured extraction
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent extraction
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Try to extract JSON from the response
            # Sometimes OpenAI wraps it in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            try:
                data = json.loads(content)
                # Handle both {"transactions": [...]} and [...] formats
                if isinstance(data, dict) and "transactions" in data:
                    transactions = data["transactions"]
                elif isinstance(data, list):
                    transactions = data
                elif isinstance(data, dict):
                    # Try to find any array value in the dict
                    transactions = next((v for v in data.values() if isinstance(v, list)), [])
                else:
                    transactions = []
            except json.JSONDecodeError:
                # Try to find JSON array in the text
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    transactions = json.loads(json_match.group())
                else:
                    raise ValueError(f"Failed to parse JSON from OpenAI response: {content}")
            
            # Transform to match database schema
            structured_transactions = []
            for tx in transactions:
                structured_tx = self._transform_transaction(tx, user_upload_id)
                if structured_tx:
                    structured_transactions.append(structured_tx)
            
            return structured_transactions
            
        except Exception as e:
            raise ValueError(f"Failed to extract structured data: {str(e)}")

    async def _extract_structured_data_using_openai(
        self, 
        file_path: str | Path | None = None,
        file_content: bytes | None = None,
        file_mime_type: str | None = None,
        user_upload_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Uses OpenAI to extract structured banking transaction data from file.
        For PDFs, splits into 2-page chunks and processes them in parallel.
        
        Returns a list of transaction dictionaries matching the schema.
        """
        # Get valid category values from enum
        valid_categories = [cat.value for cat in FinancialTransactionCategory]
        categories_list = ", ".join([f"'{cat}'" for cat in valid_categories])
        
        system_prompt = f"""You are a Malaysian financial data extraction expert specializing in Malaysian bank statements.
        Extract all banking transactions from the provided text and return them as a JSON array.

        For each transaction, extract the following fields:
        - transaction_date: Date in YYYY-MM-DD format
        - description: Full transaction description
        - merchant_name: Extracted merchant/vendor name (if available)
        - amount: Transaction amount as a decimal number (always positive)
        - transaction_type: Either 'debit' (money going out) or 'credit' (money coming in)
        - balance: Account balance after transaction (if available)
        - reference_number: Transaction reference number (if available)
        - transaction_code: Bank transaction code (if available)
        - category: Transaction category - MUST be one of the following valid values: {categories_list}. Use 'other' if the transaction doesn't fit any specific category.
        - currency: Currency code (default to 'MYR' for Malaysian Ringgit)
        - is_subscription: Whether the transaction is a subscription/membership (likely to recur monthly) e.g., Netflix, Spotify, Apple Music, gym membership, etc.

        Important rules:
        1. Parse dates in various formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc.) and convert to YYYY-MM-DD
        2. Amounts should always be positive numbers
        3. Determine transaction_type based on context:
        - Debit: Payments, purchases, withdrawals, transfers out
        - Credit: Deposits, salary, refunds, transfers in
        4. Extract merchant_name from description when possible
        5. Use merchant_name and description to determine the category if possible.
        6. If balance is not provided, set to null
        7. If any optional field is not available, set to null
        8. Category field MUST use one of the valid category values listed above. Map common transaction types as follows:
        - Income/salary/deposits → 'income'
        - Transfers or TRANSFER FROM A/C → 'cash_transfer'
        - Rent/mortgage/housing → 'housing'
        - Petrol/taxi/public transport/car payments/Grab/Gojek → 'transportation'
        - Restaurants/cafes/food delivery/makan → 'food_and_dining_out'
        - Movies/games/events/hobbies/GSC/TGV → 'entertainment'
        - Medical/dental/pharmacy → 'healthcare'
        - School/tuition/books/courses/SPM/STPM/sekolah → 'education'
        - Electricity/water/internet/phone bills → 'utilities'
        - Investments/savings/stocks/ETFs/Unit Trusts/KLCI/Pacific Trustees/ASB/Amanah Saham → 'investments_and_savings'
        - Technology/electronics/gadgets/Apple/Samsung/Google/Microsoft/smartphone → 'technology_and_electronics'
        - Supermarket/grocery stores/pasar → 'groceries'
        - Gym/sports/fitness/club memberships → 'sport_and_activity'
        - Anything else → 'other'

        Return ONLY valid JSON array, no additional text or markdown formatting."""

        user_prompt = f"""Extract all banking transactions from the following file. Return a JSON object with a "transactions" key containing an array of transaction objects with the fields specified above."""

        # Ensure we have file_content
        if file_path and file_content is None:
            with open(file_path, "rb") as f:
                file_content = f.read()
        
        if file_content is None:
            raise ValueError("Either file_path or file_content must be provided")
        
        try:
            # If PDF, split into 2-page chunks and process in parallel
            if file_mime_type and 'pdf' in file_mime_type.lower():
                # Split PDF into 2-page chunks
                import PyPDF2
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                
                chunks = []
                for start_page in range(0, total_pages, 2):
                    end_page = min(start_page + 2, total_pages)
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                    chunk_buffer = io.BytesIO()
                    pdf_writer.write(chunk_buffer)
                    chunks.append(chunk_buffer.getvalue())
                    chunk_buffer.close()
                pdf_file.close()
                
                # Process chunks in parallel
                async def process_chunk(chunk_content):
                    response = await self.async_client.responses.create(
                        model="gpt-4o-mini",
                        input=[
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": user_prompt
                                    },
                                    {
                                        "type": "input_file", 
                                        "filename": "financial_document",
                                        "file_data": f"data:{file_mime_type};base64,{base64.b64encode(chunk_content).decode('utf-8')}"
                                    }
                                ]
                            }
                        ],
                        temperature=0.1,
                    )
                    return response.output_text
                
                # Run all chunks in parallel
                tasks = [process_chunk(chunk) for chunk in chunks]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Parse all responses and combine transactions
                all_transactions = []
                for i, content in enumerate(responses):
                    if isinstance(content, Exception):
                        print(f"Error processing chunk {i+1}: {str(content)}")
                        continue
                    
                    # Try to extract JSON from the response
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    
                    # Parse JSON
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict) and "transactions" in data:
                            transactions = data["transactions"]
                        elif isinstance(data, list):
                            transactions = data
                        elif isinstance(data, dict):
                            transactions = next((v for v in data.values() if isinstance(v, list)), [])
                        else:
                            transactions = []
                    except json.JSONDecodeError:
                        import re
                        json_match = re.search(r'\[.*\]', content, re.DOTALL)
                        if json_match:
                            transactions = json.loads(json_match.group())
                        else:
                            print(f"Failed to parse JSON from chunk {i+1}: {content}")
                            continue
                    
                    all_transactions.extend(transactions)
                
                # Transform to match database schema
                structured_transactions = []
                for tx in all_transactions:
                    structured_tx = self._transform_transaction(tx, user_upload_id)
                    if structured_tx:
                        structured_transactions.append(structured_tx)
                
                return structured_transactions
            
            # For non-PDF files, use the original synchronous approach
            response = self.client.responses.create(
                model="gpt-4o-mini",  # or "gpt-4-turbo-preview" for better structured extraction
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_prompt
                            },
                            {
                                "type": "input_file", 
                                "filename": "financial_document",
                                "file_data": f"data:{file_mime_type};base64,{base64.b64encode(file_content).decode('utf-8')}"
                            }
                        ]
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
            )
            
            # Parse the response
            content = response.output_text
            
            # Try to extract JSON from the response
            # Sometimes OpenAI wraps it in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            try:
                data = json.loads(content)
                # Handle both {"transactions": [...]} and [...] formats
                if isinstance(data, dict) and "transactions" in data:
                    transactions = data["transactions"]
                elif isinstance(data, list):
                    transactions = data
                elif isinstance(data, dict):
                    # Try to find any array value in the dict
                    transactions = next((v for v in data.values() if isinstance(v, list)), [])
                else:
                    transactions = []
            except json.JSONDecodeError:
                # Try to find JSON array in the text
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    transactions = json.loads(json_match.group())
                else:
                    raise ValueError(f"Failed to parse JSON from OpenAI response: {content}")
            
            # Transform to match database schema
            structured_transactions = []
            for tx in transactions:
                structured_tx = self._transform_transaction(tx, user_upload_id)
                if structured_tx:
                    structured_transactions.append(structured_tx)
            
            return structured_transactions
            
        except Exception as e:
            raise ValueError(f"Failed to extract structured data: {str(e)}")
    
    def _transform_transaction(
        self, 
        transaction: Dict[str, Any], 
        user_upload_id: str | None = None,
    ) -> Dict[str, Any] | None:
        """
        Transform extracted transaction to match database schema.
        
        Schema fields:
        - id: TEXT PRIMARY KEY
        - user_upload_id: TEXT NOT NULL
        - transaction_date: DATE NOT NULL
        - transaction_year: INTEGER NOT NULL
        - transaction_month: INTEGER NOT NULL
        - transaction_day: INTEGER NOT NULL
        - description: TEXT NOT NULL
        - merchant_name: TEXT
        - amount: DECIMAL(15, 2) NOT NULL
        - transaction_type: TEXT NOT NULL ('debit' or 'credit')
        - balance: DECIMAL(15, 2)
        - reference_number: TEXT
        - transaction_code: TEXT
        - category: TEXT
        - currency: TEXT NOT NULL DEFAULT 'MYR'
        - is_subscription: BOOLEAN NOT NULL DEFAULT FALSE
        """
        try:
            # Parse date
            date_str = transaction.get('transaction_date', '')
            if not date_str:
                return None
            
            # Parse date in various formats
            transaction_date = self._parse_date(date_str)
            if not transaction_date:
                return None
            
            # Extract date components
            transaction_year = transaction_date.year
            transaction_month = transaction_date.month
            transaction_day = transaction_date.day
            
            # Get required fields
            description = transaction.get('description', '').strip()
            if not description:
                return None
            
            amount = float(transaction.get('amount', 0))
            if amount <= 0:
                return None
            
            transaction_type = transaction.get('transaction_type', '').lower()
            if transaction_type not in ['debit', 'credit']:
                # Try to infer from context
                transaction_type = 'debit'  # Default to debit
            
            # Get optional fields
            merchant_name = transaction.get('merchant_name')
            if merchant_name:
                merchant_name = merchant_name.strip() or None
            
            balance = transaction.get('balance')
            if balance is not None:
                try:
                    balance = float(balance)
                except (ValueError, TypeError):
                    balance = None
            
            reference_number = transaction.get('reference_number')
            if reference_number:
                reference_number = str(reference_number).strip() or None
            
            transaction_code = transaction.get('transaction_code')
            if transaction_code:
                transaction_code = str(transaction_code).strip() or None
            
            category = transaction.get('category')
            if category:
                category = str(category).strip().lower()
                # Validate category against enum values
                valid_categories = [cat.value for cat in FinancialTransactionCategory]
                if category not in valid_categories:
                    # Try to find a close match or default to 'other'
                    # Normalize common variations
                    category_mapping = {
                        'food': 'food_and_dining_out',
                        'dining': 'food_and_dining_out',
                        'restaurant': 'food_and_dining_out',
                        'transport': 'transportation',
                        'travel': 'transportation',
                        'bills': 'utilities',
                        'utilities': 'utilities',
                        'shopping': 'other',
                        'retail': 'other',
                    }
                    category = category_mapping.get(category, 'other')
                category = category if category in valid_categories else None
            else:
                category = None
            
            currency = transaction.get('currency', 'MYR').strip().upper() or 'MYR'

            is_subscription = transaction.get('is_subscription', False)
            
            return {
                'user_upload_id': user_upload_id or '',
                'transaction_date': transaction_date.strftime('%Y-%m-%d'),
                'transaction_year': transaction_year,
                'transaction_month': transaction_month,
                'transaction_day': transaction_day,
                'description': description,
                'merchant_name': merchant_name,
                'amount': round(amount, 2),
                'transaction_type': transaction_type,
                'balance': round(balance, 2) if balance is not None else None,
                'reference_number': reference_number,
                'transaction_code': transaction_code,
                'category': category,
                'currency': currency,
                'is_subscription': is_subscription,
            }
        except Exception as e:
            # Log error but don't fail completely
            print(f"Error transforming transaction: {str(e)}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string in various formats."""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d.%m.%Y',
            '%Y/%m/%d',
            '%d %b %Y',
            '%d %B %Y',
            '%b %d, %Y',
            '%B %d, %Y',
            '%d-%b-%Y',
            '%d-%B-%Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try pandas parsing as fallback
        try:
            return pd.to_datetime(date_str).to_pydatetime()
        except Exception:
            pass
        
        return None


# Convenience function for easy usage
async def extract_banking_transactions(
    file_path: str | Path | None = None,
    file_content: bytes | None = None,
    file_mime_type: str | None = None,
    user_upload_id: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract banking transactions from a file.
    
    Args:
        file_path: Path to the file (or filename if file_content provided)
        file_content: Optional file content as bytes
        file_mime_type: MIME type of the file
        user_upload_id: Optional user upload ID to associate with transactions
        
    Returns:
        List of transaction dictionaries matching the statement_banking_transaction schema
    """
    extractor = FinancialTextExtractor()
    return await extractor.extract_from_file(
        file_path=file_path,
        file_content=file_content,
        file_mime_type=file_mime_type,
        user_upload_id=user_upload_id,
    )

if __name__ == "__main__":
    from pprint import pprint
    
    file_path = Path(__file__).parent.parent.parent.parent.parent / "datasets" / "banking_transactions" / "Bank Statement Example Final.pdf"
    assert file_path.exists(), f"File with file path {file_path} does not exist"

    file_content = file_path.read_bytes()

    extractor = FinancialTextExtractor()
    transactions = extractor.extract_from_file(
        file_path=None,
        file_content=file_content,
        file_mime_type="application/pdf",
        user_upload_id="1234567890",
        backend="openai", # or "pypdf2"
    )
    pprint(transactions)
