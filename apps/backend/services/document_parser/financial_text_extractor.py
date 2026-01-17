"""
Financial Text Extractor for parsing banking statements and financial documents.

This module extracts structured banking transaction data from various document formats
(PDF, Excel, etc.) and returns data matching the statement_banking_transaction schema.
"""

import io
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

import openai
import pandas as pd
from openai import OpenAI

from backend.config import settings

class FinancialTextExtractor:
    """Extracts structured banking transaction data from financial documents."""
    
    def __init__(self):
        """Initialize the extractor with OpenAI client."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def extract_from_file(
        self, 
        file_path: str | Path, 
        file_content: bytes | None = None,
        file_mime_type: str | None = None,
        user_upload_id: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Extract banking transactions from a file.
        
        Args:
            file_path: Path to the file (or filename if file_content provided)
            file_content: Optional file content as bytes
            file_mime_type: MIME type of the file (e.g., 'application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            user_upload_id: Optional user upload ID to associate with transactions
            
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
        transactions = self._extract_structured_data(text_content, user_upload_id)
        
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
    
    def _extract_structured_data(
        self, 
        text_content: str, 
        user_upload_id: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Use OpenAI to extract structured banking transaction data from text.
        
        Returns a list of transaction dictionaries matching the schema.
        """
        system_prompt = """You are a financial data extraction expert specializing in Malaysian bank statements.
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
- category: Transaction category (e.g., 'food', 'transport', 'shopping', 'bills', etc.) if inferable
- currency: Currency code (default to 'MYR' for Malaysian Ringgit)

Important rules:
1. Parse dates in various formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc.) and convert to YYYY-MM-DD
2. Amounts should always be positive numbers
3. Determine transaction_type based on context:
   - Debit: Payments, purchases, withdrawals, transfers out
   - Credit: Deposits, salary, refunds, transfers in
4. Extract merchant_name from description when possible
5. If balance is not provided, set to null
6. If any optional field is not available, set to null
7. Generate a category based on merchant_name and description if possible

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
    
    def _transform_transaction(
        self, 
        transaction: Dict[str, Any], 
        user_upload_id: str | None = None
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
                category = str(category).strip() or None
            
            currency = transaction.get('currency', 'MYR').strip().upper() or 'MYR'
            
            # Generate unique ID
            transaction_id = str(uuid.uuid4())
            
            return {
                'id': transaction_id,
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
def extract_banking_transactions(
    file_path: str | Path,
    file_content: bytes | None = None,
    file_mime_type: str | None = None,
    user_upload_id: str | None = None
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
    return extractor.extract_from_file(
        file_path=file_path,
        file_content=file_content,
        file_mime_type=file_mime_type,
        user_upload_id=user_upload_id
    )

if __name__ == "__main__":
    file_path = Path(__file__).parent.parent.parent.parent.parent / "datasets" / "banking_transactions" / "Bank-Statement-Template-3-TemplateLab.pdf"
    assert file_path.exists(), "File does not exist"

    extractor = FinancialTextExtractor()
    transactions = extractor.extract_from_file(
        file_path=file_path,
        user_upload_id="1234567890"
    )
    print(transactions)