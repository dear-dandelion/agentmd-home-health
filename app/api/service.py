from app.core.message_processor import MessageProcessor
from app.core.response_formatter import ResponseFormatter
from app.core.user_manager import UserManager
from app.data.data_access import DataAccess
from app.literature.service import MedicalCalculatorLiteratureService


class AppService:
    def __init__(self) -> None:
        self.data_access = DataAccess()
        self.user_manager = UserManager(self.data_access)
        self.response_formatter = ResponseFormatter()
        self.message_processor = MessageProcessor(self.data_access)
        self.literature_service = MedicalCalculatorLiteratureService()
