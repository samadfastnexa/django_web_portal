"""
HANA SQL queries for SAP B1 General Ledger Reports
"""
import logging
import re
from typing import Optional, List, Dict, Any
from decimal import Decimal
from .transaction_types import get_transaction_type_name

logger = logging.getLogger("general_ledger")


def _fetch_all(db, sql: str, params=()) -> List[Dict[str, Any]]:
    """Execute query and return all rows as list of dicts"""
    cur = db.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append(dict(r))
        else:
            row = {}
            for i, c in enumerate(cols):
                v = None
                try:
                    v = r[i]
                except Exception:
                    try:
                        v = getattr(r, c)
                    except Exception:
                        v = None
                row[c] = v
            out.append(row)
    cur.close()
    return out


def _fetch_one(db, sql: str, params=()) -> Optional[Dict[str, Any]]:
    """Execute query and return single row as dict"""
    cur = db.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    cols = [d[0] for d in cur.description] if cur.description else []
    cur.close()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    out = {}
    for i, c in enumerate(cols):
        v = None
        try:
            v = row[i]
        except Exception:
            try:
                v = getattr(row, c)
            except Exception:
                v = None
        out[c] = v
    return out


def chart_of_accounts_list(db, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get Chart of Accounts list for dropdowns and filters.
    
    Args:
        db: HANA database connection
        account_type: Optional filter by account type (e.g., 'A', 'L', 'E', 'I', 'O')
            A = Assets, L = Liabilities, E = Equity, I = Income, O = Expense
    
    Returns:
        List of accounts with AcctCode, AcctName, AcctType, FatherNum (parent account)
    """
    sql = """
    SELECT 
        "AcctCode",
        "AcctName",
        "GroupMask",
        "FatherNum",
        "Postable",
        "ActCurr",
        "Finanse",
        "ExportCode"
    FROM "OACT"
    WHERE 1=1
    """
    
    params = []
    
    if account_type:
        # Finanse field: A=Assets, L=Liabilities, E=Equity, I=Income, O=Expense
        sql += ' AND "Finanse" = ?'
        params.append(account_type.strip().upper())
    
    sql += ' ORDER BY "AcctCode"'
    
    return _fetch_all(db, sql, tuple(params))


def account_opening_balance(
    db, 
    account_code: str, 
    before_date: str,
    bp_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate opening balance for an account before a specific date.
    
    Args:
        db: HANA database connection
        account_code: G/L Account code
        before_date: Calculate balance before this date (YYYY-MM-DD)
        bp_code: Optional Business Partner filter
    
    Returns:
        Dict with Debit, Credit, and Balance (Debit - Credit)
    """
    sql = """
    SELECT 
        COALESCE(SUM("Debit"), 0) AS "Debit",
        COALESCE(SUM("Credit"), 0) AS "Credit",
        COALESCE(SUM("Debit"), 0) - COALESCE(SUM("Credit"), 0) AS "Balance"
    FROM "JDT1"
    WHERE "Account" = ?
        AND "RefDate" < TO_DATE(?, 'YYYY-MM-DD')
    """
    
    params = [account_code, before_date]
    
    if bp_code:
        sql += ' AND "ShortName" = ?'
        params.append(bp_code)
    
    result = _fetch_one(db, sql, tuple(params))
    
    if not result:
        return {"Debit": 0, "Credit": 0, "Balance": 0}
    
    return result


def general_ledger_report(
    db,
    account_from: Optional[str] = None,
    account_to: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    bp_code: Optional[str] = None,
    project_code: Optional[str] = None,
    trans_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0
) -> List[Dict[str, Any]]:
    """
    Get General Ledger transactions with full details.
    
    Args:
        db: HANA database connection
        account_from: Start of account range
        account_to: End of account range
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        bp_code: Business Partner filter
        project_code: Project filter
        trans_type: Transaction type filter (e.g., 'INV', 'RCT', 'JE')
        limit: Maximum rows to return
        offset: Number of rows to skip
    
    Returns:
        List of journal entry lines with account, BP, and transaction details
    """
    sql = """
    SELECT 
        T0."TransId",
        T0."RefDate" AS "PostingDate",
        T0."DueDate",
        T0."TaxDate" AS "DocumentDate",
        T0."Ref1" AS "Reference1",
        T0."Ref2" AS "Reference2",
        T0."Ref3" AS "Reference3",
        T0."TransType",
        T0."BaseRef" AS "BaseDocument",
        T0."Memo" AS "HeaderMemo",
        T0."CreateDate" AS "CreatedOn",
        T0."UserSign" AS "CreatedByCode",
        
        T1."Line_ID" AS "LineNum",
        T1."Account",
        T2."AcctName" AS "AccountName",
        T2."Finanse" AS "AccountType",
        T1."Debit",
        T1."Credit",
        T1."FCDebit" AS "FCDebit",
        T1."FCCredit" AS "FCCredit",
        T1."FCCurrency",
        T1."ShortName" AS "BPCode",
        COALESCE(T3."CardName", T6."firstName" || ' ' || T6."lastName") AS "BPName",
        T1."LineMemo" AS "Description",
        T1."Project" AS "ProjectCode",
        T4."PrjName" AS "ProjectName",
        T1."Ref1" AS "LineRef1",
        T1."Ref2" AS "LineRef2",
        
        COALESCE(T5."Quantity", 0) AS "Qty",
        COALESCE(T5."Price", 0) AS "UnitPrice",
        COALESCE(T5."DiscPrcnt", 0) AS "Discount",
        COALESCE(T5."GTotal", ABS(T1."Debit" + T1."Credit")) AS "Amount"
        
    FROM "OJDT" T0
    INNER JOIN "JDT1" T1 ON T0."TransId" = T1."TransId"
    LEFT JOIN "OACT" T2 ON T1."Account" = T2."AcctCode"
    LEFT JOIN "OCRD" T3 ON T1."ShortName" = T3."CardCode"
    LEFT JOIN "OPRJ" T4 ON T1."Project" = T4."PrjCode"
    LEFT JOIN "INV1" T5 ON T0."BaseRef" = CAST(T5."DocEntry" AS VARCHAR) AND T1."Line_ID" = T5."LineNum"
    LEFT JOIN "OHEM" T6 ON T1."ShortName" = CAST(T6."empID" AS VARCHAR)
    WHERE 1=1
    """
    
    params = []
    
    # Account range filter
    if account_from:
        sql += ' AND T1."Account" >= ?'
        params.append(account_from.strip())
    
    if account_to:
        sql += ' AND T1."Account" <= ?'
        params.append(account_to.strip())
    
    # Date range filter
    if from_date:
        sql += " AND T0.\"RefDate\" >= TO_DATE(?, 'YYYY-MM-DD')"
        params.append(from_date.strip())
    
    if to_date:
        sql += " AND T0.\"RefDate\" <= TO_DATE(?, 'YYYY-MM-DD')"
        params.append(to_date.strip())
    
    # Business Partner filter
    if bp_code:
        if isinstance(bp_code, list):
            # Multiple BP codes
            placeholders = ','.join(['?' for _ in bp_code])
            sql += f' AND T1."ShortName" IN ({placeholders})'
            params.extend([code.strip() for code in bp_code])
        else:
            # Single BP code
            sql += ' AND T1."ShortName" = ?'
            params.append(bp_code.strip())
    
    # Project filter
    if project_code:
        sql += ' AND T1."Project" = ?'
        params.append(project_code.strip())
    
    # Transaction type filter
    if trans_type:
        sql += ' AND T0."TransType" = ?'
        params.append(trans_type.strip())
    
    # Order by account, then date, then transaction ID
    sql += ' ORDER BY T1."Account", T0."RefDate", T0."TransId", T1."Line_ID"'
    
    # Pagination
    if limit:
        sql += f' LIMIT {int(limit)}'
    if offset:
        sql += f' OFFSET {int(offset)}'
    
    # Fetch results
    results = _fetch_all(db, sql, tuple(params))
    
    # Post-process results to add transaction type name and extract project from description
    for row in results:
        # Add transaction type name
        trans_type_code = row.get('TransType')
        row['TransTypeName'] = get_transaction_type_name(trans_type_code)
        
        # Extract project from description if it contains "PR: xxxxx | IN: xxxxxx" pattern
        description = row.get('Description', '')
        if description and 'PR:' in description:
            # Pattern: "PR: 232687 | IN: 5700817"
            match = re.search(r'PR:\s*(\d+)', description)
            if match:
                row['ExtractedProject'] = match.group(1)
            else:
                row['ExtractedProject'] = None
        else:
            row['ExtractedProject'] = None
    
    return results


def general_ledger_count(
    db,
    account_from: Optional[str] = None,
    account_to: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    bp_code: Optional[str] = None,
    project_code: Optional[str] = None,
    trans_type: Optional[str] = None
) -> int:
    """
    Count total records for pagination.
    
    Same filters as general_ledger_report but returns count only.
    """
    sql = """
    SELECT COUNT(*) AS "TotalCount"
    FROM "OJDT" T0
    INNER JOIN "JDT1" T1 ON T0."TransId" = T1."TransId"
    WHERE 1=1
    """
    
    params = []
    
    if account_from:
        sql += ' AND T1."Account" >= ?'
        params.append(account_from.strip())
    
    if account_to:
        sql += ' AND T1."Account" <= ?'
        params.append(account_to.strip())
    
    if from_date:
        sql += " AND T0.\"RefDate\" >= TO_DATE(?, 'YYYY-MM-DD')"
        params.append(from_date.strip())
    
    if to_date:
        sql += " AND T0.\"RefDate\" <= TO_DATE(?, 'YYYY-MM-DD')"
        params.append(to_date.strip())
    
    if bp_code:
        if isinstance(bp_code, list):
            # Multiple BP codes
            placeholders = ','.join(['?' for _ in bp_code])
            sql += f' AND T1."ShortName" IN ({placeholders})'
            params.extend([code.strip() for code in bp_code])
        else:
            # Single BP code
            sql += ' AND T1."ShortName" = ?'
            params.append(bp_code.strip())
    
    if project_code:
        sql += ' AND T1."Project" = ?'
        params.append(project_code.strip())
    
    if trans_type:
        sql += ' AND T0."TransType" = ?'
        params.append(trans_type.strip())
    
    result = _fetch_one(db, sql, tuple(params))
    
    if not result:
        return 0
    
    return int(result.get("TotalCount", 0))


def transaction_types_lov(db) -> List[Dict[str, Any]]:
    """
    Get list of transaction types for dropdown filter.
    
    Returns:
        List of unique transaction types with descriptions
    """
    # SAP B1 standard transaction types
    transaction_types = [
        {"Code": "13", "Name": "A/R Invoice"},
        {"Code": "14", "Name": "A/R Credit Memo"},
        {"Code": "18", "Name": "A/P Invoice"},
        {"Code": "19", "Name": "A/P Credit Memo"},
        {"Code": "24", "Name": "Incoming Payment"},
        {"Code": "46", "Name": "Outgoing Payment"},
        {"Code": "30", "Name": "Journal Entry"},
        {"Code": "59", "Name": "Goods Receipt"},
        {"Code": "60", "Name": "Goods Issue"},
        {"Code": "67", "Name": "Inventory Transfer"},
        {"Code": "162", "Name": "Inventory Revaluation"},
    ]
    
    return transaction_types


def business_partner_lov(db, bp_type: Optional[str] = 'C', limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get Business Partner list for dropdown filter.
    Only returns valid business partners used in journal entries.
    Defaults to customers (CardType='C') to avoid employees and contracts.
    
    Args:
        db: HANA database connection
        bp_type: 'C' for Customer, 'S' for Supplier, 'L' for Lead
        limit: Maximum records to return
    
    Returns:
        List of business partners with CardCode and CardName
    """
    sql = """
    SELECT DISTINCT
        T0."CardCode",
        T0."CardName",
        T0."CardType"
    FROM "OCRD" T0
    INNER JOIN "JDT1" T1 ON T0."CardCode" = T1."ShortName"
    WHERE T0."CardCode" IS NOT NULL
    AND T0."CardName" IS NOT NULL
    AND T0."CardCode" NOT LIKE 'LS%'
    AND NOT EXISTS (SELECT 1 FROM "OHEM" E WHERE CAST(E."empID" AS VARCHAR) = T0."CardCode")
    """
    
    params = []
    
    if bp_type:
        sql += ' AND T0."CardType" = ?'
        params.append(bp_type.strip().upper())
    
    sql += ' ORDER BY T0."CardCode"'
    sql += f' LIMIT {int(limit)}'
    
    return _fetch_all(db, sql, tuple(params))


def projects_lov(db, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get Projects list for dropdown filter.
    
    Args:
        db: HANA database connection
        active_only: If True, return only active projects
    
    Returns:
        List of projects with PrjCode and PrjName
    """
    sql = """
    SELECT 
        "PrjCode",
        "PrjName",
        "Active"
    FROM "OPRJ"
    WHERE 1=1
    """
    
    params = []
    
    if active_only:
        sql += ' AND "Active" = ?'
        params.append('Y')
    
    sql += ' ORDER BY "PrjCode"'
    
    return _fetch_all(db, sql, tuple(params))
