from contextvars import ContextVar
from typing import Optional, ClassVar

from pymongo.client_session import ClientSession
import motor.motor_asyncio


class SessionMethods:
    """
    Session methods
    """

    def set_session(self, session: Optional[ClientSession] = None):
        """
        Set pymongo session
        :param session: Optional[ClientSession] - pymongo session
        :return:
        """
        if session is not None:
            self.session: Optional[ClientSession] = session
        return self


class DocumentSessionMethods:
    """
    Document session methods
    """

    __session__: ClassVar[
        ContextVar[Optional[motor.motor_asyncio.AsyncIOMotorClientSession]]
    ] = ContextVar("session", default=None)

    @classmethod
    def set_session(
        cls,
        session: Optional[
            motor.motor_asyncio.AsyncIOMotorClientSession
        ] = None,
    ):
        """
        Set session to the ClassVar context
        :param session: Optional[ClientSession] - pymongo session
        :return:
        """
        if session is not None:
            cls.__session__.set(session)

    @classmethod
    def get_session(
        cls,
    ) -> Optional[motor.motor_asyncio.AsyncIOMotorClientSession]:
        """
        Get session from the ClassVar context
        :return: Optional[ClientSession]
        """
        return cls.__session__.get()

    @classmethod
    def clear_session(cls):
        """
        Clear session from the ClassVar context
        :return:
        """
        cls.__session__.set(None)
