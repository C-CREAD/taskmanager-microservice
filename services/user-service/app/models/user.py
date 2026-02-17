from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid


Base = declarative_base()


class User(Base):
    """
    User model representing users in the system

    • User information
        - id: UUID (i.e. User ID) Primary key to uniquely identify User record
        - username: Username of the User
        - first_name: User's first name
        - last_name: User's last name
        - password: User's password

    • Status information
        - is_active: Checks if the user is marked for deletion
        - is_verified: Checks if the user's account has been verified (after registration)
        - is_admin: Checks if user has admin privileges

    • Audit information
        - created_at/updated_at: Audit trail for User information
        - last_login: Gets the date of the User's last login
        - login_count: Tracks how many times the user has logged in to the system successfully.
    """
    __tablename__ = 'users'

    id = Column(String,
                primary_key=True,
                default=lambda: str(uuid.uuid4())
    )
    email = Column(String(255),
                  unique=True,
                  nullable=False,
                  index=True
    )
    username = Column(String(50),
                  unique=True,
                  nullable=False,
                  index=True
    )
    password = Column(String(255),
                      nullable=False
    )
    first_name = Column(String(100),
                      nullable=True
    )
    last_name = Column(String(255),
                      nullable=True
    )

    is_active = Column(Boolean,
                       default=True,
                       index=True
    )
    is_verified = Column(Boolean,
                       default=False,
    )
    is_admin = Column(Boolean,
                       default=False
    )
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        nullable=False

    )
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        onupdate=func.now(),
                        nullable=False
    )
    last_login = Column(DateTime(timezone=True),
                        nullable=True
    )
    login_count = Column(Integer,
                        default=0
    )

    def __repr__(self):
        return f"| User {self.username} |"