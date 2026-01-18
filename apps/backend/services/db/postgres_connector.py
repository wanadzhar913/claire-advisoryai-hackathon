"""This file contains the database service for the application."""

from datetime import date, datetime
from decimal import Decimal
from typing import (
    Dict,
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
)

# Try to import settings, with fallback for when running as script
try:
    from backend.config import settings
    from backend.models.session import Session as ChatSession
    from backend.models.user import User
    from backend.models.goal import Goal
    from backend.models.banking_transaction import BankingTransaction
    from backend.models.user_upload import UserUpload
    from backend.models.financial_insight import FinancialInsight
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
    from backend.models.session import Session as ChatSession
    from backend.models.user import User
    from backend.models.goal import Goal
    from backend.models.banking_transaction import BankingTransaction
    from backend.models.user_upload import UserUpload
    from backend.models.financial_insight import FinancialInsight


class DatabaseService:
    """Service class for database operations.

    This class handles all database operations for Users, Sessions, and Messages.
    It uses SQLModel for ORM operations and maintains a connection pool.
    """

    def __init__(self):
        """Initialize database service with connection pool."""
        try:
            # Configure environment-specific database connection pool settings
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # Create engine with appropriate pool configuration
            connection_url = (
                f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
            if getattr(settings, "POSTGRES_SSLMODE", None):
                connection_url += f"?sslmode={settings.POSTGRES_SSLMODE}"

            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # Connection timeout (seconds)
                pool_recycle=1800,  # Recycle connections after 30 minutes
            )

            # Create tables (only if they don't exist)
            SQLModel.metadata.create_all(self.engine)

            # logger.info(
            #     "database_initialized",
            #     environment=settings.ENVIRONMENT.value,
            #     pool_size=pool_size,
            #     max_overflow=max_overflow,
            # )
        except SQLAlchemyError:
            # logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            raise

    async def create_user(self, email: str, password: str) -> User:
        """Create a new user.

        Args:
            email: User's email address
            password: Hashed password

        Returns:
            User: The created user
        """
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password)
            session.add(user)
            session.commit()
            session.refresh(user)
            # logger.info("user_created", email=email)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        """Get a user by Clerk ID.

        Args:
            clerk_id: The Clerk user ID to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.clerk_id == clerk_id)
            user = session.exec(statement).first()
            return user

    async def create_user_from_clerk(self, clerk_id: str, email: str) -> User:
        """Create a new user from Clerk authentication.

        Args:
            clerk_id: The Clerk user ID
            email: User's email address from Clerk

        Returns:
            User: The created user
        """
        with Session(self.engine) as session:
            user = User(clerk_id=clerk_id, email=email, hashed_password=None)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            # logger.info("user_deleted", email=email)
            return True

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            # logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            # logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            sessions = session.exec(statement).all()
            return sessions

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            # logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        return Session(self.engine)

    def create_banking_transaction(self, banking_transaction: BankingTransaction) -> BankingTransaction:
        """Create a new banking transaction.

        Args:
            banking_transaction: The banking transaction to create

        Returns:
            BankingTransaction: The created banking transaction
        """
        with Session(self.engine) as session:
            session.add(banking_transaction)
            session.commit()
            session.refresh(banking_transaction)
            return banking_transaction

    def create_banking_transactions_bulk(
        self, banking_transactions: List[BankingTransaction]
    ) -> List[BankingTransaction]:
        """Create multiple banking transactions in bulk.

        Args:
            banking_transactions: List of banking transactions to create

        Returns:
            List[BankingTransaction]: List of created banking transactions

        Raises:
            ValueError: If the list is empty
        """
        if not banking_transactions:
            raise ValueError("Cannot create empty list of banking transactions")

        with Session(self.engine) as session:
            session.add_all(banking_transactions)
            session.commit()
            # Refresh all transactions
            for transaction in banking_transactions:
                session.refresh(transaction)
            return banking_transactions

    def filter_banking_transactions(
        self,
        user_id: Optional[int] = None,
        file_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        merchant_name: Optional[str] = None,
        transaction_type: Optional[str] = None,
        category: Optional[str] = None,
        is_subscription: Optional[bool] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        transaction_year: Optional[int] = None,
        transaction_month: Optional[int] = None,
        currency: Optional[str] = None,
        description: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "transaction_date",
        order_desc: bool = True,
    ) -> List[BankingTransaction]:
        """Filter banking transactions by various criteria.

        Args:
            user_id: Filter by user ID
            file_id: Filter by file ID (user upload file ID)
            start_date: Filter transactions from this date onwards (inclusive)
            end_date: Filter transactions up to this date (inclusive)
            merchant_name: Filter by merchant name (partial match, case-insensitive)
            transaction_type: Filter by transaction type ('debit' or 'credit')
            category: Filter by transaction category
            min_amount: Minimum transaction amount (inclusive)
            max_amount: Maximum transaction amount (inclusive)
            is_subscription: Filter by subscription status (likely to recur monthly)
            transaction_year: Filter by transaction year
            transaction_month: Filter by transaction month (1-12)
            currency: Filter by currency code (e.g., 'MYR')
            description: Filter by description (partial match, case-insensitive)
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            order_by: Field to order by (default: 'transaction_date')
            order_desc: If True, order descending; if False, order ascending

        Returns:
            List[BankingTransaction]: List of matching banking transactions
        """
        with Session(self.engine) as session:
            statement = select(BankingTransaction)
            conditions = []

            # Filter by user_id
            if user_id is not None:
                conditions.append(BankingTransaction.user_id == user_id)

            # Filter by file_id
            if file_id is not None:
                conditions.append(BankingTransaction.file_id == file_id)

            # Filter by date range
            if start_date is not None:
                conditions.append(BankingTransaction.transaction_date >= start_date)
            if end_date is not None:
                conditions.append(BankingTransaction.transaction_date <= end_date)

            # Filter by merchant name (partial match, case-insensitive)
            if merchant_name is not None:
                conditions.append(
                    BankingTransaction.merchant_name.ilike(f"%{merchant_name}%")
                )

            # Filter by transaction type
            if transaction_type is not None:
                conditions.append(BankingTransaction.transaction_type == transaction_type)

            # Filter by category
            if category is not None:
                conditions.append(BankingTransaction.category == category)

            # Filter by subscription status
            if is_subscription is not None:
                conditions.append(BankingTransaction.is_subscription == is_subscription)

            # Filter by amount range
            if min_amount is not None:
                conditions.append(BankingTransaction.amount >= min_amount)
            if max_amount is not None:
                conditions.append(BankingTransaction.amount <= max_amount)

            # Filter by year
            if transaction_year is not None:
                conditions.append(BankingTransaction.transaction_year == transaction_year)

            # Filter by month
            if transaction_month is not None:
                conditions.append(BankingTransaction.transaction_month == transaction_month)

            # Filter by currency
            if currency is not None:
                conditions.append(BankingTransaction.currency == currency)

            # Filter by description (partial match, case-insensitive)
            if description is not None:
                conditions.append(BankingTransaction.description.ilike(f"%{description}%"))

            # Apply all conditions
            if conditions:
                statement = statement.where(and_(*conditions))

            # Apply ordering
            order_field = getattr(BankingTransaction, order_by, BankingTransaction.transaction_date)
            if order_desc:
                statement = statement.order_by(order_field.desc())
            else:
                statement = statement.order_by(order_field.asc())

            # Apply pagination
            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            transactions = session.exec(statement).all()
            return transactions

    def create_user_upload(self, user_upload: UserUpload) -> UserUpload:
        """Create a new user upload.

        Args:
            user_upload: The user upload to create

        Returns:
            UserUpload: The created user upload
        """
        with Session(self.engine) as session:
            session.add(user_upload)
            session.commit()
            session.refresh(user_upload)
            return user_upload

    def create_goal(self, goal: Goal) -> Goal:
        """Create a new financial goal."""
        with Session(self.engine) as session:
            session.add(goal)
            session.commit()
            session.refresh(goal)
            return goal

    def get_user_goals(
        self,
        user_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[Goal]:
        """Get all goals for a user with optional pagination."""
        with Session(self.engine) as session:
            statement = select(Goal).where(Goal.user_id == user_id)

            order_field = getattr(Goal, order_by, Goal.created_at)
            statement = statement.order_by(order_field.desc() if order_desc else order_field.asc())

            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return session.exec(statement).all()

    def get_goal(self, user_id: int, goal_id: str) -> Optional[Goal]:
        """Get a single goal for a user (ownership enforced)."""
        with Session(self.engine) as session:
            statement = select(Goal).where(and_(Goal.user_id == user_id, Goal.id == goal_id))
            return session.exec(statement).first()

    def update_goal(
        self,
        user_id: int,
        goal_id: str,
        name: Optional[str] = None,
        target_amount: Optional[Decimal] = None,
        current_saved: Optional[Decimal] = None,
        target_year: Optional[int] = None,
        target_month: Optional[int] = None,
        banner_key: Optional[str] = None,
    ) -> Goal:
        """Update a goal (ownership enforced)."""
        with Session(self.engine) as session:
            goal = session.exec(select(Goal).where(and_(Goal.user_id == user_id, Goal.id == goal_id))).first()
            if not goal:
                raise HTTPException(status_code=404, detail="Goal not found")

            if name is not None:
                goal.name = name
            if target_amount is not None:
                goal.target_amount = target_amount
            if current_saved is not None:
                goal.current_saved = current_saved
            if target_year is not None:
                goal.target_year = target_year
            if target_month is not None:
                goal.target_month = target_month
            if banner_key is not None:
                goal.banner_key = banner_key

            session.add(goal)
            session.commit()
            session.refresh(goal)
            return goal

    def delete_goal(self, user_id: int, goal_id: str) -> bool:
        """Delete a goal (ownership enforced)."""
        with Session(self.engine) as session:
            goal = session.exec(select(Goal).where(and_(Goal.user_id == user_id, Goal.id == goal_id))).first()
            if not goal:
                return False
            session.delete(goal)
            session.commit()
            return True

    def get_user_uploads(
        self,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[UserUpload]:
        """Get all user uploads with optional filtering and pagination.
        
        Args:
            user_id: Optional filter by user ID. If None, returns uploads for all users.
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            order_by: Field to order by (default: 'created_at')
            order_desc: If True, order descending; if False, order ascending
            
        Returns:
            List[UserUpload]: List of user uploads
        """
        with Session(self.engine) as session:
            statement = select(UserUpload)
            
            # Filter by user_id if provided
            if user_id is not None:
                statement = statement.where(UserUpload.user_id == user_id)
            
            # Apply ordering
            order_field = getattr(UserUpload, order_by, UserUpload.created_at)
            if order_desc:
                statement = statement.order_by(order_field.desc())
            else:
                statement = statement.order_by(order_field.asc())
            
            # Apply pagination
            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            
            uploads = session.exec(statement).all()
            return uploads

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception:
            # logger.error("database_health_check_failed", error=str(e))
            return False

    # Financial Insight methods
    def create_financial_insight(self, insight: FinancialInsight) -> FinancialInsight:
        """Create a new financial insight.

        Args:
            insight: The financial insight to create

        Returns:
            FinancialInsight: The created financial insight
        """
        with Session(self.engine) as session:
            session.add(insight)
            session.commit()
            session.refresh(insight)
            return insight

    def create_financial_insights_bulk(
        self, insights: List[FinancialInsight]
    ) -> List[FinancialInsight]:
        """Create multiple financial insights in bulk.

        Args:
            insights: List of financial insights to create

        Returns:
            List[FinancialInsight]: List of created financial insights

        Raises:
            ValueError: If the list is empty
        """
        if not insights:
            raise ValueError("Cannot create empty list of financial insights")

        with Session(self.engine) as session:
            session.add_all(insights)
            session.commit()
            for insight in insights:
                session.refresh(insight)
            return insights

    def get_user_insights(
        self,
        user_id: int,
        insight_type: Optional[str] = None,
        file_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[FinancialInsight]:
        """Get financial insights for a user with optional filtering.

        Args:
            user_id: The user ID to filter by
            insight_type: Optional filter by insight type (pattern, alert, recommendation)
            file_id: Optional filter by file ID
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            order_by: Field to order by (default: 'created_at')
            order_desc: If True, order descending; if False, order ascending

        Returns:
            List[FinancialInsight]: List of financial insights
        """
        with Session(self.engine) as session:
            statement = select(FinancialInsight).where(FinancialInsight.user_id == user_id)

            if insight_type is not None:
                statement = statement.where(FinancialInsight.insight_type == insight_type)

            if file_id is not None:
                statement = statement.where(FinancialInsight.file_id == file_id)

            order_field = getattr(FinancialInsight, order_by, FinancialInsight.created_at)
            if order_desc:
                statement = statement.order_by(order_field.desc())
            else:
                statement = statement.order_by(order_field.asc())

            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return session.exec(statement).all()

    def delete_user_insights(
        self,
        user_id: int,
        file_id: Optional[str] = None,
    ) -> int:
        """Delete financial insights for a user.

        Args:
            user_id: The user ID to delete insights for
            file_id: Optional filter to only delete insights for a specific file

        Returns:
            int: Number of deleted insights
        """
        with Session(self.engine) as session:
            statement = select(FinancialInsight).where(FinancialInsight.user_id == user_id)

            if file_id is not None:
                statement = statement.where(FinancialInsight.file_id == file_id)

            insights = session.exec(statement).all()
            count = len(insights)

            for insight in insights:
                session.delete(insight)

            session.commit()
            return count

    def delete_user_ai_insights(
        self,
        user_id: int,
        file_id: Optional[str] = None,
    ) -> int:
        """Delete AI-generated insights (metadata.source == 'ai_analysis') for a user.

        This is used to make analysis runs reproducible: re-running analysis should
        replace prior AI insights rather than accumulating duplicates.

        Args:
            user_id: The user ID to delete insights for
            file_id: Optional filter to only delete insights for a specific file

        Returns:
            int: Number of deleted insights
        """
        with Session(self.engine) as session:
            statement = select(FinancialInsight).where(FinancialInsight.user_id == user_id)
            if file_id is not None:
                statement = statement.where(FinancialInsight.file_id == file_id)

            insights = session.exec(statement).all()
            to_delete = []
            for insight in insights:
                meta = getattr(insight, "insight_metadata", None) or {}
                if meta.get("source") == "ai_analysis":
                    to_delete.append(insight)

            for insight in to_delete:
                session.delete(insight)

            session.commit()
            return len(to_delete)

    # Subscription classification methods
    def get_subscription_candidates(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        exclude_confirmed_rejected: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[BankingTransaction]:
        """Get candidate transactions for subscription classification.

        Args:
            user_id: The user ID to filter by
            start_date: Start date of the range (inclusive)
            end_date: End date of the range (inclusive)
            exclude_confirmed_rejected: If True, exclude transactions already confirmed/rejected
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List[BankingTransaction]: List of candidate transactions
        """
        with Session(self.engine) as session:
            statement = select(BankingTransaction).where(
                and_(
                    BankingTransaction.user_id == user_id,
                    BankingTransaction.transaction_type == 'debit',
                    BankingTransaction.transaction_date >= start_date,
                    BankingTransaction.transaction_date <= end_date,
                )
            )

            # Exclude already confirmed/rejected transactions if requested
            if exclude_confirmed_rejected:
                statement = statement.where(
                    or_(
                        BankingTransaction.subscription_status.is_(None),
                        BankingTransaction.subscription_status == 'predicted',
                        BankingTransaction.subscription_status == 'needs_review',
                    )
                )

            # Order by date and ID for consistent batching
            statement = statement.order_by(
                BankingTransaction.transaction_date.asc(),
                BankingTransaction.id.asc()
            )

            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return session.exec(statement).all()

    def bulk_update_subscription_classification(
        self,
        updates: List[Dict],
    ) -> int:
        """Bulk update subscription classification for transactions.

        Args:
            updates: List of dicts with transaction_id and classification fields:
                - transaction_id: str (required)
                - is_subscription: bool
                - subscription_status: str ('predicted', 'confirmed', 'rejected', 'needs_review')
                - subscription_confidence: float (0.0 to 1.0)
                - subscription_merchant_key: str | None
                - subscription_name: str | None
                - subscription_reason_codes: List[str] | None

        Returns:
            int: Number of transactions updated
        """
        if not updates:
            return 0

        updated_count = 0
        now = datetime.utcnow()

        with Session(self.engine) as session:
            for update in updates:
                transaction_id = update.get('transaction_id')
                if not transaction_id:
                    continue

                transaction = session.get(BankingTransaction, transaction_id)
                if not transaction:
                    continue

                # Update subscription fields
                if 'is_subscription' in update:
                    transaction.is_subscription = update['is_subscription']
                if 'subscription_status' in update:
                    transaction.subscription_status = update['subscription_status']
                if 'subscription_confidence' in update:
                    transaction.subscription_confidence = update['subscription_confidence']
                if 'subscription_merchant_key' in update:
                    transaction.subscription_merchant_key = update['subscription_merchant_key']
                if 'subscription_name' in update:
                    transaction.subscription_name = update['subscription_name']
                if 'subscription_reason_codes' in update:
                    transaction.subscription_reason_codes = update['subscription_reason_codes']

                transaction.subscription_updated_at = now
                session.add(transaction)
                updated_count += 1

            session.commit()

        return updated_count

    def review_subscription_transaction(
        self,
        user_id: int,
        transaction_id: str,
        decision: str,
    ) -> BankingTransaction:
        """Persist a user's review decision for a subscription classification.

        This is intended to resolve uncertain transactions (e.g. subscription_status == 'needs_review').

        Args:
            user_id: The authenticated user ID
            transaction_id: The transaction to review
            decision: 'confirmed' or 'rejected'

        Returns:
            BankingTransaction: The updated transaction

        Raises:
            ValueError: If decision is invalid, or transaction cannot be reviewed
        """
        if decision not in {"confirmed", "rejected"}:
            raise ValueError("decision must be 'confirmed' or 'rejected'")

        now = datetime.utcnow()

        with Session(self.engine) as session:
            tx = session.get(BankingTransaction, transaction_id)

            # Avoid leaking existence across users
            if not tx or tx.user_id != user_id:
                raise ValueError("Transaction not found")

            if tx.transaction_type != "debit":
                raise ValueError("Only debit transactions can be reviewed as subscriptions")

            if tx.subscription_status in {"confirmed", "rejected"}:
                raise ValueError("Transaction subscription status is already finalized")

            if decision == "confirmed":
                tx.is_subscription = True
                tx.subscription_status = "confirmed"
                reason_tag = "user_confirmed"
            else:
                tx.is_subscription = False
                tx.subscription_status = "rejected"
                reason_tag = "user_rejected"

            # Preserve and append reason codes
            existing_reasons = tx.subscription_reason_codes or []
            if not isinstance(existing_reasons, list):
                existing_reasons = []
            if reason_tag not in existing_reasons:
                existing_reasons.append(reason_tag)
            tx.subscription_reason_codes = existing_reasons

            tx.subscription_updated_at = now

            session.add(tx)
            session.commit()
            session.refresh(tx)

            return tx

    def get_subscription_needs_review(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[BankingTransaction]:
        """Get debit transactions flagged as needs_review for subscription classification."""
        with Session(self.engine) as session:
            statement = select(BankingTransaction).where(
                and_(
                    BankingTransaction.user_id == user_id,
                    BankingTransaction.transaction_type == "debit",
                    BankingTransaction.subscription_status == "needs_review",
                )
            )

            if start_date is not None:
                statement = statement.where(BankingTransaction.transaction_date >= start_date)
            if end_date is not None:
                statement = statement.where(BankingTransaction.transaction_date <= end_date)

            statement = statement.order_by(
                BankingTransaction.transaction_date.desc(),
                BankingTransaction.id.desc(),
            )

            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return session.exec(statement).all()


# Create a singleton instance
database_service = DatabaseService()

if __name__ == "__main__":
    import asyncio
    from decimal import Decimal
    
    async def main():
        database_service = DatabaseService()

        await database_service.create_user(
            email="test@example.com",
            password="test",
        )

        user = await database_service.get_user_by_email("test@example.com")
        user_id = user.id if user else None

        if not user_id:
            print("Failed to create or retrieve user")
            return

        database_service.create_user_upload(
            UserUpload(
                file_id="1",
                user_id=user_id,
                file_name="Test file",
                file_type="pdf",
                file_size=100,
                file_url="s3://bucket/test-file.pdf",
                file_mime_type="application/pdf",
                file_extension="pdf",
                statement_type="banking_transaction",
                expense_month=date.today().month,
                expense_year=date.today().year,
            )
        )

        uploads = database_service.get_user_uploads(user_id=user_id, limit=1)
        file_id = uploads[0].file_id if uploads else None

        if not file_id:
            print("Failed to create or retrieve user upload")
            return

        database_service.create_banking_transaction(
            BankingTransaction(
                id="1",
                user_id=user_id,
                file_id=file_id,
                transaction_date=date.today(),
                transaction_year=date.today().year,
                transaction_month=date.today().month,
                transaction_day=date.today().day,
                description="Test transaction",
                amount=Decimal("100.00"),
                transaction_type="debit",

            )
        )

        print(database_service.filter_banking_transactions(
            user_id=user_id,
            start_date=date.today(),
            end_date=date.today(),
            transaction_type="debit",
            min_amount=Decimal("100"),
            max_amount=Decimal("1000"),
        ))

    asyncio.run(main())